"""Runnable Pipecat bot that joins a LiveKit room (Pipecat owns the pipeline).

Install in its own environment (see requirements-pipecat.txt), then:

    python -m integrations.pipecat_livekit_bot --room pipecat-room          # text
    python -m integrations.pipecat_livekit_bot --room pipecat-room --voice  # Munsit speech

Text protocol (Pipecat's LiveKit transport uses JSON data packets, not the
`lk.chat` text streams of LiveKit Agents):
    client -> bot   {"type": "chat", "text": "..."}
    bot -> client   {"type": "reply", "text": "..."}

Do not also dispatch a LiveKit Agents worker into the same room.
"""
import argparse
import asyncio
import json
import os

from pipecat.frames.frames import (LLMFullResponseEndFrame, LLMFullResponseStartFrame,
                                   LLMMessagesAppendFrame, LLMTextFrame)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (LLMContextAggregatorPair,
                                                                    LLMUserAggregatorParams)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openrouter.llm import OpenRouterLLMService, OpenRouterLLMSettings
from pipecat.transports.livekit.transport import (LiveKitOutputTransportMessageFrame,
                                                  LiveKitParams, LiveKitTransport)

from examples.config import free_model, load_settings, require_livekit, require_speech_opt_in, required
from examples.room_access import create_token
from integrations.pipecat_pipeline import build_pipeline

BOT_IDENTITY = "pipecat-bot"
TTS_SAMPLE_RATE = 48000  # Munsit TTS native rate; the transport output must match.
SYSTEM = ("You are a concise teaching assistant running on Pipecat inside a LiveKit room. "
          "Reply in the user's language; for Arabic use clear Modern Standard Arabic. "
          "Keep answers to two short sentences. Do not invent facts.")


class ReplySender(FrameProcessor):
    """Collects one streamed LLM response and sends it to the room as JSON."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    async def process_frame(self, frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMFullResponseStartFrame):
            self._parts = []
        elif isinstance(frame, LLMTextFrame):
            self._parts.append(frame.text)
        elif isinstance(frame, LLMFullResponseEndFrame) and "".join(self._parts).strip():
            reply = json.dumps({"type": "reply", "text": "".join(self._parts).strip()},
                               ensure_ascii=False)
            await self.push_frame(LiveKitOutputTransportMessageFrame(message=reply))
        await self.push_frame(frame, direction)


def make_llm() -> OpenRouterLLMService:
    # Same guard as the LiveKit Agents examples: free routes, zero price ceilings.
    return OpenRouterLLMService(
        api_key=required("OPENROUTER_API_KEY"),
        settings=OpenRouterLLMSettings(
            model=free_model(), max_tokens=2048,
            extra={"extra_body": {"provider": {"max_price": {"prompt": 0, "completion": 0}},
                                  "reasoning": {"effort": "low", "exclude": True}}}),
    )


def make_speech(session):
    # pipecat-plugins-munsit 0.2.0 imports a private alias Pipecat 1.12 renamed.
    import pipecat.services.settings as settings
    settings._NotGiven = getattr(settings, "_NotGiven", settings.NotGiven)
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat_plugins_munsit import MunsitSTTService, MunsitTTSService

    require_speech_opt_in()
    key = required("MUNSIT_API_KEY")
    stt = MunsitSTTService(api_key=key)
    tts = MunsitTTSService(api_key=key, aiohttp_session=session, sample_rate=TTS_SAMPLE_RATE,
                           voice_id=required("MUNSIT_VOICE_ID"),
                           model=os.getenv("MUNSIT_TTS_MODEL", "faseeh-v1-preview"))
    return stt, tts, SileroVADAnalyzer()


def build_task(room: str, voice: bool, session=None) -> tuple[PipelineTask, LiveKitTransport]:
    transport = LiveKitTransport(
        url=required("LIVEKIT_URL"), token=create_token(room, BOT_IDENTITY), room_name=room,
        params=LiveKitParams(audio_in_enabled=voice, audio_out_enabled=voice,
                             audio_out_sample_rate=TTS_SAMPLE_RATE if voice else None),
    )
    context = LLMContext([{"role": "system", "content": SYSTEM}])
    llm = make_llm()
    if voice:
        stt, tts, vad = make_speech(session)
        aggregator = LLMContextAggregatorPair(
            context, user_params=LLMUserAggregatorParams(vad_analyzer=vad))
        pipeline = build_pipeline(transport, stt, llm, tts, aggregator)
    else:
        aggregator = LLMContextAggregatorPair(context)
        pipeline = Pipeline([transport.input(), aggregator.user(), llm, ReplySender(),
                             transport.output(), aggregator.assistant()])
    task = PipelineTask(pipeline, idle_timeout_secs=600)

    @transport.event_handler("on_app_message")
    async def on_app_message(transport, message: dict, sender: str):
        text = message.get("text") if message.get("type") == "chat" else None
        # Room data is untrusted input: accept only short text messages.
        if isinstance(text, str) and 0 < len(text.strip()) <= 500:
            await task.queue_frames([LLMMessagesAppendFrame(
                [{"role": "user", "content": text.strip()}], run_llm=True)])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant_id: str, reason: str):
        # One bot per conversation: stop when the last human leaves.
        await task.cancel()

    return task, transport


async def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--room", default=None)
    parser.add_argument("--voice", action="store_true")
    args = parser.parse_args()
    load_settings()
    require_livekit()
    room = args.room or os.getenv("LIVEKIT_ROOM", "tutorial-room")
    if args.voice:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            task, _ = build_task(room, voice=True, session=session)
            await PipelineRunner().run(task)
    else:
        task, _ = build_task(room, voice=False)
        print(f"Pipecat bot joining room {room!r}. Ctrl+C to stop.")
        await PipelineRunner().run(task)


if __name__ == "__main__":
    asyncio.run(main())

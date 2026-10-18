"""Live voice check without a microphone: publish a WAV as mic audio, expect speech back.

Requires a LiveKit server, a running voice agent (`... dev`) and Munsit credits:

    python -m tests.live_voice_smoke question.wav --agent tutorial-tools
    python -m tests.live_voice_smoke --say "ما هو بريد الدعم؟" --agent tutorial-tools

Passes when the agent transcribes the user, replies in text, and publishes audio.
"""
import argparse
import asyncio
import os
import sys
import uuid
import wave

import numpy as np
from livekit import rtc

from examples.config import load_settings, required, require_livekit, require_speech_opt_in
from examples.room_access import AGENTS, create_token, dispatch

RATE = 48000


async def synthesize(text: str) -> np.ndarray:
    """Speak the question with the configured Munsit voice (uses speech credits)."""
    from livekit.plugins import munsit
    import aiohttp

    require_speech_opt_in()
    async with aiohttp.ClientSession() as http:
        tts = munsit.TTS(api_key=required("MUNSIT_API_KEY"), voice_id=required("MUNSIT_VOICE_ID"),
                         model=os.getenv("MUNSIT_TTS_MODEL", "faseeh-v1-preview"),
                         sample_rate=RATE, http_session=http)
        frames = [ev.frame async for ev in tts.synthesize(text)]
        await tts.aclose()
    return np.concatenate([np.frombuffer(f.data, dtype=np.int16) for f in frames])


def load_wav(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        if w.getsampwidth() != 2:
            raise SystemExit("Use a 16-bit PCM WAV file.")
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        audio = audio.reshape(-1, w.getnchannels()).mean(axis=1)
        rate = w.getframerate()
    if rate != RATE:  # simple linear resample is enough for a smoke test
        audio = np.interp(np.arange(0, len(audio), rate / RATE), np.arange(len(audio)), audio)
    return audio.astype(np.int16)


async def run(args) -> int:
    load_settings()
    require_livekit()
    room_name = f"voice-smoke-{uuid.uuid4().hex[:8]}"
    room = rtc.Room()
    agent_joined, replied = asyncio.Event(), asyncio.Event()
    received = {"agent_audio_s": 0.0}
    tasks = set()

    def spawn(coro):
        task = asyncio.create_task(coro)
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    async def read_transcript(reader: rtc.TextStreamReader, identity: str):
        text = (await reader.read_all()).strip()
        if not text:
            return
        mine = reader.info.attributes.get("lk.transcribed_track_id") == mic_sid
        print(f"  {'you (STT)' if mine else identity}: {text}")
        if not mine:
            replied.set()

    async def count_audio(track: rtc.RemoteAudioTrack):
        async for event in rtc.AudioStream(track, sample_rate=RATE, num_channels=1):
            # Remote tracks deliver silence continuously; count only audible frames.
            if np.abs(np.frombuffer(event.frame.data, dtype=np.int16)).max(initial=0) > 500:
                received["agent_audio_s"] += event.frame.samples_per_channel / RATE

    @room.on("participant_connected")
    def on_join(participant: rtc.RemoteParticipant):
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            agent_joined.set()

    @room.on("track_subscribed")
    def on_track(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            spawn(count_audio(track))

    room.register_text_stream_handler(
        "lk.transcription", lambda reader, identity: spawn(read_transcript(reader, identity)))
    mic_sid = ""
    question = await synthesize(args.say) if args.say else load_wav(args.wav)
    try:
        await room.connect(required("LIVEKIT_URL"), create_token(room_name, f"voice-{uuid.uuid4().hex[:6]}"))
        source = rtc.AudioSource(RATE, 1)
        track = rtc.LocalAudioTrack.create_audio_track("mic", source)
        publication = await room.local_participant.publish_track(
            track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))
        mic_sid = publication.sid
        await dispatch(room_name, args.agent)
        await asyncio.wait_for(agent_joined.wait(), args.timeout)
        print(f"room={room_name} agent={args.agent} joined; speaking {len(question) / RATE:.1f}s")
        await asyncio.sleep(3)  # let the session subscribe to our microphone

        chunk = RATE // 100  # 10 ms frames, paced like a real microphone
        audio = np.concatenate([question, np.zeros(RATE * 2, dtype=np.int16)])
        for start in range(0, len(audio) - chunk + 1, chunk):
            frame = rtc.AudioFrame(audio[start:start + chunk].tobytes(), RATE, 1, chunk)
            await source.capture_frame(frame)
        await asyncio.wait_for(replied.wait(), args.timeout)
        await asyncio.sleep(args.listen)  # collect the spoken reply
        print(f"audible agent speech received: {received['agent_audio_s']:.1f}s")
        if received["agent_audio_s"] < 0.5:
            print("FAIL: agent replied in text but no audio arrived")
            return 1
        print("PASS")
        return 0
    except asyncio.TimeoutError:
        print(f"FAIL: no agent or reply within {args.timeout:.0f}s")
        return 1
    finally:
        await room.disconnect()
        for task in list(tasks):
            task.cancel()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("wav", nargs="?", help="16-bit PCM WAV with one spoken question")
    source.add_argument("--say", help="synthesize this question with the Munsit voice instead")
    parser.add_argument("--agent", choices=AGENTS, default="tutorial-voice")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--listen", type=float, default=8, help="seconds to record the reply")
    args = parser.parse_args()
    if os.name == "nt":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()

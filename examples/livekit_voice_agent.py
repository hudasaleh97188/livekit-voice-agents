"""Munsit STT + free OpenRouter LLM + Munsit TTS."""
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession

from .config import load_settings
from .livekit_common import INSTRUCTIONS, make_llm, speech_providers

load_settings()
server = AgentServer()


@server.rtc_session(agent_name="tutorial-voice")
async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(llm=make_llm(), **speech_providers())
    await session.start(room=ctx.room, agent=Agent(instructions=INSTRUCTIONS))
    # Wait for the user to speak: avoids an unnecessary greeting request.


if __name__ == "__main__":
    agents.cli.run_app(server)


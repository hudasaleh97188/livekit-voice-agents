"""A room-based text agent: no STT or TTS charges."""
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, room_io

from .config import load_settings
from .livekit_common import INSTRUCTIONS, make_llm

load_settings()
server = AgentServer()


@server.rtc_session(agent_name="tutorial-text")
async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(llm=make_llm())
    await session.start(
        room=ctx.room,
        agent=Agent(instructions=INSTRUCTIONS),
        room_options=room_io.RoomOptions(audio_input=False, audio_output=False),
    )


if __name__ == "__main__":
    agents.cli.run_app(server)


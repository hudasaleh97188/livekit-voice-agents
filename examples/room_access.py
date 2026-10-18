"""Server-side short-lived room tokens and explicit agent dispatch."""
import argparse
import asyncio
import os
from datetime import timedelta

from livekit import api

from .config import load_settings, required, require_livekit


AGENTS = ["tutorial-text", "tutorial-voice", "tutorial-tools", "tutorial-desk"]


def create_token(room: str, identity: str, attributes: dict[str, str] | None = None,
                 agent: str | None = None) -> str:
    if not room.strip() or not identity.strip():
        raise ValueError("Room and participant identity cannot be empty.")
    token = (
        api.AccessToken(required("LIVEKIT_API_KEY"), required("LIVEKIT_API_SECRET"))
        .with_identity(identity)
        .with_ttl(timedelta(minutes=10))
        .with_grants(api.VideoGrants(room_join=True, room=room,
                                    can_publish=True, can_subscribe=True,
                                    can_publish_data=True))
    )
    if attributes:
        # Signed into the JWT: the agent can trust these, unlike chat text.
        token = token.with_attributes(attributes)
    if agent:
        # Dispatch on join: the agent is assigned when this participant creates the room.
        token = token.with_room_config(api.RoomConfiguration(
            agents=[api.RoomAgentDispatch(agent_name=agent)]))
    return token.to_jwt()


async def dispatch(room: str, agent_name: str):
    # LiveKitAPI reads the same LIVEKIT_* environment variables.
    async with api.LiveKitAPI() as client:
        result = await client.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(room=room, agent_name=agent_name)
        )
        print(f"Dispatched {agent_name}; dispatch id: {result.id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["token", "dispatch"])
    parser.add_argument("--room")
    parser.add_argument("--identity", default="tutorial-human")
    parser.add_argument("--agent", choices=AGENTS, default="tutorial-voice")
    args = parser.parse_args()
    load_settings()
    require_livekit()
    room = args.room or os.getenv("LIVEKIT_ROOM", "tutorial-room")
    if args.action == "token":
        # Intended CLI output: this token is a credential, so do not log/share it.
        print(create_token(room, args.identity))
    else:
        asyncio.run(dispatch(room, args.agent))


if __name__ == "__main__":
    main()


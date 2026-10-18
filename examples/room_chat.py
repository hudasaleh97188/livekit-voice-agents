"""Local CLI client for the text agent. Keeps API secrets on this machine."""
import asyncio
import os
import uuid

from livekit import rtc

from .config import load_settings, required, require_livekit
from .room_access import create_token


async def main():
    load_settings()
    require_livekit()
    room_name = os.getenv("LIVEKIT_ROOM", "tutorial-room")
    room = rtc.Room()
    pending = set()

    async def display(reader, identity):
        try:
            print(f"\n{identity}: {await reader.read_all()}")
        except Exception:
            print("\nA text stream ended unexpectedly.")

    def receive(reader, identity):
        task = asyncio.create_task(display(reader, identity))
        pending.add(task)
        task.add_done_callback(pending.discard)

    room.register_text_stream_handler("lk.transcription", receive)
    try:
        token = create_token(room_name, f"learner-{uuid.uuid4().hex[:8]}")
        await room.connect(required("LIVEKIT_URL"), token)
        print("Connected. Dispatch tutorial-text to this room in another terminal.")
        print("Wait until the agent reports its session started, then type. /quit exits.")
        while True:
            try:
                message = await asyncio.to_thread(input, "You: ")
            except EOFError:
                break
            if message.strip() == "/quit":
                break
            if message.strip():
                await room.local_participant.send_text(message, topic="lk.chat")
    finally:
        await room.disconnect()
        for task in list(pending):
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())

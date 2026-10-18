"""Live end-to-end check: join a fresh room, dispatch an agent, exchange text.

Requires a running LiveKit server and the agent process (`... dev`). Uses the
free OpenRouter route only; no speech services are called.

    python -m tests.live_room_smoke --agent tutorial-text "What is LiveKit?"
    python -m tests.live_room_smoke --agent tutorial-desk --customer cust-amal \\
        --token-dispatch --rpc "Where is my order NR-1001?"
    python -m tests.live_room_smoke --pipecat --room pipecat-room "Hello"
"""
import argparse
import asyncio
import json
import os
import sys
import time
import uuid

from livekit import rtc

from examples.config import load_settings, required, require_livekit
from examples.room_access import AGENTS, create_token, dispatch


async def run(args) -> int:
    load_settings()
    require_livekit()
    # Fresh room per run avoids duplicate agents; a Pipecat bot joins a named room.
    room_name = args.room or f"smoke-{uuid.uuid4().hex[:8]}"
    room = rtc.Room()
    replies: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
    agent_joined = asyncio.Event()
    agent_identity = ""
    tasks = set()

    async def collect(reader, identity):
        replies.put_nowait((identity, await reader.read_all()))

    def on_text(reader, identity):
        task = asyncio.create_task(collect(reader, identity))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    def is_bot(participant: rtc.RemoteParticipant) -> bool:
        if args.pipecat:
            return participant.identity == "pipecat-bot"
        return participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT

    @room.on("participant_connected")
    def on_join(participant: rtc.RemoteParticipant):
        nonlocal agent_identity
        if is_bot(participant):
            agent_identity = participant.identity
            agent_joined.set()

    @room.on("data_received")
    def on_data(packet: rtc.DataPacket):
        # Pipecat replies arrive as JSON data packets rather than text streams.
        try:
            message = json.loads(packet.data)
        except ValueError:
            return
        if isinstance(message, dict) and message.get("type") == "reply":
            replies.put_nowait((packet.participant.identity, str(message.get("text", ""))))

    @room.on("participant_attributes_changed")
    def on_attrs(changed: dict, participant: rtc.Participant):
        if "desk.agent" in changed:
            print(f"  [ui] active specialist -> {changed['desk.agent']}")

    room.register_text_stream_handler("lk.transcription", on_text)
    attributes = {"customer_id": args.customer} if args.customer else None
    token = create_token(room_name, f"smoke-{uuid.uuid4().hex[:6]}", attributes,
                         agent=args.agent if args.token_dispatch else None)
    try:
        await room.connect(required("LIVEKIT_URL"), token)
        for participant in room.remote_participants.values():  # bot may already be here
            on_join(participant)
        if not (args.token_dispatch or args.pipecat):
            await dispatch(room_name, args.agent)
        await asyncio.wait_for(agent_joined.wait(), args.timeout)
        await asyncio.sleep(1.5)  # let the session register its text handler
        print(f"room={room_name} bot={agent_identity} joined")
        for message in args.messages:
            started = time.perf_counter()
            if args.pipecat:
                payload = json.dumps({"type": "chat", "text": message}, ensure_ascii=False)
                await room.local_participant.publish_data(payload, reliable=True)
            else:
                await room.local_participant.send_text(message, topic="lk.chat")
            print(f"\nYou: {message}")
            answered = False
            wait = args.timeout
            while True:  # a handoff can produce several replies for one turn
                try:
                    identity, text = await asyncio.wait_for(replies.get(), wait)
                except asyncio.TimeoutError:
                    break
                if text.strip():  # models may stream blank text beside a tool call
                    print(f"{identity} ({time.perf_counter() - started:.1f}s): {text}")
                    answered, wait = True, args.settle
            if not answered:
                print("FAIL: no non-empty reply")
                return 1
        if args.rpc:
            state = await room.local_participant.perform_rpc(
                destination_identity=agent_identity, method="desk.state", payload="")
            print(f"\nRPC desk.state -> {json.loads(state)}")
        print("\nPASS")
        return 0
    except asyncio.TimeoutError:
        print(f"FAIL: no agent/reply within {args.timeout:.0f}s. "
              f"Is `{args.agent}` running in dev mode?")
        return 1
    finally:
        await room.disconnect()
        for task in list(tasks):
            task.cancel()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("messages", nargs="*", default=["In one sentence, what is LiveKit?"])
    parser.add_argument("--agent", choices=AGENTS, default="tutorial-text")
    parser.add_argument("--customer", help="verified customer_id token attribute")
    parser.add_argument("--token-dispatch", action="store_true",
                        help="embed the dispatch in the token instead of calling the API")
    parser.add_argument("--rpc", action="store_true", help="query desk.state over RPC")
    parser.add_argument("--pipecat", action="store_true",
                        help="talk to integrations.pipecat_livekit_bot (needs --room)")
    parser.add_argument("--room", help="join this room instead of a fresh one")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--settle", type=float, default=6,
                        help="seconds of quiet that end one turn's replies")
    args = parser.parse_args()
    if args.pipecat and not args.room:
        parser.error("--pipecat needs --room (the room the bot joined)")
    if os.name == "nt":
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()

# Noura Care: a complete local customer-support use case

Noura is a fictional UAE electronics store. Noor is its support assistant. The application combines a responsive English/Arabic frontend, a Python backend, a bilingual knowledge base, SQLite conversations and tickets, free OpenRouter generation, and an optional LiveKit/Munsit voice agent.

All products, prices, orders and store policies are invented for this tutorial. No real customer system, courier, payment provider, email service or staff inbox is connected.

## Start the app

From the repository root, run:

```powershell
python -m pip install -r requirements.txt
python -m support_app
```

Open **http://127.0.0.1:8080** in your browser. Keep the terminal running. Ctrl+C stops it. If port 8080 is occupied, use `python -m support_app --port 8081` and open that port instead.

The application reads your existing root `.env`. Your existing `open_router` key name is accepted. When the key is present, AI replies are enabled; all LLM requests use the existing free-model guard. If a provider request fails, the interface explicitly shows direct support-guide excerpts instead of silently presenting them as AI generation.

For an entirely local demonstration with no model or speech requests:

```powershell
python -m support_app --offline
```

The browser's **AI replies** toggle also lets you choose local guide excerpts for individual conversations. Offline server mode overrides the toggle and disables voice, even if credentials exist.

No frontend build step or Node installation is needed. The interface is HTML, CSS and JavaScript. Text mode has no external frontend dependencies. The LiveKit browser SDK is fetched lazily from a versioned CDN URL only when you start voice.

## What to try

| Action | Expected result |
|---|---|
| Ask “What is your return policy?” | A policy answer with a clickable source article |
| Ask “ما سياسة الإرجاع؟” | The Arabic policy and its source |
| Open My orders, then ask about NR-1042 | Shipped status from the demo order record |
| Ask “Can I cancel NR-1042?” | Actual demo status plus the cancellation policy; no cancellation is performed |
| Ask about order NR-9999 | No matching order; no invented tracking details |
| Ask how to pair Noura Air headphones | Steps from the product guide |
| Ask who won a lunar chess tournament | An explicit knowledge gap and an offer to create a request |
| Open Knowledge base and search | Search the same ten articles used by the assistant |
| Create a request | A local ticket ID appears under My requests |
| Refresh the page | Conversation and requests persist for the browser session |
| Switch to Arabic | Right-to-left navigation, Arabic articles and UI |

Tickets are saved locally. The application does **not** send an email or promise a real staff response. Attaching the last 12 messages is a separate checkbox, unchecked by default. Repeating the same ticket submission identifier returns the same ticket rather than creating a duplicate.

## Enable LiveKit voice

Voice is an optional second process. Text, knowledge search, order tracking and ticket creation work without it.

Install the dependencies:

```powershell
python -m pip install -r requirements-livekit.txt
python -m examples.munsit_transcribe --select-voice Mansour
```

Configure the root `.env`, preserving your existing keys:

```dotenv
OPENROUTER_MODEL=openrouter/free
MUNSIT_API_MODE=current
MUNSIT_STT_MODEL=munsit-en-ar
MUNSIT_TTS_MODEL=faseeh-v1-preview
# The selection command saves MUNSIT_VOICE_ID automatically.

# Enable only when you intend to use your Munsit speech allowance/credits.
ENABLE_MUNSIT_BILLING=true

LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_key
LIVEKIT_API_SECRET=your_livekit_secret
```

Alternatively, run `livekit-server --dev` in a separate terminal and use `ws://127.0.0.1:7880`, `devkey`, and `secret` for **local development only**. See [LiveKit's local-server guide](https://docs.livekit.io/transport/self-hosting/local/). A LiveKit server and the Python voice worker are separate processes.

Prepare model assets, then start the voice worker:

```powershell
python -m support_app.voice_agent download-files
python -m support_app.voice_agent dev
```

In another terminal, run the web app without `--offline`:

```powershell
python -m support_app
```

Restart both processes after editing `.env`, and refresh the browser. Click **Start a voice chat**, grant microphone permission, wait for Noor to join, and speak. Use headphones. You can mute the microphone or end the call. If browser autoplay is blocked, use **Enable audio playback**.

The backend issues a short-lived token restricted to the session's own room and includes a dispatch for `noura-support`. You do not need the manual `room_access dispatch` command used by the examples. Tokens and provider secrets are different: the browser receives a room token, never provider API keys.

Calls have a five-minute limit in both the frontend and voice worker. The end-call endpoint deletes only the current session's room. If room cleanup fails, the UI reports it; check the worker rather than assuming a provider has stopped billing. Reloading or closing the tab relies on disconnect handling and the worker's time limit.

Munsit STT/TTS, LiveKit hosting, and network infrastructure can have separate costs. `openrouter/free` only controls the language-model route. The app does not silently switch to a paid model or enable search plugins.

The voice agent has two read-only tools:

- `search_support_knowledge(question)` retrieves the same articles used by text support and sends source links to the frontend.
- `get_order_status(order_number)` looks up only the demo customer assigned to that session.

Voice transcript events are persisted to the same local conversation record. After a call ends, the frontend reloads those records. The text and voice models do not share an in-memory model session; the text backend can use recent saved messages, while a new voice call starts with fresh model context. Voice source links are live UI hints and are not currently persisted alongside each transcript.

## How the application works

```text
Browser: responsive HTML/CSS/JavaScript
  |
  +-- JSON API -> Python backend -> SQLite sessions/messages/tickets
  |                    |
  |                    +-- bilingual lexical retrieval -> knowledge.json
  |                    +-- demo order lookup (customer-scoped)
  |                    +-- free OpenRouter LLM -> validated source IDs
  |
  +-- room token -> LiveKit WebRTC room -> Python voice worker
                                             |
                                             +-- Munsit STT / TTS
                                             +-- free OpenRouter LLM
                                             +-- the same knowledge and order tools
```

### Retrieval and grounded answers

`knowledge.py` normalizes Arabic letter forms and diacritics and adds simple English plural variants. It ranks keyword, title and body matches with inverse-frequency weighting. At least one subject/title match is required; unrelated questions do not go to the LLM. Short follow-ups can reuse the previous user question as retrieval context.

When AI replies are enabled, `service.py` sends only the selected articles, the current question, and a small recent conversation window to OpenRouter. It asks for JSON containing an answer and source IDs. The backend accepts only IDs from the actual retrieved articles. Invalid responses, missing citations and provider errors fall back to clearly labelled guide excerpts.

This is a small lexical RAG system, not vector search. A valid citation ID does not prove that every generated sentence is correct. Free-model quality and availability vary; test known answers, ambiguity and adversarial questions. Voice grounding is instruction/tool-based and does not have the text route's JSON validation gate.

### Backend API

| Method and path | Behavior |
|---|---|
| `GET /api/bootstrap` | Create/resume an anonymous demo session; return configuration and session data |
| `GET /api/health` | Local health check |
| `GET /api/messages` | Read this browser session's conversation |
| `POST /api/chat` | Retrieve knowledge, answer, and save both turns |
| `POST /api/conversation/clear` | Clear this session's messages; retain tickets |
| `GET /api/tickets` | Read this session's saved requests |
| `POST /api/tickets` | Validate and save an idempotent local support request |
| `POST /api/voice/token` | Issue a room-scoped JWT with named-agent dispatch |
| `POST /api/voice/end` | Close this session's LiveKit room |

The server uses Python's standard-library threaded HTTP server so the existing environment can run the full demo without another framework installation. It binds to loopback only, checks Host/Origin, requires a CSRF token on writes, uses an HttpOnly/SameSite cookie, validates payload sizes, and rate-limits writes per session. Its static-file route is an explicit allowlist, so `.env` is never served.

This is **a local teaching application, not a production deployment**. Browser sessions isolate conversations and tickets, but the customer identity is a deliberately fixed demo account. Before handling real customers, replace it with authentication and tenant authorization, move to a production ASGI/WSGI server behind HTTPS, add secure cookies and distributed rate limits, configure retention/deletion, use a managed datastore, and add audited integrations for any real order changes. Do not expose the built-in HTTP server publicly.

### Local storage

The default database is `support_app/runtime/support.sqlite3`, ignored by Git. Sessions expire after seven days for access purposes; old rows are **not automatically purged**. Define a purge policy before storing real data. Clearing a chat leaves any transcript already attached to a ticket intact.

For an isolated demo database:

```powershell
python -m support_app --offline --db .\support_app\runtime\demo.sqlite3
```

If you use a custom database with voice, set the same absolute path as `SUPPORT_DB` in the worker's environment. Otherwise the worker cannot resolve the browser session.

## Customize the company knowledge

Edit [knowledge.json](knowledge.json). Each article has a stable `id`, category, English/Arabic titles and bodies, and retrieval keywords. Restart the web server and voice worker after changes. Keep policies consistent across languages. Avoid placing secrets or real customer data in articles because they are public in the frontend.

Replace the fixtures in [store.py](store.py) with a customer-authorized order service when ready. Do not accept a customer ID from the browser and trust it. Authorization belongs on the backend and inside agent tools.

## Code map

| File | Responsibility |
|---|---|
| [static/index.html](static/index.html) | Four app views and accessible dialogs |
| [static/style.css](static/style.css) | Responsive layouts, RTL and product illustrations |
| [static/app.js](static/app.js) | UI state, API calls, source links, forms and LiveKit client |
| [server.py](server.py) | Local HTTP API, session checks and room credentials |
| [service.py](service.py) | Retrieval, model calls, citation validation and fallback |
| [knowledge.py](knowledge.py) | Bilingual lexical search |
| [knowledge.json](knowledge.json) | Ten original fictional support articles |
| [store.py](store.py) | SQLite persistence and demo order fixtures |
| [voice_agent.py](voice_agent.py) | LiveKit/Munsit worker and read-only tools |
| [test_support.py](test_support.py) | Offline API integration tests |

## Validation

```powershell
python -m unittest support_app.test_support -v
python -m unittest discover -s tests -v
python -m compileall -q support_app
node --check support_app/static/app.js
```

Node is only needed for the optional JavaScript syntax check. The offline tests mock provider calls; a live voice session needs configured LiveKit and Munsit credentials.

Official integration references: [LiveKit dispatch](https://docs.livekit.io/agents/server/agent-dispatch/), [LiveKit browser SDK](https://docs.livekit.io/reference/client-sdk-js/), [Munsit voice catalogue](https://docs.munsit.com/text-to-speech/voices), [Munsit LiveKit plugin](https://docs.munsit.com/integrations/livekit), [OpenRouter free routing](https://openrouter.ai/docs/guides/routing/routers/free-router).

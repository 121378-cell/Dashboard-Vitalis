# Agent Context — ATLAS Project

Full-stack AI Fitness Dashboard integrating Garmin and wger data, with a mobile Android companion via Capacitor.

## Tech Stack Overview
- **Frontend**: React 19 + TypeScript + Vite 6 + Tailwind CSS 4 + Recharts + Motion + TanStack Query + Zustand
- **Backend**: FastAPI (Python 3.12+) — Pydantic v2, SQLAlchemy (SQLite), async ORM
- **Mobile**: Capacitor with `capacitor-health` plugin (Health Connect)
- **AI Provider Chain**: Groq (Groq API: `llama-3.3-70b-versatile` → Gemini (`gemini-2.0-flash`) → Ollama local

## Project Structure

```
├── src/
│   ├── components/         # Domain folders: analytics, biometrics, chat, dashboard, nutrition, plan, recovery, training, ui
│   ├── hooks/              # TanStack Query hooks + WebSocket + device APIs + tests in __tests__/
│   ├── services/           # API clients (garmin, biometrics, healthConnect, planner, etc.)
│   ├── store/              # Zustand global state → atlasStore.ts
│   ├── pages/              # Route views: Overview, Biometrics, Training, Readiness, Coach, Memory, Plan
│   ├── App.tsx             # BrowserRouter with QueryClientProvider + Zustand
│   └── main.tsx            # StrictMode entry point
├── backend/
│   ├── app/
│   │   ├── api/api_v1/endpoints/   # Feature-organized REST + WebSocket endpoints
│   │   ├── core/            # Pydantic settings, auth, readiness engine, rate limiter
│   │   ├── db/              # SQLAlchemy session & models (session.py, base.py)
│   │   ├── models/          # ORM: User, Biometrics, Workout, TrainingPlan, Session, Memory, Nutrition, Community…
│   │   ├── services/        # Business logic: Garmin sync, AI coach, readiness, training plan, athletic intelligence, etc.
│   │   ├── training/        # Domain-driven training subsystem (separate API + domain models)
│   │   └── utils/           # Garmin wrappers, training plan optimizer
│   ├── tests/
│   │   ├── unit/            # Pytest unit tests
│   │   ├── test_critical_paths.py   # MUST pass before deploy
│   │   ├── test_garmin_connection.py
│   │   └── verify_integration.py
│   ├── requirements.txt
│   └── fly.toml             # Fly.io deployment config
├── capacitor.config.ts     # Capacitor config
├── vite.config.ts          # Dev proxy /api/v1 → localhost:8005
└── tsconfig.json            # @ alias maps root "."
```

## Dependencies

Key frontend packages:
- `motion` (Framer Motion): animations
- `recharts`: charts
- `lucide-react`: icons
- `zustand`: global state
- `@tanstack/react-query`: data fetching & caching
- `react-router-dom`: routing
- `react-markdown`: rendering AI responses
- `react-loading-skeleton`: loading UI
- `@capacitor/*`: Capacitor core + Android + local notifications
- `capacitor-health`: plugin for Google Health Connect
- `dexie`: IndexedDB wrapper for offline storage
- `@google/genai`: Gemini API SDK
- `html2canvas`: screenshot / export charts
- `xlsx`: Excel data export

Backend packages in `requirements.txt`:
- `fastapi>=0.111.0`, `uvicorn>=0.30.0`, `gunicorn>=22.0.0`
- `SQLAlchemy>=2.0.30`, `alembic>=1.13.0`
- `pydantic-settings>=2.3.0`, `python-dotenv>=1.0.0`
- `google-genai>=1.0.0`, `openai>=1.35.0`
- `garminconnect>=0.2.19`, `garth>=0.4.45`
- `pandas>=2.2.0`, `numpy>=1.26.0`
- `apscheduler>=3.10.0`
- `plyer>=2.1.0`

## Build & Development

| Command | Purpose |
|---------|---------|
| `npm install` | Installs deps & patches (patch-package postinstall) |
| `npm run dev` | Vite dev server, proxies `/api/v1` → `localhost:8005` |
| `npm run dev:backend` | FastAPI backend with hot reload on port 8005 |
| `npm run build` | Production frontend build |
| `npm run preview` | Preview production build |
| `npm run lint` | TypeScript type check (`tsc --noEmit`) |
| `npm run test` | Vitest frontend tests (jsdom env) |
| `npm run test:watch` | Vitest in watch mode |
| `cap:sync` / `cap:android` / `cap:build` | Capacitor sync & open Android Studio |
| `build:android` | PowerShell script to build APK |

## Backend Environment & AI

The backend uses `.env` in `backend/` with these keys (verified via `app/core/config.py`):
- `GROQ_API_KEY` — **primary AI provider** (model: `llama-3.3-70b-versatile`, 10s timeout)
- `GEMINI_API_KEY` — fallback (model: `gemini-2.0-flash`)
- `OLLAMA_BASE_URL` — local fallback (default: `http://localhost:11434`)
- `DATABASE_URL` — SQLite path (default: `sqlite:///backend/atlas_v2.db`)
- `GARMIN_EMAIL`, `GARMIN_PASSWORD` — Garmin Connect credentials
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — Telegram bot notifications
- `NOTIFICATIONS_ENABLED` (default true)

### Running backend locally from `backend/`:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

### Testing Backend
Run all tests:
```bash
pytest backend/tests/ -v --tb=short
```
Critical paths (runs in CI before deploy):
```bash
pytest backend/tests/test_critical_paths.py -v --tb=short
```

## Key Architecture Notes

### Frontend
- **Entry**: `src/main.tsx` → `src/App.tsx` (BrowserRouter + QueryClientProvider + Zustand store)
- **State**: Zustand store (`src/store/atlasStore.ts`) persisted to localStorage (chat history, briefing, memories)
- **API layer**: `src/services/api.ts` — axios instance with interceptors for auth + error handling
  - Default user header: `x-user-id: default_user`
  - BaseURL from `src/config.ts`: `http://localhost:8005/api/v1`
- **WebSocket**: `/api/v1/ws/readiness` for live readiness updates + `/ws/notifications` for push notifications
- **Health Connect**: `capacitor-health` plugin wrapped in `src/services/healthConnectService.ts`
- **Offline**: `dexie` for localIndexedDB + service workers

### Backend
- **Entry**: `backend/app/main.py` (FastAPI lifespan: init tables + bootstrap default_user)
- **DB**: SQLAlchemy with SQLite (`atlas_v2.db`). WAL mode enabled via `PRAGMA` for concurrency. See `backend/app/db/session.py`
- **Models**: All ORM defined in `backend/app/models/` — imported in `db/base.py` to auto-register
- **API routing**: `backend/app/api/api_v1/api.py` — prefixed `/api/v1` (configured in `config.py`)
- **AI chat endpoint**: `POST /api/v1/ai/chat` — uses `build_coach_context()` which gathers biometric, training, injury, ACWR, memory, and exercise data into a rich system prompt for the AI coach
- **Services**: Each `.service` is a class with static methods (e.g. `ReadinessService.calculate()`, `AIService.chat()`)
- **Training subsystem**: Separate domain in `backend/app/training/` with its own API, domain models, schemas, use cases
- **Scheduler**: `app/services/scheduler_service.py` → started in FastAPI lifespan, used for daily syncs

## Commit Style

Mixed English/Spanish. Messages are predominantly descriptive (e.g. `fixeo de errores`, `DATA SYNC COMPLETO`) with occasional conventional prefixes (`feat:`, `fix:`, `chore:`). Keep messages concise and informative.

## Known Quirks

- **AI Studio / HMR**: Vite HMR is disabled in AI Studio (`DISABLE_HMR=true`). Do not enable file watching during agent edits — it causes flickering.
- **Capacitor patches**: `postinstall` applies patches via `patch-package`. If it fails, must manually `git apply patches/*.patch`
- **Fly.io deploy**: Backend autodeploys on push to `main` if `backend/**` changes. Tests (`test_critical_paths.py`) run first in CI.
- **Token upload**: Garmin OAuth tokens are uploaded to Fly.io via a manual workflow (`.github/workflows/upload-garmin-tokens.yml`) — not auto-managed
- **One user**: The app is single-user (`default_user`) — hardcoded in frontend API layer and backend `user_id` defaults
- **No Ruff / Pyproject.toml**: Python linting is not configured in root. Use `pytest` for validation.
- **Backend `.env` vs root `.env`**: Root `.env` only has `GROQ_API_KEY` for frontend Vite injection. Backend `.env` has the full config (AI, DB, Telegram, Garmin).
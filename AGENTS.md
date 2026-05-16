# Repository Guidelines

Full-stack AI Fitness Dashboard (ATLAS) integrating Garmin, biometric, and training data with a mobile Android companion via Capacitor. Single-user app (`default_user` hardcoded in frontend API layer and backend user defaults).

## Architecture Overview

- **Frontend** (`src/`): React 19 + TypeScript + Vite 6 + Tailwind CSS 4. Entry: `main.tsx` → `App.tsx` (BrowserRouter + TanStack Query + Zustand). API layer via `src/services/api.ts` (axios, sends `x-user-id: default_user`). Dev server proxies `/api/v1` → `localhost:8005`.
- **Backend** (`backend/`): FastAPI (Python 3.12+) + SQLAlchemy + SQLite (WAL mode). Entry: `app/main.py`. API prefix `/api/v1`. AI coach at `POST /api/v1/ai/chat` — context assembled from biometrics, training, injuries, memories. Training subsystem in `app/training/` has its own domain models and use cases.
- **Mobile**: Capacitor (`capacitor.config.ts`) + `capacitor-health` plugin. Patches applied via `patch-package` on `postinstall`.
- **AI Provider Chain**: Primary is Gemini (`gemini-2.0-flash`) via `@google/genai` on the frontend. Backend also supports Groq (`llama-3.3-70b-versatile`) and Ollama (local fallback) via dedicated services.

## Build, Test, and Development Commands

| Command | Purpose |
|---------|---------|
| `npm install` | Install deps + apply Capacitor patches |
| `npm run dev` | Vite dev server (proxies `/api/v1` → `localhost:8005`) |
| `npm run dev:backend` | FastAPI at port 8005 with hot reload |
| `npm run build` | Production frontend build |
| `npm run lint` | TypeScript type check (`tsc --noEmit`) |
| `npm run test` | Vitest frontend tests (jsdom env) |
| `npm run test:watch` | Vitest watch mode |
| `npm run cap:sync` / `cap:android` / `cap:build` | Capacitor sync & open Android Studio |
| `npm run build:android` | PowerShell script to build APK |
| `pytest backend/tests/ -v --tb=short` | Run all backend tests |
| `pytest backend/tests/test_critical_paths.py -v --tb=short` | CI-critical (must pass before deploy) |

## Development Quirks & Gotchas

- **HMR is disabled in AI Studio**: The `DISABLE_HMR` env var is set in the AI Studio environment. Do not modify the Vite config's `hmr` check — it's there to prevent flickering during agent edits.
- **Backend `.env` is required**: The backend loads its config from `backend/.env`. Copy `.env.example` to `backend/.env` and fill in values. Never commit `.env` files.
- **FERNET_KEY is critical**: Used to encrypt sensitive credentials (Garmin, etc.) in the database. Generate once with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and never change it, or encrypted data will be lost.
- **Capacitor patches**: `patch-package` runs on `postinstall`. If patches fail, manually apply with `git apply patches/*.patch`.
- **Database**: SQLite with WAL mode. Database file is `backend/atlas_v2.db`. Migrations are handled automatically on startup in `app/main.py` lifespan.
- **CORS origins are hardcoded**: In `app/main.py`, exact origins are listed (no wildcards). If deploying to a new frontend domain, add it to the `origins` list.
- **Backend deploy**: Auto-deploys to Fly.io on pushes to `main` that touch `backend/**`. CI runs all tests first, then critical paths, then deploys.

## Coding Style & Naming Conventions

- **TypeScript**: Checked via `tsc --noEmit`. No ESLint or Prettier configs — compiler is the sole enforcer.
- **Python**: No Ruff, flake8, or `pyproject.toml`. Validation via `pytest` only.
- **Naming**: PascalCase for React components, `use` prefix for hooks (e.g., `useAnalytics`, `useDashboardData`). Backend services use static methods (e.g., `ReadinessService.calculate()`).
- **Imports**: Frontend uses `@/` path alias mapping to project root (`tsconfig.json`).

## Testing Guidelines

- **Frontend**: Vitest with jsdom environment. Tests in `src/hooks/__tests__/` and `src/**/*.{test,spec}.{js,ts}`. Run with `npm run test`.
- **Backend**: Pytest. Critical path tests (`test_critical_paths.py`) must pass before deployment.

## Commit Guidelines

Mixed English/Spanish convention. Messages are predominantly descriptive (e.g., `fixeo de errores`, `DATA SYNC COMPLETO`, `AUDITORÍA`) with occasional conventional prefixes (`feat:`, `fix:`, `chore:`). Keep concise and informative.

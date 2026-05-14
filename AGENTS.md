# Repository Guidelines

Full-stack AI Fitness Dashboard (ATLAS) integrating Garmin, biometric, and training data with a mobile Android companion via Capacitor. Single-user app (`default_user` hardcoded in frontend API layer and backend user defaults).

## Project Structure & Module Organization

- **Frontend** (`src/`): React 19 + TypeScript + Vite 6 + Tailwind CSS 4. Entry: `main.tsx` → `App.tsx` (BrowserRouter + TanStack Query + Zustand). API layer via `src/services/api.ts` (axios, sends `x-user-id: default_user`). Dev server proxies `/api/v1` → `localhost:8005`.
- **Backend** (`backend/`): FastAPI (Python 3.12+) + SQLAlchemy + SQLite (WAL mode). Entry: `app/main.py`. API prefix `/api/v1`. AI coach at `POST /api/v1/ai/chat` — context assembled from biometrics, training, injuries, memories. Training subsystem in `app/training/` has its own domain models and use cases.
- **Mobile**: Capacitor (`capacitor.config.ts`) + `capacitor-health` plugin. Patches applied via `patch-package` on `postinstall`.
- **AI Provider Chain**: Groq (`llama-3.3-70b-versatile`) → Gemini (`gemini-2.0-flash`) → Ollama (local fallback).

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

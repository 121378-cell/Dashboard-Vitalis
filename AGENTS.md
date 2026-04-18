# Repository Guidelines

## Project Structure & Module Organization
This project is a full-stack AI Fitness Dashboard integrating Garmin and wger data.
- **Frontend**: React application built with TypeScript and Vite.
  - `src/components`: UI components using Tailwind CSS and Framer Motion.
  - `src/hooks`: Custom React hooks for state and data management.
  - `src/services`: API clients for frontend-backend communication.
  - `src/types.ts`: Global TypeScript interfaces.
- **Backend**: Python FastAPI application in `backend/`.
  - `backend/app/api/api_v1`: Endpoint definitions organized by feature (auth, workouts, biometrics, ai, etc.).
  - `backend/app/core`: Configuration and global settings using Pydantic.
  - `backend/app/db`: Database session management (SQLAlchemy with SQLite).
  - `backend/app/models`: SQLAlchemy database models (User, Token, Biometrics, Workout).
  - `backend/app/services`: Core business logic and external API integrations.
  - `backend/app/utils`: Helper functions and sync utilities.

## Build, Test, and Development Commands
Commands are managed via `npm` in the root `package.json`:
- `npm install`: Installs all frontend and backend dependencies using the shared `package.json`.
- `npm run dev`: Starts the Vite development server for the frontend (React/TypeScript/Tailwind).
- `npm run dev:backend`: Starts the FastAPI backend server with hot reload, accessible via `uvicorn app.main:app --reload --app-dir backend`. Note: The API entry point is `backend/app/main.py`.
- `npm run build`: Builds optimized production assets for the frontend.
- `npm run lint`: Runs TypeScript type checking (`tsc --noEmit`). For backend linting, use dedicated Python tests/scripts within `backend/tests/` or `ruff`.

## Coding Style & Naming Conventions
- **Frontend**: TypeScript (ESNext), Functional React components, Tailwind CSS. Aliases use `@/` for root.
- **Backend**: Python 3.12+, Pydantic v2, SQLAlchemy for ORM.
- **Naming**: `CamelCase` for components/types, `camelCase` for JS/TS variables, `snake_case` for Python.
- **Linting**: Ruff (Python) and `tsc` (TypeScript) are the primary linting/validation tools.

## Testing Guidelines
- Backend tests are in `backend/tests/`.
- Includes unit tests and verification scripts for integrations (e.g., `verify_integration.py`, `test_garmin_connection.py`).

## Commit & Pull Request Guidelines
- Follow existing patterns: `feat:`, `fix:`, or descriptive Spanish labels (e.g., `inicio aplicación`, `AUDITORIA`).
- Keep commit messages concise and informative.

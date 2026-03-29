# Investigation Report - 404 Not Found Endpoints

## Bug Summary
Several API endpoints are returning `404 Not Found` when accessed via the frontend or direct API calls:
- `GET /api/v1/auth/status`
- `GET /api/v1/settings/services`
- `GET /api/v1/workouts`
- `POST /api/v1/auth/garmin/login`

## Root Cause Analysis
The investigation revealed that there are two conflicting `app` directories in the repository:
1. `c:\Users\sergi\Nueva carpeta\Dashboard-Vitalis\app` (Root level)
2. `c:\Users\sergi\Nueva carpeta\Dashboard-Vitalis\backend\app` (Inside backend directory)

The `npm run dev:backend` script uses the following command:
`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend`

When using `python -m uvicorn`, Python's module resolution system finds the root-level `app` package before considering the one in the `backend` directory, even with `--app-dir backend`. 

The root-level `app/main.py` is a simplified version of the API that **does not include** the `/api/v1` routes. It only defines `/` and `/health`.

The `backend/app/main.py` is the correct one that includes all the required routers:
```python
app.include_router(api.api_router, prefix=settings.API_V1_STR)
```
where `settings.API_V1_STR` is `/api/v1`.

## Affected Components
- `package.json`: The `dev:backend` script is incorrectly invoking `uvicorn`.
- Directory Structure: Having two packages named `app` in the same project root causes resolution conflicts.

## Proposed Solution
1. **Rename the root-level `app` directory**: This is the cleanest solution to avoid name collisions in the Python path.
2. **Update `package.json`**: Change the `dev:backend` script to call `uvicorn` directly without the `python -m` prefix if possible, or ensure the correct path is used.
   - Recommended command: `uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --app-dir backend` (using port 8001 as 8000 might be occupied).
3. **Verify Port usage**: The `backend/app/core/config.py` specifies `PORT: int = 8001`, but `package.json` uses `8000`. They should be synchronized.

## Implementation Results

### Changes Made:
1. **Renamed root-level `app` directory** to `app_backup_v2`
2. **Updated `Start-Vitalis.ps1`** to:
   - Check for `backend/app/main.py` instead of `app/main.py`
   - Change working directory to `backend` before starting uvicorn

### Verification Results:
After the fix, all endpoints return HTTP 200 OK:
- `GET /api/v1/auth/status` → `200 OK` `{"authenticated": true}`
- `GET /api/v1/settings/services` → `200 OK` `{"wger_api_key": null, "hevy_username": "mock_hevy_user"}`
- `GET /health` → `200 OK` `{"status": "ok"}`

### Root Cause Confirmed:
Python's module resolution was finding the root-level `app` package first, which only had basic endpoints (`/`, `/health`), instead of `backend/app` which contains all API routes.

### Status: ✅ FIXED

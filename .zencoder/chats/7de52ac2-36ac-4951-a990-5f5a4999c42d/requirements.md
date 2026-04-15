# Product Requirements Document (PRD): Fix Garmin Synchronization Issue

## 1. Problem Statement
The Garmin synchronization feature in the Dashboard-Vitalis project is currently failing. The primary cause is a combination of hitting Garmin's strict API rate limits (HTTP 429) and bugs in the backend implementation that cause redundant and incorrect calls to the Garmin client.

### 1.1 Identified Issues
- **Redundant API calls**: `SyncService.sync_garmin_health` and `SyncService.sync_garmin_activities` both call `get_garmin_client` twice.
- **Incorrect unpacking**: The first call to `get_garmin_client` in these functions assigns the returned tuple `(client, session_updated)` to a single variable `client`, causing subsequent method calls on `client` to fail because it's a tuple.
- **Session Persistence**: Redundant calls and potential failures in resuming sessions from disk/database force unnecessary fresh logins, which are heavily rate-limited by Garmin.
- **Rate Limit (429) errors**: Garmin's SSO and API endpoints are blocking requests due to too many login/request attempts.

## 2. Goals
- Eliminate redundant and incorrect calls to `get_garmin_client` in the backend.
- Optimize session management to favor session resumption over fresh logins.
- Improve error handling and user feedback when rate limits are hit.
- Ensure the synchronization process is robust and follows Garmin's best practices for API usage.

## 3. Functional Requirements
### 3.1 Backend Fixes
- **Refactor `SyncService.sync_garmin_health`**: Remove the redundant call to `get_garmin_client` and correctly unpack the returned tuple.
- **Refactor `SyncService.sync_garmin_activities`**: Remove the redundant call to `get_garmin_client` and correctly unpack the returned tuple.
- **Enhance `get_garmin_client`**: Improve the reliability of session resumption from the database and disk.
- **Unified Error Handling**: Implement specific exceptions for Garmin rate limiting and authentication errors that are consistently caught and reported by the API.

### 3.2 Frontend Improvements
- **Clearer Rate Limit Messages**: Inform the user specifically when a Garmin rate limit is hit and provide a suggested wait time (e.g., 30-60 minutes).
- **Sync Status Feedback**: Better visibility into why a sync failed (e.g., "Credenciales incorrectas" vs "Bloqueo por exceso de intentos").

## 4. Technical Requirements
- **Language**: Python 3.12+ (Backend), TypeScript/React (Frontend).
- **Libraries**: `garth`, `garminconnect` (for Garmin integration).
- **Persistence**: SQLite (via SQLAlchemy) for storing session tokens and credentials.

## 5. Success Criteria
- The `test_garmin_connection.py` script passes successfully (when not rate-limited).
- The `SyncService` methods no longer contain redundant or incorrect `get_garmin_client` calls.
- Garmin synchronization successfully retrieves health stats and activities and stores them in the database.
- The UI correctly displays the reason for failure when synchronization cannot be completed.

## 6. Assumptions and Constraints
- **Rate Limits**: Even with optimized code, Garmin's rate limits are beyond our control. The goal is to minimize the chances of hitting them.
- **User Credentials**: We assume the user provides valid Garmin credentials.
- **Storage**: The backend environment must have a writable directory for storing session tokens (managed via `GARMIN_TOKEN_DIR`).

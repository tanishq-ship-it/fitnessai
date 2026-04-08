# Wi-Fi / Local Network Setup

This project uses a React Native Expo frontend and a FastAPI backend.

When testing on a physical phone, the phone must be able to reach the backend over the local network. If the laptop IP changes after switching Wi-Fi, the frontend may point to the wrong backend address and login/chat requests can fail.

## What Happened Before

The frontend was trying to use an old local IP:

- old backend host: `192.168.1.5`
- current backend host at the time of fix: `192.168.0.118`

Because of that mismatch:

- login could stay loading
- chat could show `Network request failed`
- the app could appear fine in Expo, but API calls would never complete

## Current Setup

The frontend now supports two ways to resolve the backend API URL:

1. Explicit override from `frontend/.env`
2. Expo host auto-detection from `frontend/src/constants/api.ts`

Current override:

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.0.118:8000/api
```

Important:

- if `frontend/.env` has `EXPO_PUBLIC_API_BASE_URL`, that value wins
- if it is removed, the frontend falls back to Expo host detection

Relevant files:

- [frontend/.env](/Users/tanishqbhosale/Desktop/projects/fitnessai/frontend/.env)
- [frontend/src/constants/api.ts](/Users/tanishqbhosale/Desktop/projects/fitnessai/frontend/src/constants/api.ts)
- [frontend/src/services/auth-service.ts](/Users/tanishqbhosale/Desktop/projects/fitnessai/frontend/src/services/auth-service.ts)

## Backend Requirement

The backend must listen on all interfaces, not just localhost.

Use:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Do not use a localhost-only bind when testing on a phone.

## Standard Dev Checklist

1. Make sure laptop and phone are on the same Wi-Fi.
2. Start the backend on `0.0.0.0:8000`.
3. Confirm the backend health endpoint works on the laptop LAN IP.
4. Start or restart Expo.
5. Open the app on the phone.

## How To Find Your Current Laptop IP

On macOS:

```bash
ifconfig | rg "inet 192\\.|inet 10\\.|inet 172\\.(1[6-9]|2[0-9]|3[0-1])\\."
```

Look for a local IP such as:

- `192.168.x.x`
- `10.x.x.x`
- `172.16.x.x` to `172.31.x.x`

Example from the last fix:

- `192.168.0.118`

## How To Check The Backend Is Reachable

After finding the laptop IP, test the backend:

```bash
curl http://127.0.0.1:8000/api/health
curl http://YOUR_LAPTOP_IP:8000/api/health
```

Expected response:

```json
{"status":"ok"}
```

If localhost works but LAN IP does not, the issue is usually:

- backend not started with `--host 0.0.0.0`
- firewall/network isolation
- wrong laptop IP

## What To Do When Wi-Fi Changes

If you switch to another Wi-Fi, your laptop IP may change.

When that happens:

1. Find the new laptop IP.
2. Update `frontend/.env`.
3. Replace the old value:

```env
EXPO_PUBLIC_API_BASE_URL=http://NEW_IP:8000/api
```

4. Restart Expo so the new env value is loaded.
5. Reload the app on the phone.

Recommended restart:

```bash
cd frontend
npx expo start -c
```

The `-c` clears cache and avoids the phone using an older bundle.

## Why Login Looked Like It Was Stuck

The auth request was trying to reach the wrong backend host. The login screen showed a loader because the request did not complete quickly.

To make this fail more clearly in the future, auth requests now have a timeout in `frontend/src/services/auth-service.ts`.

If the backend is unreachable, the app should now fail with a timeout error instead of spinning indefinitely.

## Common Symptoms And Causes

### Symptom: Login keeps loading

Usually caused by:

- wrong API base URL
- Expo still serving an old bundle
- backend unreachable from phone

### Symptom: Chat says `Network request failed`

Usually caused by:

- backend IP changed
- phone is not on the same Wi-Fi
- backend process is not running

### Symptom: Works on laptop browser but not on phone

Usually caused by:

- backend only listening on localhost
- LAN IP not reachable

## Fast Recovery Steps

If the app suddenly stops connecting:

1. Check backend is running:

```bash
curl http://127.0.0.1:8000/api/health
```

2. Find current laptop IP.
3. Check LAN reachability:

```bash
curl http://YOUR_LAPTOP_IP:8000/api/health
```

4. Update `frontend/.env` if needed.
5. Restart Expo with cache clear:

```bash
npx expo start -c
```

6. Reload the app on the phone.

## If You Want Less Manual Work Later

Current setup is intentionally simple and reliable for development.

If manual IP updates become annoying later, possible next improvements are:

- add an in-app dev backend URL setting
- show the active API base URL somewhere in the app
- add a small connection test screen
- support a local hostname instead of raw IP if your network setup allows it

For now, the simplest reliable rule is:

`when Wi-Fi changes, verify laptop IP, update frontend/.env, restart Expo`

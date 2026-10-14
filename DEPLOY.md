# Deploying the backend to Railway

1. Push this repo to a **private** GitHub repo (secrets are gitignored:
   `google-ads.yaml`, `gtm-credentials.yaml`, `client_secret*.json`).
2. Railway project -> New -> GitHub Repo -> pick it. Railway builds the
   `Dockerfile` automatically.
3. Add a **Volume** to the service, mount path `/data`.
4. Service -> Variables:
   - `APP_PASSWORD`  your login password (long, unique)
   - `SESSION_SECRET`  any long random string
   - `NTFY_TOPIC`  long random string; subscribe to it in the ntfy phone app
   - `PUBLIC_URL`  the service's public URL (Settings -> Networking -> Generate Domain)
   - (later phases) `ANTHROPIC_API_KEY`, Google Ads / GTM credentials
5. Open the public URL, sign in, check projects appear.

Local run: `ALLOW_NO_AUTH=1 venv/bin/python -m uvicorn server.app:app --port 8788`
(or the `campaign-builder-backend` entry in `.claude/launch.json`, which
uses throwaway copies of the data so testing never touches real projects).

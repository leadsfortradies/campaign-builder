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
   - `ANTHROPIC_API_KEY`  from console.anthropic.com -> API Keys
   - `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`,
     `GOOGLE_ADS_LOGIN_CUSTOMER_ID`  copy the matching values out of the local
     `google-ads.yaml` (client_id, client_secret, refresh_token, login_customer_id)
   - `GITHUB_TOKEN`  fine-grained token for the `leadsfortradies` account (all repositories; Administration
     + Contents: read and write). Landing page builds create a private repo per client.
   - `NETLIFY_AUTH_TOKEN`  Netlify personal access token (User settings > Applications). Landing pages deploy
     to a new Netlify site per client.
   - optional: `GITHUB_OWNER` (default `leadsfortradies`), `LP_TEMPLATE_REPO` (default
     `leadsfortradies/site-template`), `NETLIFY_ACCOUNT_SLUG` (team slug if sites should go in a team)
   - optional: `PROJECT_TOKEN_CAP` (default 4,000,000 Claude tokens per campaign),
     `DEFAULT_MODEL`, `GOOGLE_ADS_CUSTOMER_ID` (Keyword Planner account)
5. Open the public URL, sign in, check projects appear.

Local run: `ALLOW_NO_AUTH=1 venv/bin/python -m uvicorn server.app:app --port 8788`
(or the `campaign-builder-backend` entry in `.claude/launch.json`, which
uses throwaway copies of the data so testing never touches real projects).

# Google Ads Campaign Builder

Goal: eventually, "build me a Google Ads campaign for XYZ" triggers a repeatable
process. Step 1 (in progress): automated keyword research via the Google Ads
API's Keyword Planner service.

## How auth works here (as of Oct 2026)

Google sunset developer tokens on 2026-09-09. Access level (Test / Explorer /
Basic / Standard) is now tied to the **Google Cloud project** your OAuth
client belongs to, not a separate token. You already applied and got
**Explorer** access on your Cloud project — that's enough to query real
(non-test) Google Ads accounts, capped at 2,880 operations/day. Plenty for
keyword research.

So the only credentials needed are the OAuth client (already have it) plus a
refresh token (generate once, see below).

## One-time setup

1. **Create the venv and install deps** (already done if you're reading this
   after the initial setup):
   ```
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   ```

2. **Generate a refresh token.** This opens your browser, you log in with the
   Google account that has access to the Ads account you want to query, and
   approve access:
   ```
   venv/bin/python scripts/generate_refresh_token.py
   ```
   Copy the printed refresh token.

3. **Create your config file:**
   ```
   cp google-ads.yaml.example google-ads.yaml
   ```
   Open `google-ads.yaml` and fill in:
   - `client_id` / `client_secret` — from the `client_secret*.json` file in
     this folder (already here)
   - `refresh_token` — from step 2
   - `login_customer_id` — only needed if you're accessing the account through
     a Google Ads **manager** account; delete the line otherwise

   This file is gitignored — it will never be committed.

4. **Get a customer ID.** This is the specific Google Ads account (digits
   only, no dashes) you want to run keyword research against — e.g. your own
   business's account, or a client's. Find it top-right of the Ads UI when
   logged into that account. If you don't have one yet, you can create one
   free at ads.google.com — it doesn't need an active campaign for Keyword
   Planner to work, though number ranges are more precise on accounts with
   billing history.

## Running keyword research

```
venv/bin/python scripts/keyword_research.py \
  --customer-id 1234567890 \
  --keywords "emergency plumber" "blocked drain" \
  --location 2554 \
  --language 1000 \
  --out output/keywords.csv
```

- `--keywords` and/or `--url` — at least one required. `--url` pulls seed
  ideas from a landing page.
- `--location` — geo target constant ID. Default 2554 = New Zealand.
  Common ones: Australia 2036, United States 2840, United Kingdom 2826.
- `--language` — language constant ID. Default 1000 = English.
- `--out` — optional CSV path for the results.

Output includes: keyword, avg monthly searches, competition level, and
top-of-page bid range (low/high) — the core inputs for building ad groups and
setting initial bids in the next step.

## Project layout

```
google-ads.yaml.example   - template config (safe to commit)
google-ads.yaml           - your real credentials (gitignored)
requirements.txt
scripts/
  generate_refresh_token.py  - one-time OAuth login -> refresh token
  keyword_research.py        - step 1: Keyword Planner research
```

# Plan: run the whole campaign builder from the web app (phone / laptop / anywhere)

Status: DRAFT for review, 2026-10-14. Nothing built yet.

## Goal

Start and finish a campaign build entirely from a browser, including from a
phone while out, with the Mac mini (and this laptop) switched off. Every
existing approval point stays. The Claude Code chat is no longer needed.

## Why it can't just live on Netlify

Netlify is fine for the front end (it already hosts `web/`). It is not a place
to run the builds:

- Functions time out in seconds; "background functions" cap at 15 minutes.
  Keyword research, classification and site builds run longer and in many
  stages.
- No persistent disk and no Python venv for the existing scripts.
- No way to hold a job open while it waits days for your approval.

So the plan is: **front end stays on Netlify, a small always-on server runs the
jobs.**

## Architecture

```
Phone / laptop browser
        |  (login)
   Web app UI  (Netlify, existing web/ pages + new pages)
        |  HTTPS
   Backend API + job runner  (small cloud server, always on)
        |-- runs existing Python scripts (Keyword Planner, Ads upload, GTM)
        |-- calls Claude (Agent SDK) for judgment steps
        |-- reads/writes project state (database)
        |-- sends phone notifications when a step needs approval
        |
   External: Google Ads API, Keyword Planner, GTM, Airtable, Netlify, Trello, Delacon
```

### The backend, in plain terms

- **Projects and steps become database rows**, not loose files in `web/data/`.
  Each step has a status: `queued`, `running`, `needs_approval`, `approved`,
  `changes_requested`, `failed`.
- **A job runner** picks up queued steps and runs them. A step that reaches
  `needs_approval` simply stops and waits, for minutes or days, at no cost.
- **Approve** moves to the next step. **Request changes** re-queues the same
  step with your note attached (this replaces the "can you change X" chat).
- **Claude does the judgment work** (classify keywords, write ad copy, write
  landing page copy, sitelinks). PROCESS.md and the saved feedback rules are
  loaded as its instructions, so the rules you've already taught it carry over.
- **Hard gates** (never run without an explicit tap): upload to Google Ads,
  deploy a site, create Delacon number, anything that writes to a live account.
  Matches the existing "no unrequested live-account actions" rule.

### New screens

1. **Projects list**: every campaign, current step, what's waiting on you.
2. **New campaign**: business info, logo, photos, service areas (Step 0).
3. **Step review screens**: the existing ones, now saving to the backend.
4. **"Ask for changes" box** on every review screen.
5. **Live status** while a step runs, plus clear error messages if it fails.

### Notifications

Push to your phone when a step needs approval or fails. Simplest options:
ntfy (free) or Pushover (about $5 once). Email fallback.

### Login

Single user (you) to start: passwordless email link or a passkey. The app holds
live Ads credentials, so it must not be open to the internet without login.

## What has to change in the existing code

| Today | In the cloud |
|---|---|
| Credentials in `google-ads.yaml`, `gtm-credentials.yaml`, client secret JSON in the project folder | Server environment secrets, never committed |
| Approvals written to `web/approvals/*.json` by `local_server.py` | Backend API + database |
| Step data in `web/data/<project>/` and `output/` | Database + object storage for images/CSVs |
| Airtable, Netlify and Trello done via MCP tools in chat | Direct API calls from the backend (Airtable API, Netlify API, Trello API) |
| Step 5 "build a site" copies a template into `~/Desktop/Websites/...` | Template repos in GitHub; backend copies, edits, pushes; Netlify builds from git |
| Me reading PROCESS.md each session | PROCESS.md + feedback rules shipped with the backend as the Claude instructions |
| Per-client one-off scripts (`classify_step1_<client>.py` etc.) | Generalised per-trade/per-client logic driven by Claude, with the old scripts kept as reference |

The per-client scripts are the biggest piece of work: right now each new
client gets a hand-written classify/compile script. Unattended runs need that
generalised so Claude does it from rules + the prior same-trade project.

## Phases

### Phase 1 - Foundations (backend, login, notifications)
- Cloud server, database, secrets, login.
- Job runner and step state machine.
- Existing review screens switched from local files to the backend.
- Import the current projects (Rowdy, Bolt, Taupo, etc.) so history is there.
- Done when: you can open the app on your phone, log in, and see every project
  with correct status.

### Phase 2 - Start a campaign and run Steps 0-3
- New campaign form incl. logo/photo upload.
- Step 1 (keyword research + classification), Step 2 (location keywords),
  Step 3 (ad groups), each with approval and change requests.
- Reuse-prior-research-for-same-trade logic built in.
- Done when: a new campaign goes from phone to approved ad groups with no
  laptop involved.

### Phase 3 - Steps 4-6
- Ad copy (with the pinned-headline and Price Discovery rules).
- Landing pages: "I'll provide URLs" path first, then "build me a site".
- Sitelinks, callouts, snippets.

### Phase 4 - Live actions
- Step 7 lead capture (Airtable), Step 8 upload (Priority 1 by default, per
  the saved rule), Steps 9-11 (Delacon, Make.com, Trello).
- All behind explicit confirm buttons showing exactly what will be written.

### Phase 5 - Hardening
- Retry/resume on failure, audit log of every live write, spend/usage view,
  backup of project data.

Order is chosen so each phase is usable on its own: after Phase 2 you can
already start builds from your phone, and anything later can still be finished
the old way if needed.

## Costs (rough, NZD-ish, verify before committing)

- **Cloud server** (Fly.io / Railway / Render / small VPS): about $8-25/month.
- **Database**: free tier is enough at first (or Airtable, which you already
  pay for).
- **Netlify**: no change, current plan.
- **Notifications**: free (ntfy) or ~$5 once (Pushover).
- **Claude API usage**: this is the new cost. It is pay-per-use instead of
  coming out of your Claude subscription. A full campaign build is many
  steps with long keyword lists, so expect a few dollars per campaign, more for
  big ones. I'd measure it on the first real build and put a per-campaign cap
  in.
- **Google Ads / Keyword Planner / GTM APIs**: free.
- **Domain** (optional, for a clean URL): ~$25/year.

## Risks and open questions

1. **Quality unattended.** Classification has had a lot of corrections. Plan:
   replay 2-3 past projects through the new pipeline and compare to what you
   approved before trusting it.
2. **Site builds in the cloud** need the template repos in GitHub and a
   Netlify-from-git flow. Need to know where templates live today.
3. **Credentials in the cloud.** Needs a one-time move of the Ads/GTM tokens
   into server secrets; I can't do that for you, you'll paste them in.
4. **Images** (logo, work photos) via phone upload: fine, but need storage.
5. **Who else uses it?** Single user to start. Adding staff later means
   accounts and permissions.

## Decisions made (2026-10-14)

1. Hosting: Railway.
2. Claude API pay-as-you-go: accepted (set a monthly spend limit).
3. Templates: on the Mac mini now; moving to GitHub.
4. Single user (Liam).
5. First milestone: Steps 0-4 (keywords, ad groups, ad copy) approvable from
   phone. Landing pages / sitelinks (Steps 5-6) come after.

## Decisions that were needed (kept for reference)

1. Cloud server provider preference (or "you pick"; I'd suggest Fly.io or
   Railway).
2. OK with Claude API usage billing per campaign (with a cap)?
3. Where do the website templates live, and are they in GitHub yet?
4. Single user (you) for now, or will team members log in too?
5. Phase 2 target: is "phone -> approved ad groups" the right first milestone,
   or do you want Steps 4-5 sooner?

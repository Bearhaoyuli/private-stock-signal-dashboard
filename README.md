# Private Stock Research Signal Dashboard

Lean personal-use web app for tracking Reddit ticker mentions, extracting post context, validating historical forward returns, and showing probability-style research signals instead of buy or sell calls.

## Deployment shape

GitHub Pages can only host the frontend. This repo is structured accordingly:

- `frontend/`: static Next.js export deployed to GitHub Pages
- `backend/`: FastAPI app and Python jobs for ingestion, feature engineering, and signal building
- `supabase/`: SQL migration for schema, RLS, and helper views

GitHub Pages cannot host FastAPI or protect backend secrets. The practical setup is:

1. GitHub Pages hosts the private frontend shell.
2. Supabase handles auth and stores dashboard data.
3. Python jobs run locally or on a separate worker to ingest Reddit data and rebuild signals.
4. The frontend reads either:
   - Supabase views directly, or
   - the optional FastAPI API if `NEXT_PUBLIC_API_BASE_URL` is set.

## Product boundaries

- Private personal use only
- Labels use `Research Signal`, not buy or sell language
- No portfolio tracking
- No order execution
- No public signup UI
- No notifications or social features

## Folder structure

```text
.
├── .github/workflows/deploy-pages.yml
├── backend
│   ├── app
│   │   ├── core
│   │   ├── data
│   │   ├── models
│   │   └── services
│   ├── requirements.txt
│   └── scripts
├── frontend
│   ├── app
│   ├── components
│   ├── lib
│   └── package.json
└── supabase
    └── migrations
```

## Environment variables

Copy `.env.example` to `.env` at repo root.

Required for frontend deployment:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_ALLOWED_USER_EMAIL`

Optional frontend:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_BASE_PATH`

Backend and jobs:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ALLOWED_USER_EMAIL`
- `ENABLE_REDDIT_LIVE=false`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USERNAME`
- `REDDIT_PASSWORD`
- `REDDIT_USER_AGENT`
- `SUBREDDITS`
- `OPENAI_API_KEY`
- `ENABLE_TRANSLATION=true`
- `ENABLE_LLM_SUMMARY=false`

## Supabase setup

1. Create a Supabase project.
2. Run [`supabase/migrations/0001_init.sql`](/Users/haoyu/Documents/Codex/Trading/supabase/migrations/0001_init.sql) in the SQL editor or via the Supabase CLI.
3. In Auth settings:
   - disable public signup
   - create your user manually
   - use email/password auth
4. Set `NEXT_PUBLIC_ALLOWED_USER_EMAIL` in GitHub repository secrets.
5. Set the same email in backend `ALLOWED_USER_EMAIL`.

### RLS behavior

- All core market and Reddit tables are readable by authenticated users only.
- `profiles` is readable and writable only by the owner row.
- Do not expose the service role key to the frontend.

### Static GitHub Pages auth note

Because GitHub Pages is static, the allowed email check in the frontend is a build-time public value. That is acceptable for a personal app if:

- public signup is disabled
- only your user exists in Supabase Auth
- data tables remain protected behind authenticated Supabase sessions

If you want fully server-side email gating, move the frontend to Vercel or Netlify instead of GitHub Pages.

## Backend

### Install

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

### Run the API

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API endpoints

- `GET /api/dashboard`
- `GET /api/ticker/{ticker}`
- `POST /api/ingest/reddit`
- `POST /api/jobs/build-signals`

### Job scripts

Run scripts from repo root with `PYTHONPATH=backend`.

```bash
PYTHONPATH=backend python backend/scripts/seed_mock_data.py
PYTHONPATH=backend python backend/scripts/ingest_reddit.py
PYTHONPATH=backend python backend/scripts/build_daily_signals.py
```

Available scripts:

- [`backend/scripts/ingest_reddit.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/ingest_reddit.py)
- [`backend/scripts/reddit_client.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/reddit_client.py)
- [`backend/scripts/mock_reddit_client.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/mock_reddit_client.py)
- [`backend/scripts/extract_tickers.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/extract_tickers.py)
- [`backend/scripts/detect_translate_language.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/detect_translate_language.py)
- [`backend/scripts/update_stock_prices.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/update_stock_prices.py)
- [`backend/scripts/calculate_historical_returns.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/calculate_historical_returns.py)
- [`backend/scripts/build_daily_signals.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/build_daily_signals.py)
- [`backend/scripts/seed_mock_data.py`](/Users/haoyu/Documents/Codex/Trading/backend/scripts/seed_mock_data.py)

## Mock Reddit mode

Default:

```env
ENABLE_REDDIT_LIVE=false
```

Behavior:

- uses seeded English and Chinese Reddit posts
- includes AAPL, NVDA, TSLA, AMD, SOFI
- includes research, hype, bearish-risk, Chinese bullish, and Chinese bearish examples
- still produces a working dashboard without Reddit credentials

If `ENABLE_REDDIT_LIVE=true` but Reddit credentials are missing, the backend logs a warning and falls back to mock mode.

## Translation design

Translation entrypoint:

```python
translate_text(text, source_language, target_language="en")
```

Behavior:

- English text is analyzed directly
- Chinese text stores original fields and attempts English translation
- if `OPENAI_API_KEY` is missing, the pipeline falls back to a small built-in translation map for known mock samples, otherwise it skips translation gracefully
- NLP uses translated text when present

## Scoring model

`signal_score` is intentionally explainable and rule-based:

- 20% historical 5D win rate after similar posts
- 20% average 5D return after similar posts
- 15% mention spike versus 7-day average
- 15% sentiment score
- 10% real trading volume spike
- 10% catalyst score
- 5% engagement quality
- 5% cross-subreddit confirmation

`risk_score`:

- 20% hype language
- 20% price already ran up in the last 5 days
- 15% low liquidity
- 15% low market cap or penny-stock risk
- 10% weak catalyst
- 10% suspicious repeated language
- 10% concentrated discussion from few posts

High confidence is blocked unless the similar-post sample size is at least 30.

## Frontend

### Install

```bash
cd frontend
npm install
```

### Local run

```bash
npm run dev
```

Pages-safe design choices:

- static export via `next build`
- no server middleware
- client-side Supabase auth session check
- frontend can query Supabase views directly

Routes:

- `/login`
- `/dashboard`

## GitHub Pages deployment

1. Create a GitHub repository and push this repo to `main`.
2. In repository settings, enable GitHub Pages with `GitHub Actions` as the source.
3. Add repository secrets:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_ALLOWED_USER_EMAIL`
   - `NEXT_PUBLIC_API_BASE_URL` if using the optional FastAPI host
4. Push to `main`.
5. The workflow [`deploy-pages.yml`](/Users/haoyu/Documents/Codex/Trading/.github/workflows/deploy-pages.yml) builds `frontend/out` and publishes it.

## Recommended runtime flow

1. Run the Supabase migration.
2. Seed mock data with the backend script.
3. Confirm `daily_signals`, `dashboard_rows`, and `ticker_post_context` are populated.
4. Deploy the frontend to GitHub Pages.
5. Later, enable live Reddit mode by setting credentials and toggling `ENABLE_REDDIT_LIVE=true`.

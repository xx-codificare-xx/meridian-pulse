# Meridian Pulse

Meridian Pulse is an AI-powered healthcare intelligence dashboard built for a
Blue Shield of California UCI Capstone project. It combines healthcare news,
SEC filings, transcript analysis, and an AI research assistant in one web
application.

## Architecture

- **Frontend:** React and Vite, served locally with Nginx and deployed to
  GitHub Pages.
- **API:** FastAPI on Render for chatbot responses and in-memory transcript
  analysis.
- **Data:** Firebase Realtime Database for public article and SEC filing reads,
  with server-side writes from ingestion.
- **Ingestion:** GitHub Actions runs RSS and SEC EDGAR ingestion twice daily.
- **SEC source:** `data.sec.gov/submissions/CIK##########.json`, using
  zero-padded 10-digit CIKs and the configured SEC `User-Agent`.

## Local development

### Prerequisites

- Docker Desktop
- Python 3.11 or later for running Python commands locally
- Node.js 20 or later for frontend-only development

### Start the full local stack

From the project root:

```bash
docker compose up --build
```

The services are available at:

| Service | URL |
| --- | --- |
| Dashboard | http://localhost:4174/ |
| FastAPI | http://localhost:8000/ |
| API health | http://localhost:8000/health |
| FastAPI docs | http://localhost:8000/docs |
| Firebase emulator UI | http://localhost:4000/ |
| Firebase emulator database | http://localhost:9000/ |

The local dashboard uses the configured Firebase Realtime Database for
populated article and SEC reads. The emulator is available for local Firebase
experiments but is not automatically populated with production data.

### Run the frontend without Docker

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server normally runs on port 5173. The Docker/Nginx
preview on port 4174 is the authoritative local preview because it provides
the same-origin `/api` proxy used by the containerized dashboard.

### Run the backend without Docker

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Install Python dependencies first when needed:

```bash
pip install -r requirements.txt
```

## Environment configuration

Copy `.env.example` to `.env` for local configuration. Never commit `.env`,
Firebase service-account material, API keys, or other credentials.

Important variables include:

| Variable | Purpose |
| --- | --- |
| `FIREBASE_DATABASE_URL` | Firebase Realtime Database URL |
| `FIREBASE_SA_B64` | Base64-encoded Firebase service account for server writes |
| `LLM_API_MODE` | LLM mode, such as `aicredits` or direct OpenAI-compatible mode |
| `LLM_PROVIDER` | Provider selection |
| `LLM_API_KEY` | Runtime API key used by the backend |
| `AI_CREDITS_KEY` | Ingestion/API compatibility key |
| `LLM_BASE_URL` | OpenAI-compatible provider endpoint |
| `SEC_USER_AGENT` | Identifying SEC request header, including a contact email |
| `CORS_ORIGINS` | Allowed production frontend origins |
| `CHAT_SHARED_SECRET` | Optional shared secret for chatbot requests |
| `IP_HASH_SALT` | Salt used for privacy-preserving rate-limit keys |
| `DAILY_TOKEN_BUDGET` | Daily backend token budget |

## Dashboard behavior

### Urgency Dashboard

The dashboard displays healthcare articles from the active ingestion window.
Category filters use OR behavior:

- One selected category shows only articles associated with that category.
- Multiple selected categories show articles associated with any selected
  category.
- With no categories selected, only untagged articles appear under **Others**.
- Pagination is calculated from the complete filtered result set.

Article cards display their matched categories. CSV and Excel exports are
available from the dashboard.

### SEC Intelligence

SEC filings are fetched for the companies configured in `sources.yaml`:

- UnitedHealth
- Elevance
- CVS Health
- Humana
- Cigna

The submissions endpoint requires a 10-digit zero-padded CIK. SEC Archives
URLs use the unpadded CIK and the accession number without dashes in the path.
The SEC fetcher preserves the parallel array indexes returned by the API and
uses each filing's `primaryDocument` for its direct document URL.

The SEC tab shows the retained filings for all tracked companies with dynamic
pagination and CSV and Excel exports. The dashboard category filters do not
affect SEC filings.

### Transcripts

The Transcripts tab supports TXT, PDF, and DOCX uploads. Bundled transcripts
are loaded from `assets/data` and can be selected, analyzed, or downloaded.
Uploaded files are processed in memory and are not retained by the API.

### Behind Meridian Pulse

This tab contains project information, contact links, and the LinkedIn QR code
served from `frontend/public/linkedin.png`.

## Data ingestion

Run ingestion locally with:

```bash
python -m ingestion.news_processor
```

The ingestion pipeline:

1. Fetches configured RSS feeds and SEC submissions.
2. Normalizes URLs and canonicalizes titles.
3. Suppresses duplicate and syndicated records using URL and title hashes.
4. Scores candidate records against the configured intelligence categories.
5. Writes articles and filings to Firebase Realtime Database.
6. Maintains `/seen` and `/seen_title` suppression records.
7. Removes records outside the retention window.

RSS and SEC sources are configured in `sources.yaml`. Firebase rules are in
`database.rules.json`.

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health check |
| `POST /chat` | AI chatbot response |
| `POST /transcripts/analyze` | Analyze an uploaded transcript |
| `GET /transcripts/bundled` | List bundled transcript files |
| `GET /transcripts/bundled/{filename}` | Download a bundled transcript |

The API applies upload limits, PDF page limits, chatbot rate limits, daily
token budgeting, and security response headers.

## Tools and techniques

| Tool or technique | Use in Meridian Pulse |
| --- | --- |
| React | Component-based public dashboard UI |
| Vite | Frontend development and production bundling |
| FastAPI | Python API for chatbot and transcript analysis |
| Render | Hosts the always-available backend API |
| GitHub Pages | Hosts the public frontend website |
| Firebase Realtime Database | Public article/filing reads and protected server writes |
| GitHub Actions | Twice-daily news and SEC ingestion plus deployment workflows |
| Docker and Docker Compose | Reproducible local frontend, backend, and emulator stack |
| Nginx | Static frontend serving and local same-origin `/api` reverse proxy |
| SEC EDGAR API | Company submissions and filing document metadata |
| RSS | Publisher and topic-feed news collection |
| CIK normalization | Correct zero-padded SEC submissions requests and archive URLs |
| OpenAI-compatible API | Common client interface for AI Credits models |
| `gpt-4o-mini` | Cost-conscious AI model for chatbot, prefiltering, and tagging |
| Retrieval-augmented generation (RAG) | Chat prompt context is assembled from current Firebase article records and bounded conversation history |
| LLM classification | Assigns the seven dashboard categories and reasoning to each article |
| URL/title canonicalization | Suppresses duplicate and syndicated stories |
| Rate limiting and token budgets | Controls chatbot usage and provider spend |
| In-memory processing | Analyzes transcript uploads without retaining uploaded files |
| CSV and Excel export | Downloads dashboard and SEC results for analysis |

## Reliability and daily operation

The production system is intentionally split into independent services. GitHub
Pages can continue serving the dashboard even when the Render API is waking or
temporarily unavailable; Firebase continues serving public data; and GitHub
Actions refreshes news, AI tags, and SEC filings on its schedule.

The ingestion workflow runs at `10:00 UTC` and `22:00 UTC`. Each run fetches
new RSS and SEC records, applies duplicate suppression, sends new articles
through AI prefiltering and category scoring, and writes successful results to
Firebase. Records whose AI scoring fails remain eligible for retry on a later
run rather than being permanently marked as processed.

For a production smoke test, check `/health`, open the GitHub Pages site, verify
that today's article freshness timestamp changes after ingestion, and send a
test chatbot request. If AI calls fail, inspect the provider key, model
availability, and the GitHub Actions or Render deployment logs before changing
application code.

## Deployment

### GitHub Pages

The workflow in `.github/workflows/deploy-pages.yml` builds the frontend and
deploys it to GitHub Pages under `/meridian-pulse/`. Configure this repository
variable:

```text
VITE_API_BASE_URL=https://<your-render-service>.onrender.com
```

The workflow also sets the Firebase database URL and the production Vite base
path.

Render hosts the FastAPI backend only. Its public URL is not the dashboard
website; `/health` and `/docs` are the relevant API pages. The Pages workflow
uses the `VITE_API_BASE_URL` repository variable when present and falls back to
`https://meridian-pulse.onrender.com`.

### Render

`render.yaml` defines the FastAPI service. Configure the following values in
Render, keeping credentials as secret environment variables:

```text
LLM_API_MODE
LLM_PROVIDER
LLM_MODEL_PREFILTER
LLM_MODEL_SCORER
LLM_API_KEY
LLM_BASE_URL
FIREBASE_SA_B64
FIREBASE_DATABASE_URL
CORS_ORIGINS
CHAT_SHARED_SECRET
IP_HASH_SALT
DAILY_TOKEN_BUDGET
```

The Render service starts with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Its health check is `/health`.

### GitHub Actions ingestion

The workflow in `.github/workflows/ingest.yml` runs twice daily and supports
manual dispatch. Configure these repository secrets:

```text
FIREBASE_SA_B64
AI_CREDITS_KEY
SEC_USER_AGENT
```

## Project structure

```text
backend/       FastAPI app, Firebase adapter, LLM and transcript services
engine/        Prompts, scoring, and legacy LLM integration
frontend/      React/Vite application and Nginx configuration
ingestion/     RSS, SEC, deduplication, scoring, and Firebase writes
assets/data/   Bundled transcript files
main/          Original Streamlit application and tab references
plan/          Architecture and governance documentation
```

## Safety and governance

AI-generated summaries and analysis are informational and should be checked
against the original source. The application does not provide investment,
medical, or legal advice. Governance details are published in
`frontend/public/GOVERNANCE.md` and linked from the dashboard footer.

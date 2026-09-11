# Meridian Pulse — Migration Plan (Zero-Cost Revision)

**Revision date:** 10 September 2026
**Supersedes:** the Cloudflare Pages + Cloud Run + Supabase plan

---

## 1. Problem statement

Meridian Pulse is a Streamlit monolith. Streamlit handles UI, server execution, state, and reruns in a single process. This limits the application in five specific ways:

1. **The floating chatbot does not render.** `chatbot_component/index.html` runs inside a sandboxed Streamlit iframe, so `position: fixed` is clipped to the iframe rather than the viewport. There is no reliable workaround inside Streamlit.
2. **No persistence.** Articles, filings, scores, and chat history live in `st.session_state` and vanish on restart.
3. **LLM calls run during page rendering.** Fetch-and-score blocks the UI and re-runs on every interaction.
4. **Credentials are in `config.py`.** These must be revoked, not just moved.
5. **No shared state between users.** Every visitor re-fetches and re-scores from scratch, at full LLM cost.

## 2. Constraints

- **No billing account anywhere.** No credit card on file with any platform.
- **Publicly accessible** to any user, no login.
- **Final home:** `https://<username>.github.io/meridian-pulse`.

These rule out Google Cloud Run (requires a linked billing account), Firebase Cloud Functions and Firebase Cloud Storage (Blaze only since 3 Feb 2026), and any paid object storage.

---

## 3. Target architecture

```
Browser
  |
  |-- static bundle ------------> GitHub Pages          (free, no card)
  |
  |-- direct reads -------------> Firebase Firestore    (Spark, no card, no pause)
  |     articles (last 48h), sec_filings,
  |     transcripts, meta/last_run
  |
  '-- POST /chat ---------------> Render web service    (free tier, no card)
      POST /transcripts/analyze     FastAPI + LLM
                                       |
                                       v
                                 LLM provider (only billable component)

GitHub Actions (cron, 10:00 + 22:00 UTC)
  |-- RSS + SEC fetch
  |-- normalize + dedupe vs seen / seen_title
  |-- prefilter + all-tag scoring   (new items only)
  |-- SEC filing summarization
  |-- write meta/last_run
  '-- retention sweep
        |
        v
   Firestore (Admin SDK)
```

**Why the read path bypasses the backend.** Render's free tier sleeps after 15 minutes idle and takes 30–50 seconds to wake. If the dashboard read through FastAPI, every cold visit would appear broken. Reading Firestore directly from the browser means the dashboard loads instantly regardless of Render's state; the cold start affects only the first chatbot message, where a "connecting" indicator is acceptable.

---

## 4. Cost control

The LLM API key is the only component that can generate a bill. Everything else hard-stops at its quota. Treat this as a Phase 0 requirement, not a Phase 7 nicety.

| Control | Where | Value |
|---|---|---|
| Hard monthly spend cap | LLM provider console | set before first public deploy |
| Rate limit on `/chat` | `slowapi`, keyed on `sha256(ip + IP_HASH_SALT)` | 10/min, 100/day |
| Daily token budget | Firestore `usage/{YYYY-MM-DD}` | 429 when exceeded |
| `max_tokens` on every call | `llm_handler.ask_llm()` | explicit, no default |
| History cap | `/chat` request validation | 6 messages, server-enforced |
| Article context cap | `/chat` request validation | 20 articles, server-enforced |
| Prefilter fails **closed** | `tag_scorer.batch_prefilter()` | see §5.2 |

No Redis. In-process rate limiting is adequate on a single free instance.

---

## 5. Design changes to existing logic

These are behavioural changes to current code, not ports. They must be resolved before the phases below make sense.

### 5.1 Scoring is decoupled from tag selection

**Current:** `score_all_articles()` applies the three tags the user selected in `render_tag_selector()`, computes a weighted urgency score, and filters below threshold. `tab2.py` does the same for filings using `selected_tags` from session state.

**Problem:** scheduled ingestion has no user, so there is no tag selection.

**Change:** `score_single()` asks the LLM to evaluate **all seven tags** in one call and stores the raw boolean map. It no longer computes a score, label, or threshold filter.

```python
# stored per article
"tags_evaluated": {
    "time_sensitivity": true,
    "strategic_alignment": false,
    "regulatory_risk": true,
    "competitive_momentum": false,
    "financial_impact": true,
    "member_impact": false,
    "women_in_healthcare": false
},
"reasoning": "..."
```

Weighted score, urgency label, and threshold filtering move to the **frontend**, computed from `TAG_WEIGHTS` and `URGENCY_THRESHOLDS` shipped in the bundle.

**Benefits:** changing tag selection becomes instant with zero LLM calls (today it re-scores everything). Each article costs exactly one scoring call for its lifetime, regardless of how many tag combinations are ever viewed.

### 5.2 Prefilter fails closed

**Current:** if `batch_prefilter()` fails, all articles are treated as relevant and passed to `score_single()` — one LLM call each. A provider outage becomes the largest bill of the month.

**Change:** on prefilter failure, score at most `PREFILTER_FALLBACK_LIMIT` (default 20) articles and write the remainder to Firestore with `scored: false` for the next run to pick up.

### 5.3 SEC filing text extraction is bounded and precomputed

**Current:** `tab2.py` downloads filing HTML on demand, strips it with BeautifulSoup, truncates to ~6,000 chars, and summarizes during the user's request. A 10-K is tens of megabytes; parsing that in a 512 MB container will OOM.

**Change:**
- Stream the download with a 5 MB hard cap; abandon and mark `summary_unavailable` beyond that.
- Parse with `lxml`, not `html.parser`.
- Move the whole flow into the daily ingestion job. Filing summaries are stored, not generated live.

### 5.4 Transcript uploads are never written to disk

**Current:** `transcript_handler.py` reads from the local filesystem.

**Problem:** Render's disk is ephemeral and Firebase Cloud Storage requires Blaze. There is no free object store.

**Change:** uploads are processed entirely in memory inside the request. Only the analysis JSON is persisted to Firestore. Bundled transcripts in `assets/data` ship inside the container image and remain readable via `get_transcript_files()`.

### 5.5 Exports move to the browser

**Current:** `openpyxl`, `fpdf`, and `python-pptx` generate files server-side, written to configured export paths or held in memory.

**Change:** SheetJS, jsPDF, and PptxGenJS generate exports client-side from data already loaded. Removes three heavy dependencies from the container, removes the ephemeral-disk write path, and makes exports instant.

### 5.6 Freshness window and iterative ingestion

**Requirement:** the dashboard shows only today's and yesterday's articles, served from cache, with no live fetching.

**Display:** a single Firestore query — `published_at >= now - 48h`, ordered descending, `limit(50)`, cursor paginated. No LLM calls, no network fetches, no scoring on the read path. Expected load time 200–400 ms.

**Ingestion (twice daily, `0 10,22 * * *` UTC):**

```
fetch feeds (~200 items)
  → normalize + hash each URL
  → batch-check seen/{url_hash} and seen_title/{title_hash}
  → discard known and suppressed
  → prefilter only what is new        (~20–40 items in steady state)
  → score only what survives
  → upsert articles/ + seen/ + seen_title/
  → write meta/last_run
```

Two runs per day rather than one, so "today" is meaningful by mid-afternoon. Well inside Actions and Firestore quotas.

**Retention must not equal the display window.** If articles are deleted at 48 h, anything that resurfaces in a feed is re-ingested and re-scored at full LLM cost. Split them:

| Collection | Retained | Why |
|---|---|---|
| `articles/{url_hash}` | 14 days | display window plus headroom |
| `seen/{url_hash}` | 90 days, indefinitely if suppressed | prevents re-scoring and re-ingestion |
| `seen_title/{title_hash}` | 90 days | catches syndication |

`seen` documents are a few bytes each; 90 days of them is negligible against the 1 GiB ceiling.

**Date parsing is load-bearing.** The 48-hour window is only as good as `published_at`. Feeds report dates inconsistently and some omit them. Parse to UTC, fall back to `ingested_at` when absent or unparseable, and store both fields. A bad timezone assumption silently empties the dashboard.

### 5.7 Title-level near-duplicate detection

**Current:** deduplication is by URL only.

**Problem:** Google News searches for Medicare, health insurance, CMS policy, and ACA surface the same STAT and Fierce Healthcare stories already arriving from those direct feeds, under different URLs. Users see visible duplicate cards and you pay to score the same story twice.

**Change:** secondary key `sha256(title.lower(), punctuation stripped, stopwords trimmed)` stored in `seen_title/`. Check both keys before the prefilter.

### 5.8 Takedown suppression survives re-ingestion

Deleting an `articles` document is not a takedown — the next cron run re-fetches and re-scores it.

**Change:** `seen/{url_hash}` carries a `suppressed` boolean. Ingestion checks it before scoring and skips. The `articles` document is deleted; the `seen` tombstone is kept indefinitely. Suppressed entries are the one exception to the 90-day retention rule.

### 5.9 Excerpt cap at ingestion

Some publishers put full article text in RSS. Storing it is a copyright problem regardless of what the feed offers.

**Change:** `rss_fetcher.fetch_feed()` truncates `summary` to 300 characters after HTML cleaning. Store headline, capped excerpt, publication date, source name, and canonical URL. Never the body.

Redirect resolution in §5.10 uses a HEAD request for the canonical URL only. Do not fetch publisher page content.

### 5.10 Google News URL normalization

`rss_fetcher.py` pulls Google News searches for Medicare, health insurance, CMS policy, and ACA. Those URLs carry tracking parameters that change between runs. If the raw URL is hashed as the Firestore document ID, the same article re-inserts under a new ID daily.

**Change:** before hashing — resolve redirects, strip query strings and fragments, lowercase the host, drop trailing slashes.

---

## 6. Data model (Firestore)

Firestore has no unique constraints. Deduplication is structural: the dedupe key **is** the document ID, and writes use `.set(data, merge=True)` for idempotent upserts.

```
articles/{sha256(normalized_url)}
    url, source, title, published_at, summary,
    tags_evaluated {map}, reasoning, scored {bool},
    type: "rss" | "sec", ingested_at

sec_filings/{accession_number}
    cik, company_name, form_type, filed_at,
    viewer_url, doc_url, title,
    tags_evaluated {map}, reasoning,
    ai_summary, summary_unavailable {bool}

transcripts/{source_id}
    filename, uploaded_at, analysis {map}, source: "bundled" | "upload"

seen/{sha256(normalized_url)}
    first_seen, suppressed {bool}          # tombstone, survives article deletion

seen_title/{sha256(normalized_title)}
    first_seen

usage/{YYYY-MM-DD}
    tokens_used  (firestore.Increment)
    chat_requests, budget_hits

meta/last_run
    started_at, finished_at, feeds_ok, feeds_failed,
    items_fetched, items_new, items_scored, items_suppressed
```

**Not stored:** article bodies, filing HTML, transcript files, urgency scores, urgency labels, matched tags, chat history, IP addresses.

**Required composite indexes** (`firestore.indexes.json`) — these fail at query time until declared:
- `articles`: `published_at DESC` (the 48-hour window)
- `articles`: `type ASC, published_at DESC` (RSS/SEC split)
- `sec_filings`: `cik ASC, form_type ASC, filed_at DESC`

**Read budget.** Spark allows 50K document reads/day. Every returned document is a billable read, including `seen` lookups during ingestion. Budget:

| Consumer | Reads/day |
|---|---|
| Ingestion dedupe checks (2 runs × ~200 URL + ~200 title) | ~800 |
| Dashboard page loads | 50 per page view |
| Chat token-budget check | 1 per request |

That leaves roughly 49K/day for readers — about 980 page views. Pagination uses `limit(50)` with `start_after()` cursors; never fetch a collection to count it, use aggregation queries.

**Exposure to note:** direct Firestore reads from the browser cannot be rate limited the way `/chat` can. A scraper or a traffic spike can exhaust the daily read quota, at which point the dashboard stops serving until reset. This produces downtime, never a bill. If it happens in practice, the mitigation is moving reads behind a cached backend route.

**Security rules:**

```
match /{col}/{doc} {
  allow read: if col in ['articles','sec_filings','transcripts','meta'];
  allow write: if false;
}
```

`seen`, `seen_title`, and `usage` are deliberately absent — they are server-side only and must not be publicly readable.

The Admin SDK bypasses rules, so the Actions job still writes. The Firebase web config in the bundle is an identifier, not a credential — rules are what enforce access.

---

## 7. Module migration map

| Current | Destination | Change |
|---|---|---|
| `config.py` | `backend/settings.py` | pydantic-settings, same attribute names, no literals |
| `engine/prompts.py` | backend + Actions job | unchanged |
| `engine/llm_handler.py` | backend + Actions job | add explicit `max_tokens` |
| `engine/tag_scorer.py` | Actions job only | all-seven-tags rewrite (§5.1), fail closed (§5.2) |
| `ingestion/rss_fetcher.py` | Actions job only | URL normalization (§5.9, §5.10) |
| `ingestion/sec_fetcher.py` | Actions job only | User-Agent from env |
| `ingestion/news_processor.py` | Actions job only | writes to Firestore, returns nothing |
| `transcripts/transcript_handler.py` | `backend/services/` | in-memory only (§5.4) |
| `main/chatbot.py` | `backend/routes/chat.py` | strip session state and rerun |
| `main/chatbot_component/index.html` | `frontend/src/Chatbot.jsx` | `setComponentValue` → `fetch` |
| `style/load_styles.py` | `frontend/src/styles.css` | `data-theme` attribute |
| `main/components.py` | `frontend/src/components/` | rewrite as JSX |
| `main/tabs/tab1–4.py` | `frontend/src/pages/` | rewrite as JSX |
| export libraries | browser | SheetJS / jsPDF / PptxGenJS |

**Resulting backend surface:** `GET /health`, `POST /chat`, `POST /transcripts/analyze`. Nothing else.

**Session state mapping:**

| Key | Replacement |
|---|---|
| `dark_mode` | `localStorage` |
| `selected_tags` | URL query param (shareable views) |
| `page`, `sec_page` | React state holding Firestore cursors, not offsets |
| `articles`, `sec_filings` | Firestore queries |
| `transcript_*` | component state |
| `sidebar_chat`, `chat_open` | component state |

### 7a. Source registry

Feed definitions move out of `config.py` into `sources.yaml`, so adding a source is a reviewable diff rather than an edit buried in a config module.

```yaml
- name: STAT News
  url: https://www.statnews.com/feed/
  type: rss
  basis: public RSS feed
  max_items: 15
  active: true

- name: SEC EDGAR
  type: api
  basis: public API, declared User-Agent with contact, rate limited
  companies: [UnitedHealth, Elevance, CVS Health, Humana, Cigna]
  forms: [8-K, 10-K, 10-Q, DEF 14A]
  active: true
```

`GOVERNANCE.md` references this file rather than duplicating the list.

---

## 8. Phases

### Phase 0 — Security and cost (blocking)

- Revoke the AI provider keys currently in `config.py`. Revocation is the protection; everything else is cleanup.
- Set a hard monthly spend cap in the provider console.
- Scrub git history: `git filter-repo --path config.py --invert-paths`, or delete `.git` and re-init if history has no value.
- Enable GitHub push protection on the repo before the first push.
- Create `.env.example`; add `.env` to `.gitignore`.
- Move `SEC_USER_AGENT` contact email to an env var — do not commit a personal address to a public repo.
- Confirm no credentials remain in tracked files **or history**.
- Create `sources.yaml` (§7a) and the governance pack (`GOVERNANCE.md`). Both are documentation-only and can proceed in parallel with Phase 1.

### Phase 1 — Backend extraction

- Create `backend/`.
- Port `settings.py` from `config.py` using pydantic-settings.
- Port `llm_handler.py` with explicit `max_tokens`; preserve `openai_direct` / `aicredits` modes and `prefilter` / `scorer` roles.
- Port `prompts.py` unchanged. `CHATBOT_PROMPT` and the transcript Q&A section contract (`QUERY` / `RESPONSE` / `CONFIDENCE` / `SOURCE`) are preserved exactly.
- Extract the chatbot into a service taking `(query, history, article_context)` and returning text — no Streamlit references.
- Extract transcript analysis as in-memory only.
- Add pydantic request/response models and structured error handling.

### Phase 2 — FastAPI

- `GET /health`
- `POST /chat` — slowapi limits, Firestore token-budget check, server-enforced caps on history (6) and context (20)
- `POST /transcripts/analyze` — multipart upload, in-memory, returns analysis JSON
- CORS `allow_origins` from env: `https://<username>.github.io` and `http://localhost:5173`. Never `["*"]`.
- Rate limiting keyed on `sha256(ip + IP_HASH_SALT)`, 24-hour TTL. No raw IP is stored or logged anywhere.
- `CHAT_SHARED_SECRET` header check on `/chat` only. It ships in the public bundle, so it stops casual `curl` traffic and nothing more — the rate limit and token budget are the real controls.
- Upload caps on `/transcripts/analyze`: 10 MB, and a page limit on PDF extraction. Unbounded parsing will OOM a 512 MB container.
- No Supabase Auth, no user accounts — all displayed data is public.

### Phase 3 — Floating chatbot slice ⭐

The reason for the migration. Ship this before rebuilding anything else.

- Vite + React app. Set `base` from `VITE_BASE_PATH` — `/` while served from Render in this phase, `/meridian-pulse/` at Phase 7. Hardcoding the Pages path now breaks every asset URL on Render.
- Copy `dist/index.html` → `dist/404.html` in the build so refresh survives client-side routing on Pages.
- Port `chatbot_component/index.html` to `Chatbot.jsx`. Launcher, panel, message rendering, send, clear, close, dark mode, and context indicator already exist — replace `Streamlit.setComponentValue()` with `fetch` to `POST /chat`.
- Add a visible "connecting" state covering the 30–50s Render cold start.
- Mount the built bundle in FastAPI (`app.mount("/", StaticFiles(directory="dist", html=True))`) and deploy **one** Render service. No CORS, no two-service cold-start mismatch.
- Streamlit continues serving everything else during this phase.
- **Article context is empty in this phase.** Firestore does not exist yet and Streamlit's articles live in session state the React app cannot reach. `POST /chat` must accept `article_context: []` and degrade to general Q&A. The context indicator shows "no article context". Full context arrives in Phase 5.

**Exit criterion:** the floating chatbot renders correctly over the viewport on desktop and mobile at a public URL.

### Phase 4 — Firestore and scheduled ingestion

- Create the Firebase project (Spark). Deploy security rules and `firestore.indexes.json`.
- Rewrite `tag_scorer.py` per §5.1 and §5.2.
- Add URL normalization per §5.10, excerpt cap per §5.9.
- Rewrite `news_processor.fetch_all_news()` to upsert into Firestore instead of returning a list.
- Add bounded SEC filing download and summarization per §5.3.
- Add title-hash near-duplicate detection per §5.7 and suppression checking per §5.8.
- Implement UTC date normalization with `ingested_at` fallback per §5.6.
- Single GitHub Actions workflow, `0 10,22 * * *` UTC: fetch → normalize → dedupe against `seen` and `seen_title` → prefilter → all-tag scoring → filing summaries → upsert → write `meta/last_run` → delete `articles` older than 14 days and unsuppressed `seen` entries older than 90 days.
- Add `workflow_dispatch` for manual backfill and for resetting the 60-day inactivity clock (see §10).
- Verify the 48-hour window query returns results before building the dashboard against it.

### Phase 5 — Frontend rebuild

Port one tab at a time; Streamlit stays live as fallback until each is replaced.

- Dashboard: 48-hour Firestore query, client-side weighted scoring from `tags_evaluated`, tag selector (max 3), urgency filter, cursor pagination, article cards.
- **Client-side filtering interacts badly with server-side pagination.** A `limit(50)` page filtered down to "High urgency only" may render three cards. Either fetch pages of 50 and render variable counts, or keep fetching pages until the filtered count reaches a display target. Decide this explicitly rather than discovering it.
- Attribution on every card: source name, publication timestamp, link to original. Model-generated fields (`reasoning`, urgency score, `ai_summary`) carry a visible AI-assessment marker.
- Cache-age indicator from `meta/last_run` — "Updated 3 hours ago".
- Not-investment-advice line on SEC filing summaries.
- SEC Intelligence: Firestore query, company and form-type filters, stored `ai_summary`.
- Transcript Intelligence: bundled list plus upload → `POST /transcripts/analyze`; render pulse, signals, risks, horizon, metrics; TXT and DOCX download client-side.
- Behind Meridian Pulse: static page.
- Exports: SheetJS / jsPDF / PptxGenJS.
- Port `load_styles.py` to CSS custom properties under `[data-theme="dark"]`.
- Responsive layouts, accessible labels, keyboard support.

### Phase 6 — Local parity

- `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`.
- Firebase emulator suite in place of a local Postgres container.
- Full local run before any production change.

### Phase 7 — Split hosting

- GitHub Actions `deploy-pages` publishes `frontend/dist` to `<username>.github.io/meridian-pulse`.
- Point `VITE_API_BASE_URL` at the Render service; remove the `StaticFiles` mount; add the Pages origin to CORS.
- Render start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` — Render will not route to a hardcoded port.
- Do **not** host the frontend on Render too. The 750 free hours are per account; a second service halves the budget.
- Set `VITE_BASE_PATH=/meridian-pulse/` for the Pages build.
- CSP header limiting `connect-src` to the Render origin and Firestore.
- Enable Dependabot.
- Publish the takedown contact route and `GOVERNANCE.md` link in the footer.
- Sentry free tier plus Render logs. No custom domain — it costs money, and Pages provides HTTPS free.
- Decommission Streamlit.

---

## 9. Secrets matrix

| Variable | Render | GitHub Actions | Frontend bundle |
|---|:---:|:---:|:---:|
| `LLM_API_KEY` | ✅ | ✅ | ❌ |
| `LLM_API_MODE`, `LLM_BASE_URL` | ✅ | ✅ | ❌ |
| `FIREBASE_SA_B64` | ✅ | ✅ | ❌ |
| `SEC_USER_AGENT` | — | ✅ | ❌ |
| `CHAT_SHARED_SECRET` | ✅ | — | ✅ (not a real secret) |
| `CORS_ORIGINS` | ✅ | — | ❌ |
| `IP_HASH_SALT` | ✅ | — | ❌ |
| `VITE_BASE_PATH` | — | — | ✅ (build-time) |
| `VITE_API_BASE_URL` | — | — | ✅ |
| Firebase web config | — | — | ✅ (public by design) |

Firebase Admin is a service account JSON, not a connection string. Base64 it into one variable and decode at startup:

```python
cred = credentials.Certificate(
    json.loads(base64.b64decode(os.environ["FIREBASE_SA_B64"]))
)
```

Anything prefixed `VITE_` is baked into the public bundle at build time. Only the API base URL and Firebase web config belong there.

---

## 10. Free-tier limits and failure modes

| Platform | Limit | What happens at the limit |
|---|---|---|
| Firestore (Spark) | 1 GiB stored; 50K reads / 20K writes / 20K deletes per day; 10 GiB/mo egress | Product stops serving until daily reset. **No project pause.** |
| Firebase Auth | 50K MAU | Not used in this plan |
| Render free | 750 hrs/mo, 512 MB RAM | Sleeps after 15 min idle; wakes automatically in 30–50s |
| GitHub Pages | 100 GB/mo soft bandwidth | Soft limit, contact from GitHub |
| GitHub Actions | Unlimited on public repos | Scheduled workflows disabled after 60 days of repo inactivity — mitigate with a periodic commit or `workflow_dispatch`; set a calendar reminder |

**Watch:** 512 MB rules out locally-loaded embedding or transformer models. If semantic features are added later, call an embeddings API.

**Watch:** Spark does not pause the project, but a product that exhausts its daily quota stops responding until reset. The protection is the read discipline in §6, not the absence of a pause.

---

## 11. Verify before building

- Render free-tier terms (750 hrs, 512 MB, no card) — confirm current at signup.
- Firebase Spark quotas on the live pricing page.
- That Firebase Cloud Storage still requires Blaze, if object storage ever becomes necessary.

---

## 12. Governance

HIPAA is out of scope: the system ingests published news and public EDGAR filings, holds no PHI, and has no user accounts. Compliance would in any case require BAAs that no free tier offers. The applicable governance is publisher- and reader-facing, documented in `GOVERNANCE.md` across seven areas — data scope, source policy, accuracy and AI disclosure, deduplication keys, retention, security and privacy, and rights and takedowns.

The code-level requirements arising from it are §5.6 through §5.9, the hashed-IP rate limiting in Phase 2, the attribution and disclosure work in Phase 5, and the takedown route and CSP in Phase 7.

---

## 13. Build order

```
0 → 1 → 2 → 3 ⭐ → 4 → 5 → 6 → 7
```

Phase 3 is the deliverable that solves the stated problem. Everything after it is migration of features that currently work.

Phase 0 documentation (`GOVERNANCE.md`, `sources.yaml`) can run in parallel with Phases 1–3; only the credential revocation is genuinely blocking.

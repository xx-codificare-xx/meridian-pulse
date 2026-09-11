Problem statement

The current Meridian Pulse application is built as a Streamlit monolith. While Streamlit is useful for rapid prototyping, it limits the application’s ability to provide a production-quality website experience, especially for the floating chatbot, responsive navigation, independent frontend/backend scaling, persistent user state, and secure API handling.

The chatbot is currently coupled to Streamlit session state and UI rendering. Its backend logic—LLM requests, article context, conversation history, SEC/news ingestion, scoring, and transcript analysis—should be separated from the frontend before deployment.

The current  config.py  also contains exposed API credentials, which creates a serious security risk and must be addressed before publishing.

Quick plan

1. Stabilize and secure the existing application
• Preserve current chatbot functionality.
• Remove exposed credentials from source code.
• Move secrets to environment variables.
• Document existing features and data flows.
2. Separate backend services from the Streamlit UI
• Extract news, SEC, transcript, scoring, and chatbot functionality into Python service modules.
• Build a FastAPI backend.
• Add API endpoints for dashboard data, SEC filings, transcripts, scoring, and chatbot messages.
3. Build a modern frontend
• Use React or Next.js.
• Recreate the dashboard, SEC intelligence, transcripts, and information pages.
• Implement the chatbot as a real floating icon and popup panel.
• Add responsive layouts and reusable UI components.
4. Add persistent storage and background processing
• Use PostgreSQL through Supabase or another managed database.
• Store articles, filings, transcript metadata, scoring results, and chat sessions.
• Run ingestion and scoring as scheduled/background jobs instead of during page rendering.
5. Containerize and deploy
• Use Docker for local development and deployment consistency.
• Host the frontend on Cloudflare Pages.
• Host the FastAPI backend on Google Cloud Run.
• Use Supabase for database/authentication/storage.
• Add monitoring, logging, and rate limiting.

List of actions

Phase 1: Audit and security

• Inventory all existing Streamlit features.
• Identify imports and functions that contain business logic.
• Identify all external APIs and data sources.
• Revoke the exposed AI provider keys in  config.py .
• Create  .env.example .
• Load secrets through environment variables.
• Add  .env  to  .gitignore .
• Confirm no credentials remain in tracked files.
• Review SEC API User-Agent configuration.

Phase 2: Backend extraction

• Create a  backend/  directory.
• Move or refactor news ingestion into reusable services.
• Move SEC filing retrieval into reusable services.
• Move transcript loading and analysis into reusable services.
• Keep tag scoring independent from Streamlit.
• Create a chatbot service that accepts:
• user query
• conversation history
• article context
• Preserve the existing  CHATBOT_PROMPT .
• Preserve the existing LLM provider and role behavior.
• Add structured error handling.
• Add request and response data models.

Phase 3: FastAPI API

• Add  GET /health .
• Add  GET /articles .
• Add  POST /articles/fetch .
• Add  GET /sec-filings .
• Add  POST /sec-filings/fetch .
• Add  GET /transcripts .
• Add  POST /chat .
• Add request validation.
• Add CORS configuration for the frontend.
• Add backend rate limiting for chatbot requests.
• Add API authentication if the application will contain private data.

Phase 4: Database and jobs

• Create database tables for articles and SEC filings.
• Create transcript metadata tables.
• Create scoring result tables.
• Create chat session/message tables if persistence is needed.
• Add deduplication using article URLs, accession numbers, and transcript identifiers.
• Add scheduled news ingestion.
• Add scheduled SEC ingestion.
• Move expensive LLM scoring into background jobs.
• Cache results to avoid repeated API and LLM calls.

Phase 5: Frontend

• Create a React or Next.js frontend.
• Rebuild the Meridian Pulse dashboard.
• Rebuild tag selection and urgency filtering.
• Rebuild pagination.
• Rebuild SEC filing intelligence.
• Rebuild transcript analysis.
• Rebuild export functionality.
• Create a floating chatbot launcher.
• Create a responsive chatbot panel.
• Preserve:
• conversation history
• clear chat
• article context
• loading states
• backend error messages
• dark mode
• Add responsive behavior for desktop, tablet, and mobile.
• Add accessible labels and keyboard support.

Phase 6: Local architecture

• Add a frontend Dockerfile.
• Add a backend Dockerfile.
• Add  docker-compose.yml .
• Run frontend, backend, and PostgreSQL locally.
• Add API environment configuration.
• Test the complete application locally before deployment.
• Keep Streamlit available temporarily as a fallback during migration.

Phase 7: Deployment

• Deploy the frontend to Cloudflare Pages.
• Deploy the FastAPI backend to Google Cloud Run.
• Configure backend environment variables.
• Configure frontend API URL.
• Configure Supabase database and authentication if required.
• Configure scheduled Cloud Run jobs or GitHub Actions.
• Configure custom domain and HTTPS.
• Configure CORS for production domains.
• Add logging and error monitoring.
• Test deployment with production-like data.

Recommended target architecture

React/Next.js frontend
        |
        | HTTPS API requests
        v
FastAPI backend on Cloud Run
        |
        +-- News and RSS services
        +-- SEC filing service
        +-- Transcript service
        +-- Scoring service
        +-- Chatbot/LLM service
        |
        v
PostgreSQL/Supabase

Scheduled jobs
        |
        +-- News ingestion
        +-- SEC ingestion
        +-- Article scoring

The safest migration approach is incremental: first secure and extract the existing logic, then expose it through FastAPI, and finally replace the Streamlit interface with the new frontend.
give me the structure of the current system - what does what and architecture
Thought for 2s

I’ll map the current runtime flow and module responsibilities from the existing code, including the Streamlit entrypoint, tabs, ingestion, scoring, LLM, and storage behavior.

Search "**/*.py" 24 files found

Read app.py L1:100 (58 lines read)
Read news_processor.py L1:220 (54 lines read)
Read tab3.py L1:220 (210 lines read)

Thought for 2s

Read rss_fetcher.py L1:220 (139 lines read)
Read transcript_handler.py L1:220 (56 lines read)
Read prompts.py L1:220 (143 lines read)
Read tab4.py L1:160 (52 lines read)

Thought for 43s

Current Meridian Pulse System Structure

1. High-level architecture

The current system is a single-process Streamlit application.

User browser
    |
    v
Streamlit: main/app.py
    |
    +-- Dashboard tab
    |     |
    |     +-- RSS news ingestion
    |     +-- SEC filing ingestion
    |     +-- Deduplication
    |     +-- LLM relevance filtering
    |     +-- LLM tag scoring
    |     +-- Urgency ranking
    |
    +-- SEC Intelligence tab
    |     |
    |     +-- SEC filing retrieval
    |     +-- Filing filtering
    |     +-- Filing document download
    |     +-- LLM summary
    |
    +-- Transcript Intelligence tab
    |     |
    |     +-- Local transcript files
    |     +-- User upload
    |     +-- PDF/DOCX/TXT extraction
    |     +-- LLM war-room analysis
    |     +-- LLM transcript Q&A
    |
    +-- Behind Meridian Pulse tab
    |
    +-- Chatbot
          |
          +-- Article context
          +-- Conversation history
          +-- LLM response

There is currently no separate frontend, backend API, database, queue, or persistent application service. Streamlit handles the UI, server execution, state management, and request reruns.

────────────────────

2. Application entrypoint

 main/app.py 

This is the main application controller.

Responsibilities:

• Configures Streamlit page settings.
• Initializes dark mode.
• Renders the Night mode toggle.
• Loads CSS styles.
• Renders the hero section.
• Creates the four main tabs.
• Calls the corresponding tab functions.
• Calls the chatbot renderer.

Current execution flow:

main()
  ├── initialize dark_mode
  ├── render Night toggle
  ├── load_styles()
  ├── render_hero()
  ├── create tabs
  ├── tab_dashboard()
  ├── tab_sec()
  ├── tab_transcripts()
  ├── tab_hire()
  └── render_sidebar_chat()

The application is imperative and rerun-based. When a user clicks a button, Streamlit reruns the entire script and reconstructs the page.

────────────────────

3. Presentation layer

 main/components.py 

Contains reusable UI components.

 render_hero() 

• Loads  assets/logo.png .
• Converts the image to Base64.
• Renders the Meridian Pulse logo, title, and tagline.

 render_card(article, idx) 

Renders an article or SEC filing card containing:

• Urgency badge.
• Title.
• Source.
• Publication date.
• Urgency score bar.
• Reasoning.
• Matched tags.
• Expandable summary.
• Source link.

 render_pagination(total, page_key) 

Controls pagination using Streamlit session state.

State is stored in keys such as:

st.session_state["page"]
st.session_state["sec_page"]

The pagination state is not stored in a database.

 style/load_styles.py 

Contains the application’s CSS styling:

• Light mode colors.
• Dark mode colors.
• Hero styling.
• Tab styling.
• Cards.
• Badges.
• Buttons.
• Chat-related visual styles.
• Responsive visual rules.

────────────────────

4. Dashboard tab

 main/tabs/tab1.py 

This is the main intelligence dashboard.

Tag selection

 render_tag_selector() :

• Displays all configured intelligence tags.
• Defaults to the first three tags.
• Allows a maximum of three selected tags.
• Returns the selected tags.

Configured tags are defined in  config.py :

Time Sensitivity
Strategic Alignment
Regulatory Risk
Competitive Momentum
Financial Impact
Member Impact
Women in Healthcare

Fetch and score flow

When the user clicks Fetch and Score News:

tab1.py
  |
  v
news_processor.fetch_all_news()
  |
  +-- fetch_all_rss()
  +-- fetch_all_sec()
  +-- merge results
  +-- deduplicate by URL
  +-- pre-filter with LLM
  +-- score articles with LLM
  +-- sort by urgency
  |
  v
st.session_state["articles"]

The dashboard then displays:

• Total articles.
• High-priority count.
• Medium-priority count.
• Low-priority count.
• Urgency filter.
• Paginated article cards.
• Export options.

Exports

The dashboard can generate:

• Excel via  openpyxl .
• PDF via  fpdf .
• PowerPoint via  python-pptx .

These exports are generated during the Streamlit request and are either:

• Held in memory for download, or
• Written under the configured export paths.

────────────────────

5. News ingestion pipeline

 ingestion/news_processor.py 

This is the master news pipeline.

Pipeline steps

RSS feeds
    +
SEC filings
    |
    v
Combined articles
    |
    v
Deduplicate by URL
    |
    v
Batch relevance filtering
    |
    v
Tag scoring
    |
    v
Urgency threshold filtering
    |
    v
Sorted articles

 fetch_all_news() 

This function:

1. Fetches RSS articles.
2. Fetches SEC filings.
3. Merges both sources.
4. Removes duplicate URLs.
5. Runs  score_all_articles() .
6. Returns the final ranked list.

The result is a list of dictionaries, for example:

{
    "title": "...",
    "summary": "...",
    "url": "...",
    "source": "...",
    "published": "...",
    "type": "rss",
    "tags_matched": [...],
    "urgency_score": 0.75,
    "urgency_label": "🔴 High",
    "reasoning": "..."
}

────────────────────

6. RSS ingestion

 ingestion/rss_fetcher.py 

Responsible for external RSS news sources.

Configured feeds include:

• STAT News.
• Fierce Healthcare.
• KFF Health News.
• Kaiser Health.
• NPR Health.
• CDC Newsroom.
• Google News Medicare searches.
• Google News health insurance searches.
• Google News CMS policy searches.
• Google News ACA searches.

Main functions

 fetch_feed(name, url) 

• Downloads and parses one RSS feed.
• Limits results per feed.
• Cleans HTML from titles and summaries.
• Normalizes dates.
• Converts entries into article dictionaries.

 fetch_all_rss() 

• Iterates through configured feeds.
• Fetches each feed sequentially.
• Deduplicates articles by URL.
• Returns a combined list.

RSS results are fetched live when the user clicks the dashboard fetch button. They are not automatically scheduled or cached persistently.

────────────────────

7. SEC ingestion

 ingestion/sec_fetcher.py 

Responsible for SEC EDGAR filings.

Configured companies:

• UnitedHealth.
• Elevance.
• CVS Health.
• Humana.
• Cigna.

Relevant forms:

8-K
10-K
10-Q
DEF 14A

Main functions

 get_company_filings(company_name, cik) 

• Calls the SEC submissions endpoint.
• Extracts recent filing metadata.
• Builds:
• Filing title.
• Filing type.
• Filing date.
• Viewer URL.
• Document URL.
• Company name.
• Accession number.
• Returns filing dictionaries.

 fetch_all_sec() 

• Fetches companies concurrently using a thread pool.
• Combines filing results.
• Returns all filings.

The SEC tab later uses the  doc_url  to download the filing HTML for summarization.

────────────────────

8. Tag scoring and urgency classification

 engine/tag_scorer.py 

This is the AI scoring engine.

Step 1: Batch pre-filter

 batch_prefilter()  sends groups of articles to the LLM and asks whether each article is relevant to healthcare insurance intelligence.

The LLM returns responses such as:

1:YES 2:NO 3:YES

Articles marked irrelevant are removed.

If the pre-filter fails, the implementation currently defaults to treating all articles as relevant.

Step 2: Parallel tag scoring

 score_all_articles() :

• Uses a thread pool.
• Scores relevant articles in parallel.
• Calls  score_single()  for each article.
• Applies the selected tags.
• Calculates a weighted urgency score.
• Assigns an urgency label.
• Filters out articles below the minimum threshold.
• Sorts results by score.

 score_single() 

For each article:

1. Sends the article title and summary to the LLM.
2. Parses the JSON response.
3. Checks which selected tags are true.
4. Adds the corresponding tag weights.
5. Caps the score at  1.0 .
6. Assigns a label.

Labels are based on thresholds:

0.50 or higher  -> High
0.20 or higher  -> Medium
0.05 or higher  -> Low
below 0.05      -> Minimal

The scoring result is stored directly in the article dictionary.

────────────────────

9. LLM layer

 engine/llm_handler.py 

This module provides the common LLM interface.

 get_llm(role) 

Creates a LangChain OpenAI-compatible chat client.

Supported modes:

openai_direct
aicredits

Supported roles include:

prefilter
scorer

The actual model is selected from  config.py .

 ask_llm(prompt, llm) 

• Sends a prompt to the LLM.
• Returns the response as plain text.

 is_healthcare_relevant() 

A single-article relevance helper exists, although the primary news pipeline uses the batch pre-filter in  tag_scorer.py .

────────────────────

10. Prompt layer

 engine/prompts.py 

Centralizes the main prompt templates.

Prompts exist for:

• Transcript war-room analysis.
• Transcript Q&A.
• Article tag scoring.
• Article relevance filtering.
• General chatbot responses.

This is an important reusable part of the system because the application’s behavior and output formats depend heavily on these prompts.

The transcript analysis prompt expects strict JSON.

The transcript Q&A prompt expects sections:

QUERY
RESPONSE
CONFIDENCE
SOURCE

The chatbot prompt receives:

• Current article context.
• Conversation history.
• User query.

────────────────────

11. SEC Intelligence tab

 main/tabs/tab2.py 

Responsibilities:

• Displays the SEC intelligence page.
• Fetches SEC filings on demand.
• Scores the filings using selected tags from session state.
• Stores results in:

st.session_state["sec_filings"]

• Filters by:
• Company.
• Filing type.
• Displays paginated filing cards.
• Downloads filing HTML.
• Removes scripts and styles using BeautifulSoup.
• Extracts visible text.
• Truncates content to approximately 6,000 characters.
• Sends filing content to the LLM.
• Displays an AI summary.

The SEC summary flow is:

SEC filing metadata
    |
    v
doc_url
    |
    v
download HTML
    |
    v
BeautifulSoup text extraction
    |
    v
LLM prompt
    |
    v
AI filing summary

────────────────────

12. Transcript Intelligence tab

 main/tabs/tab3.py 

This module supports local transcript analysis.

Transcript sources

Transcripts come from:

• Existing files in  assets/data .
• User uploads through Streamlit.

Supported formats:

.txt
.pdf
.docx

Transcript flow

Select or upload transcript
    |
    v
transcript_handler.read_transcript()
    |
    v
Display raw transcript preview
    |
    v
Run War Room Briefing
    |
    v
LLM JSON analysis
    |
    v
Display pulse, signals, risks, horizon, and metrics

Transcript Q&A

The user can ask questions about the currently loaded transcript.

The application:

• Stores the question in Streamlit session state.
• Sends the transcript and question to the LLM.
• Stores the response in session state.
• Parses and displays the expected sections.
• Allows downloading:
• TXT.
• Word document.

────────────────────

13. Transcript file handling

 transcripts/transcript_handler.py 

Provides file extraction utilities.

Supported readers

•  read_txt() 
•  read_pdf() 
•  read_docx() 
•  read_transcript() 
•  get_transcript_files() 

It reads files directly from the local filesystem.

There is no document database or object-storage layer currently.

────────────────────

14. Chatbot

 main/chatbot.py 

The chatbot currently combines three responsibilities:

1. UI rendering.
2. Session-state management.
3. LLM orchestration.

Context construction

The chatbot retrieves up to 20 scored articles from:

st.session_state["articles"]

It creates context using:

• Urgency label.
• Article title.
• Source.
• Publication date.
• Scoring reasoning.

Conversation state

The current conversation is stored in:

st.session_state["sidebar_chat"]

The session state contains messages such as:

{
    "role": "user",
    "content": "..."
}

and:

{
    "role": "assistant",
    "content": "..."
}

Only the latest six messages are sent to the LLM as prompt history.

Chatbot response flow

User query
    |
    v
Append user message to session state
    |
    v
Build article context
    |
    v
Build conversation history
    |
    v
Load CHATBOT_PROMPT
    |
    v
Call get_llm(role="scorer")
    |
    v
Call ask_llm()
    |
    v
Append assistant response
    |
    v
Rerun Streamlit

The chatbot UI was being migrated from the sidebar to a custom Streamlit component. The backend behavior still depends on Streamlit session state and reruns.

────────────────────

15. Custom chatbot component

 main/chatbot_component/index.html 

This is the frontend portion of the newer chatbot implementation.

It is intended to provide:

• Floating chat launcher.
• Popup chat panel.
• Message rendering.
• Send button.
• Clear chat button.
• Close button.
• Dark mode colors.
• Article-context indicator.

Communication works through:

Browser component
    |
    v
Streamlit.setComponentValue(...)
    |
    v
main/chatbot.py
    |
    v
Streamlit rerun

The component itself does not call the LLM. It sends events back to Python, and Python performs the LLM request.

────────────────────

16. Session state

The application uses Streamlit’s in-memory session state for temporary application state.

Important keys include:

dark_mode
articles
selected_tags
page
sec_filings
sec_page
transcript_analysis
transcript_query
transcript_submitted
transcript_response
sidebar_chat
chat_open

This means:

• State belongs to the active browser session.
• State is lost when the session is cleared or the server restarts.
• State is not shared reliably between users.
• There is no durable chat history.
• There is no persistent article cache.
• There is no job status storage.

────────────────────

17. Configuration

 config.py 

Central configuration includes:

• LLM provider.
• Model names.
• API mode.
• API credentials.
• AI Credits base URL.
• Tag weights.
• Urgency thresholds.
• SEC company CIKs.
• SEC request headers.
• RSS feed URLs.
• Article limits.
• Export paths.
• Transcript paths.
• Application title and tagline.

The current configuration is globally imported by most modules.

A major architectural/security issue is that API credentials are currently stored directly in  config.py . They should be moved to environment variables before deployment.

────────────────────

18. Storage model

The current system has no database.

Current storage

┌────────────────────┬─────────────────────────────────────┐
│ Data               │ Current location                    │
├────────────────────┼─────────────────────────────────────┤
│ RSS articles       │ In-memory Python lists              │
├────────────────────┼─────────────────────────────────────┤
│ SEC filings        │ In-memory Python lists              │
├────────────────────┼─────────────────────────────────────┤
│ Scored articles    │ Streamlit session state             │
├────────────────────┼─────────────────────────────────────┤
│ Chat history       │ Streamlit session state             │
├────────────────────┼─────────────────────────────────────┤
│ Transcript files   │ Local filesystem                    │
├────────────────────┼─────────────────────────────────────┤
│ Exported files     │ Local filesystem or download buffer │
├────────────────────┼─────────────────────────────────────┤
│ Configuration      │ config.py                           │
├────────────────────┼─────────────────────────────────────┤
│ Logo and QR assets │ Local assets/ directory             │
└────────────────────┴─────────────────────────────────────┘

This is appropriate for a prototype but not for a multi-user production application.

────────────────────

19. Current architecture characteristics

Strengths

• Fast to prototype.
• Simple single-command startup.
• Business logic is already partially separated into:
• ingestion,
• scoring,
• prompts,
• transcript handling.
• Uses concurrent processing for SEC retrieval and article scoring.
• Has reusable prompt templates.
• Supports multiple input sources and export formats.

Limitations

• UI and business logic are still tightly coupled.
• Streamlit reruns the entire application after interactions.
• No REST or GraphQL API.
• No persistent database.
• No background job system.
• No scheduled ingestion.
• No authentication or user management.
• No durable chat sessions.
• LLM calls happen directly during UI requests.
• RSS and SEC data are fetched live.
• Long-running jobs can block the UI.
• Credentials are present in source configuration.
• Transcript uploads are stored locally.
• The chatbot custom component is constrained by Streamlit iframe behavior.
• Error handling is mostly UI-level and not centrally logged.

────────────────────

20. Current module dependency map

main/app.py
  ├── config.py
  ├── style/load_styles.py
  ├── main/components.py
  ├── main/chatbot.py
  ├── main/tabs/tab1.py
  ├── main/tabs/tab2.py
  ├── main/tabs/tab3.py
  └── main/tabs/tab4.py

main/tabs/tab1.py
  ├── config.py
  ├── main/components.py
  ├── ingestion/news_processor.py
  └── export libraries

main/tabs/tab2.py
  ├── config.py
  ├── main/components.py
  ├── ingestion/sec_fetcher.py
  ├── engine/tag_scorer.py
  ├── BeautifulSoup
  └── engine/llm_handler.py

main/tabs/tab3.py
  ├── config.py
  ├── transcripts/transcript_handler.py
  ├── engine/prompts.py
  ├── engine/llm_handler.py
  └── document libraries

ingestion/news_processor.py
  ├── ingestion/rss_fetcher.py
  ├── ingestion/sec_fetcher.py
  └── engine/tag_scorer.py

engine/tag_scorer.py
  ├── config.py
  ├── engine/prompts.py
  └── engine/llm_handler.py

engine/llm_handler.py
  ├── config.py
  └── LangChain/OpenAI-compatible provider

main/chatbot.py
  ├── Streamlit session state
  ├── engine/prompts.py
  └── engine/llm_handler.py

────────────────────

21. Architectural summary

The current Meridian Pulse architecture is best described as:

A Streamlit monolith with modular Python service-like packages, live external data ingestion, LLM-based enrichment, and session-state-only storage.

It is not yet a conventional web application with a separate frontend and backend.

The existing logical layers are already a useful foundation:

Presentation
  main/

Application orchestration
  ingestion/news_processor.py

External data adapters
  ingestion/rss_fetcher.py
  ingestion/sec_fetcher.py

AI processing
  engine/tag_scorer.py
  engine/llm_handler.py
  engine/prompts.py

Document processing
  transcripts/transcript_handler.py

Configuration
  config.py

Local assets and files
  assets/
  exports/

For a future migration, the most reusable parts are the ingestion, scoring, prompt, LLM, and transcript modules. The parts most dependent on Streamlit and requiring replacement are the tab files, session-state handling, download UI, and chatbot rendering.
import { useEffect, useMemo, useState } from "react";
import * as XLSX from "xlsx";
import Chatbot from "./Chatbot";
import { analyzeTranscript, readBundledTranscripts, readLastRun, readRecentArticles, readRecentFilings } from "./firebaseData";

const tabs = ["Urgency Dashboard", "SEC Intelligence", "Transcripts", "Behind Meridian Pulse"];
const TAGS = {
  "Time Sensitivity": 0.25,
  "Strategic Alignment": 0.2,
  "Regulatory Risk": 0.18,
  "Competitive Momentum": 0.12,
  "Financial Impact": 0.1,
  "Member Impact": 0.05,
  "Women in Healthcare": 0.1,
};
const OTHER_TAG = "Others";
const FILTER_TAGS = [...Object.keys(TAGS), OTHER_TAG];

function canonicalTitle(title) {
  return (title || "")
    .toLowerCase()
    .replace(/^google\s*-\s*[^:]+:\s*/, "")
    .replace(/\s+-\s+(stat|fierce healthcare|yahoo)\s*$/, "")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function dedupeArticles(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = canonicalTitle(item.title) || item.url;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function matchedTags(item) {
  const tags = Array.isArray(item.tags_matched)
    ? item.tags_matched
    : Object.entries(item.tags_evaluated || {})
      .filter(([, matched]) => matched)
      .map(([tag]) => tag);
  return tags.length > 0 ? tags : [OTHER_TAG];
}

function urgency(item, selectedTags) {
  return Math.min(
    1,
    selectedTags.reduce((score, tag) => score + (item.tags_evaluated?.[tag] ? TAGS[tag] : 0), 0),
  );
}

function DataCard({ item, selectedTags, filing = false }) {
  const score = urgency(item, selectedTags);
  const categories = matchedTags(item);
  return (
    <article className="data-card">
      <div className="card-meta">{item.source || item.company || "SEC EDGAR"} · {item.published || item.filed_at || "Date unavailable"}</div>
      <h2>{item.title}</h2>
      {categories.length > 0 && (
        <div className="card-tags" aria-label="Article categories">
          {categories.map((tag) => <span className="card-tag" key={tag}>{tag}</span>)}
        </div>
      )}
      <p>{item.summary || item.ai_summary || "No summary available."}</p>
      {(item.reasoning || item.ai_summary) && <small className="ai-note">AI assessment — review against the original source.</small>}
      <div className="card-bottom">
        <span>{filing ? item.form_type : `Urgency ${(score * 100).toFixed(0)}%`}</span>
        <a href={item.url || item.viewer_url} target="_blank" rel="noreferrer">Original source ↗</a>
      </div>
      {filing && <small className="ai-note">SEC information only; not investment advice.</small>}
    </article>
  );
}

function Pager({ page, total, pageSize, onPage }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  if (pageCount === 1) return null;
  return (
    <div className="pager">
      <button type="button" disabled={page === 1} onClick={() => onPage(page - 1)}>Previous</button>
      <span>Page {page} of {pageCount}</span>
      <button type="button" disabled={page === pageCount} onClick={() => onPage(page + 1)}>Next</button>
    </div>
  );
}

function downloadCsv(items, filename) {
  const columns = ["title", "source", "published", "filed_at", "form_type", "url", "summary"];
  const csv = [
    columns.join(","),
    ...items.map((item) => columns.map((column) => {
      const value = String(item[column] ?? "");
      return `"${value.replaceAll('"', '""').replaceAll("\n", " ")}"`;
    }).join(",")),
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function downloadText(content, filename, type = "text/plain") {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([content], { type }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function downloadBundledTranscript(name) {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "/api";
  const response = await fetch(`${apiBase}/transcripts/bundled/${encodeURIComponent(name)}`);
  if (!response.ok) throw new Error("Transcript download failed.");
  downloadText(await response.text(), name);
}

function exportExcel(items, filename) {
  const sheet = XLSX.utils.json_to_sheet(items.map(({ id, ...item }) => item));
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, sheet, "Meridian Pulse");
  XLSX.writeFile(workbook, filename);
}

function ExportButtons({ items, prefix }) {
  return (
    <div className="export-buttons">
      <button type="button" onClick={() => downloadCsv(items, `${prefix}.csv`)}>CSV</button>
      <button type="button" onClick={() => exportExcel(items, `${prefix}.xlsx`)}>Excel</button>
    </div>
  );
}

function TranscriptPage() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [busy, setBusy] = useState(false);
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const [bundled, setBundled] = useState([]);
  const [selectedBundled, setSelectedBundled] = useState("");
  const [bundledLoading, setBundledLoading] = useState(true);

  useEffect(() => {
    readBundledTranscripts()
      .then((names) => {
        setBundled(names);
        setSelectedBundled(names[0] || "");
      })
      .catch((requestError) => setError(requestError.message))
      .finally(() => setBundledLoading(false));
  }, []);

  async function submit(event) {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setBusyAction("upload");
    setError("");
    try {
      setAnalysis(await analyzeTranscript(file));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      setBusyAction("");
    }
  }

  async function analyzeBundled() {
    if (!selectedBundled || busy) return;
    setBusy(true);
    setBusyAction("selected");
    setError("");
    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || "/api";
      const response = await fetch(`${apiBase}/transcripts/bundled/${encodeURIComponent(selectedBundled)}`);
      if (!response.ok) throw new Error("Transcript download failed.");
      const text = await response.text();
      const selectedFile = new File([text], selectedBundled, { type: "text/plain" });
      setFile(selectedFile);
      setAnalysis(await analyzeTranscript(selectedFile));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      setBusyAction("");
    }
  }

  return (
    <section className="content">
      <h1>Transcript Intelligence</h1>
      <p className="muted">Upload a TXT, PDF, or DOCX transcript for in-memory analysis. Files are not stored.</p>
      <form className="upload-form" onSubmit={submit}>
        <input type="file" accept=".txt,.pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        <button type="submit" disabled={!file || busy}>
          {busyAction === "upload" ? "Analyzing upload..." : "Analyze transcript"}
        </button>
      </form>
      <div className="bundled-transcripts">
          <h2>Analyze an existing transcript</h2>
          {bundledLoading && <p className="status">Loading documents from assets/data...</p>}
          {bundled.length === 0 && <p className="status">No bundled transcripts could be loaded.</p>}
          <div className="bundled-picker">
            <label>Select an existing transcript ({bundled.length} available)
              <select value={selectedBundled} onChange={(event) => setSelectedBundled(event.target.value)}>
                {!selectedBundled && <option value="">Choose a document...</option>}
                {bundled.map((name) => <option value={name} key={name}>{name}</option>)}
              </select>
            </label>
            <button type="button" disabled={!selectedBundled || busy} onClick={analyzeBundled}>
              {busyAction === "selected" ? "Analyzing selected..." : "Analyze selected"}
            </button>
            <button type="button" disabled={!selectedBundled} onClick={() => downloadBundledTranscript(selectedBundled)}>Download</button>
          </div>
          {selectedBundled && <p className="muted">Selected: {selectedBundled}</p>}
      </div>
      {error && <p className="error">{error}</p>}
      {analysis && (
        <div className="analysis">
          <h2>Pulse check</h2>
          <p>{analysis.pulse_check}</p>
          {[
            ["Green signals", "green_signals"],
            ["Red signals", "red_signals"],
            ["Future horizon", "future_horizon"],
            ["Data spotlight", "data_spotlight"],
          ].map(([label, key]) => (
            <div className="analysis-block" key={key}>
              <h3>{label}</h3>
              <ul>{(analysis[key] || []).map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}</ul>
            </div>
          ))}
          <small className="ai-note">AI-generated analysis. Confirm important details against the source transcript.</small>
        </div>
      )}
    </section>
  );
}

function Feed({ items, selectedTags, filing = false }) {
  if (!items.length) return <p className="status">No matching items found in the last 48 hours.</p>;
  return <div className="data-grid">{items.map((item) => <DataCard key={item.id} item={item} selectedTags={selectedTags} filing={filing} />)}</div>;
}

export default function App() {
  const [dark, setDark] = useState(false);
  const [activeTab, setActiveTab] = useState(tabs[0]);
  const [articles, setArticles] = useState([]);
  const [filings, setFilings] = useState([]);
  const [selectedTags, setSelectedTags] = useState(["Time Sensitivity", "Regulatory Risk", "Financial Impact"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastRun, setLastRun] = useState(null);
  const [urgencyFilter, setUrgencyFilter] = useState("all");
  const [articlePage, setArticlePage] = useState(1);
  const [filingPage, setFilingPage] = useState(1);

  useEffect(() => {
    Promise.all([readRecentArticles(), readRecentFilings(), readLastRun()])
      .then(([nextArticles, nextFilings, nextLastRun]) => {
        setArticles(dedupeArticles(nextArticles.sort((a, b) => (b.published_at || "").localeCompare(a.published_at || ""))));
        setFilings(nextFilings.sort((a, b) => (b.filed_at || "").localeCompare(a.filed_at || "")));
        setLastRun(nextLastRun);
      })
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false));
  }, []);

  const rankedArticles = useMemo(
    () => [...articles]
      .filter((item) => {
        const categories = matchedTags(item);
      return selectedTags.length === 0
        ? categories.includes(OTHER_TAG)
        : selectedTags.some((tag) => categories.includes(tag));
    })
      .filter((item) => urgencyFilter === "all" || (
        urgency(item, selectedTags) >= Number(urgencyFilter)
      ))
      .sort((a, b) => urgency(b, selectedTags) - urgency(a, selectedTags)),
    [articles, selectedTags, urgencyFilter],
  );
  const filteredFilings = filings;
  const pageSize = 12;
  const visibleArticles = rankedArticles.slice((articlePage - 1) * pageSize, articlePage * pageSize);
  const visibleFilings = filteredFilings.slice((filingPage - 1) * pageSize, filingPage * pageSize);

  function toggleTag(tag) {
    setSelectedTags((current) => current.includes(tag)
      ? current.filter((value) => value !== tag)
      : current.length < 3 ? [...current, tag] : current);
    setArticlePage(1);
  }

  const updatedText = lastRun?.finished_at
    ? `Updated ${new Date(lastRun.finished_at).toLocaleString()}`
    : "Awaiting first ingestion run";

  return (
    <main className={dark ? "app dark" : "app"}>
      <header className="hero">
        <button className="theme-toggle" type="button" onClick={() => setDark(!dark)}>{dark ? "Day" : "Night"}</button>
        <div className="hero-title">Meridian Pulse</div>
        <div className="hero-tagline">Where healthcare intelligence peaks</div>
      </header>
      <nav className="tabs" aria-label="Application sections">
        {tabs.map((tab) => <button type="button" className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)} key={tab}>{tab}</button>)}
      </nav>
      {activeTab === "Urgency Dashboard" && (
        <section className="content">
          <h1>Urgency Dashboard</h1>
          <p className="muted">Fresh healthcare intelligence from the last 48 hours. Select a category to show only related articles.</p>
          <p className="freshness">{updatedText}</p>
          <div className="tag-filters">
            {FILTER_TAGS.map((tag) => <button type="button" className={selectedTags.includes(tag) ? "selected" : ""} onClick={() => toggleTag(tag)} key={tag}>{tag}</button>)}
          </div>
          <div className="toolbar">
            <label>Minimum urgency
              <select value={urgencyFilter} onChange={(event) => { setUrgencyFilter(event.target.value); setArticlePage(1); }}>
                <option value="all">All</option><option value="0.5">High</option><option value="0.2">Medium+</option><option value="0.05">Any signal</option>
              </select>
            </label>
            <ExportButtons items={rankedArticles} prefix="meridian-pulse-articles" />
          </div>
          {loading && <p className="status">Loading Firebase data...</p>}
          {error && <p className="error">{error}</p>}
          {!loading && !error && <><Feed items={visibleArticles} selectedTags={selectedTags} /><Pager page={articlePage} total={rankedArticles.length} pageSize={pageSize} onPage={setArticlePage} /></>}
        </section>
      )}
      {activeTab === "SEC Intelligence" && (
        <section className="content">
          <h1>SEC Intelligence</h1>
          <p className="muted">SEC filings from tracked healthcare companies retained by the intelligence pipeline.</p>
          <p className="freshness">{updatedText}</p>
          <div className="toolbar">
            <ExportButtons items={filteredFilings} prefix="meridian-pulse-sec-filings" />
          </div>
          {loading && <p className="status">Loading Firebase data...</p>}
          {error && <p className="error">{error}</p>}
          {!loading && !error && <><Feed items={visibleFilings} selectedTags={selectedTags} filing /><Pager page={filingPage} total={filteredFilings.length} pageSize={pageSize} onPage={setFilingPage} /></>}
        </section>
      )}
      {activeTab === "Transcripts" && <TranscriptPage />}
      {activeTab === "Behind Meridian Pulse" && (
        <section className="placeholder">
          <h1>Behind Meridian Pulse</h1>
          <h2>Akansha Rawat</h2>
          <p className="muted">Healthcare AI and Strategy</p>
          <p>
            Meridian Pulse was built to solve a real problem: healthcare strategy
            teams spending hours on manual news research. It brings that work
            down to minutes using urgency scoring, live data pipelines, and
            intelligent filtering.
          </p>
          <div className="linkedin-card">
            <a href="https://www.linkedin.com/in/akansharawat01/" target="_blank" rel="noreferrer">
              <img src={`${import.meta.env.BASE_URL}linkedin.png`} alt="Akansha Rawat LinkedIn QR code" />
            </a>
            <p><a href="mailto:amrawat@uci.edu">Email</a>{" · "}<a href="https://www.linkedin.com/in/akansharawat01/" target="_blank" rel="noreferrer">LinkedIn</a></p>
          </div>
        </section>
      )}
      <footer className="site-footer">
        <span>Public healthcare intelligence research tool.</span>
        <a href="mailto:amrawat@uci.edu">Corrections and takedowns</a>
        <a href={`${import.meta.env.BASE_URL}GOVERNANCE.md`}>Governance</a>
      </footer>
      <Chatbot dark={dark} articleContext={rankedArticles} />
    </main>
  );
}

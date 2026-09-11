const DATABASE_URL = (
  import.meta.env.VITE_FIREBASE_DATABASE_URL ||
  "https://meridian-pulse-94152-default-rtdb.firebaseio.com"
).replace(/\/$/, "");

function toRecords(payload) {
  return Object.entries(payload || {}).map(([id, value]) => ({ id, ...value }));
}

async function readPath(path, params = {}) {
  const query = new URLSearchParams({ ...params, format: "export" });
  const response = await fetch(`${DATABASE_URL}/${path}.json?${query}`);
  if (!response.ok) throw new Error(`Firebase read failed (${response.status}).`);
  return toRecords(await response.json());
}

export function readRecentArticles() {
  const start = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
  return readPath("articles", {
    orderBy: JSON.stringify("published_at"),
    startAt: JSON.stringify(start),
    limitToLast: "50",
  });
}

export function readRecentFilings() {
  const start = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
  return readPath("sec_filings", {
    orderBy: JSON.stringify("filed_at"),
    startAt: JSON.stringify(start),
    limitToLast: "50",
  });
}

export async function readLastRun() {
  const response = await fetch(`${DATABASE_URL}/meta/last_run.json`);
  if (!response.ok) throw new Error(`Firebase read failed (${response.status}).`);
  return response.json();
}

export async function analyzeTranscript(file) {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const formData = new FormData();
  formData.append("upload", file);
  const response = await fetch(`${apiBase}/transcripts/analyze`, {
    method: "POST",
    body: formData,
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "Transcript analysis failed.");
  return body;
}

export async function readBundledTranscripts() {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(`${apiBase}/transcripts/bundled`);
  if (!response.ok) throw new Error(`Transcript list failed (${response.status}).`);
  return response.json();
}

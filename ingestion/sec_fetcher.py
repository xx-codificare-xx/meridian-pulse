# import requests
# import time
# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import (
#     SEC_SUBMISSIONS_BASE,
#     SEC_FULL_SEARCH_BASE,
#     SEC_HEADERS,
#     SEC_HEALTHCARE_CIKS,
#     SEC_RATE_LIMIT_SLEEP,
#     MAX_ARTICLES_PER_SOURCE,
# )

# RELEVANT_FORMS = {"8-K", "10-K", "10-Q", "DEF 14A"}


# def get_company_filings(company_name: str, cik: str) -> list:
#     """Fetch recent filings for a company from SEC EDGAR."""
#     cik_padded = cik.zfill(10)
#     url = f"{SEC_SUBMISSIONS_BASE}/CIK{cik_padded}.json"

#     try:
#         response = requests.get(url, headers=SEC_HEADERS, timeout=10)
#         response.raise_for_status()
#         data = response.json()
#     except Exception as e:
#         print(f"[SEC] Failed for {company_name}: {e}")
#         return []

#     filings      = data.get("filings", {}).get("recent", {})
#     forms        = filings.get("form", [])
#     dates        = filings.get("filingDate", [])
#     accessions   = filings.get("accessionNumber", [])
#     descriptions = filings.get("primaryDocument", [])

#     articles = []
#     count    = 0

#     for i, form in enumerate(forms):
#         if form not in RELEVANT_FORMS:
#             continue
#         if count >= MAX_ARTICLES_PER_SOURCE:
#             break

#         cik_plain   = str(int(cik))
#         viewer_url  = (
#             f"https://www.sec.gov/cgi-bin/browse-edgar?"
#             f"action=getcompany&CIK={cik_plain}"
#             f"&type={form}&dateb=&owner=include&count=10"
#         )

#         articles.append({
#             "id":            accessions[i],
#             "title":         f"{company_name}: {form} Filing ({dates[i]})",
#             "summary":       (
#                 f"{company_name} submitted a {form} filing to the SEC on {dates[i]}. "
#                 f"Document: {descriptions[i]}. This filing may contain material "
#                 f"information about the company's financial position, strategy, or operations."
#             ),
#             "url":           viewer_url,
#             "source":        f"SEC EDGAR - {company_name}",
#             "published":     dates[i],
#             "type":          "sec_filing",
#             "form_type":     form,
#             "company":       company_name,
#             "tags_matched":  [],
#             "urgency_score": 0.0,
#             "urgency_label": "Unscored",
#         })
#         count += 1
#         time.sleep(SEC_RATE_LIMIT_SLEEP)

#     print(f"[SEC] {company_name}: {len(articles)} filings")
#     return articles


# def fetch_all_sec() -> list:
#     """Fetch filings for all configured healthcare companies."""
#     all_filings = []
#     for company, cik in SEC_HEALTHCARE_CIKS.items():
#         filings = get_company_filings(company, cik)
#         all_filings.extend(filings)

#     print(f"\n[SEC] Total filings fetched: {len(all_filings)}")
#     return all_filings


# if __name__ == "__main__":
#     filings = fetch_all_sec()
#     for f in filings[:3]:
#         print(f"\n{f['company']} | {f['form_type']} | {f['published']}")
#         print(f"  {f['title']}")
#         print(f"  {f['url']}")
import requests
import time
import sys
import os
from io import BytesIO
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    SEC_SUBMISSIONS_BASE,
    SEC_HEADERS,
    SEC_HEALTHCARE_CIKS,
    SEC_RATE_LIMIT_SLEEP,
    MAX_ARTICLES_PER_SOURCE,
)

RELEVANT_FORMS = {"8-K", "10-K", "10-Q", "DEF 14A"}
MAX_FILING_BYTES = 5 * 1024 * 1024


def _cik_parts(cik: str) -> tuple[str, str]:
    digits = str(cik).strip()
    if not digits.isdigit():
        raise ValueError(f"Invalid SEC CIK: {cik!r}")
    return digits.zfill(10), str(int(digits))


def _get_sec_json(url: str) -> dict:
    response = requests.get(url, headers=SEC_HEADERS, timeout=10)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "json" not in content_type:
        raise ValueError(f"SEC returned non-JSON content for {url}")
    data = response.json()
    time.sleep(SEC_RATE_LIMIT_SLEEP)
    return data


def download_filing_text(url: str) -> str | None:
    """Download at most 5 MB of filing HTML and extract readable text."""
    try:
        response = requests.get(
            url,
            headers=SEC_HEADERS,
            stream=True,
            timeout=20,
        )
        response.raise_for_status()
        content = BytesIO()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            content.write(chunk)
            if content.tell() > MAX_FILING_BYTES:
                return None
        html = content.getvalue()
    except requests.RequestException as error:
        print(f"[SEC] Filing download failed: {error}")
        return None

    try:
        from lxml import html as lxml_html
        document = lxml_html.fromstring(html)
        return " ".join(document.text_content().split())[:20000]
    except (ImportError, ValueError, TypeError) as error:
        print(f"[SEC] Filing parsing failed: {error}")
        return None


def summarize_filing(article: dict) -> dict:
    text = download_filing_text(article["doc_url"])
    if not text:
        article["summary_unavailable"] = True
        return article
    try:
        from engine.llm_handler import ask_llm
        article["ai_summary"] = ask_llm(
            "Summarize this SEC filing in 3 concise sentences for a healthcare "
            "strategy analyst. Return only the summary.\n\n" + text,
        )
        article["summary_unavailable"] = False
    except Exception as error:
        print(f"[SEC] Summary failed for {article['id']}: {error}")
        article["summary_unavailable"] = True
    return article


def get_company_filings(company_name: str, cik: str) -> list:
    cik_padded, cik_plain = _cik_parts(cik)
    url        = f"{SEC_SUBMISSIONS_BASE}/CIK{cik_padded}.json"

    try:
        data = _get_sec_json(url)
    except (requests.RequestException, ValueError) as error:
        print(f"[SEC] Failed for {company_name}: {error}")
        return []

    filings    = data.get("filings", {}).get("recent", {})
    forms      = filings.get("form", [])
    dates      = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])
    documents  = filings.get("primaryDocument", [])

    articles = []
    count    = 0

    for i, form in enumerate(forms):
        if form not in RELEVANT_FORMS:
            continue
        if count >= MAX_ARTICLES_PER_SOURCE:
            break

        viewer_url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar?"
            f"action=getcompany&CIK={cik_plain}"
            f"&type={form}&dateb=&owner=include&count=10"
        )

        accession_clean = accessions[i].replace("-", "")
        document = documents[i] if i < len(documents) else ""
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_plain}/{accession_clean}/{document}"
            if document else
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_plain}/{accession_clean}/{accessions[i]}-index.htm"
        )

        articles.append({
            "id":            accessions[i],
            "title":         f"{company_name} {form} Filing ({dates[i]})",
            "summary":       (
                f"{company_name} filed a {form} with the SEC on {dates[i]}. "
                f"Click Summarize to get AI intelligence on this filing."
            ),
            "url":           viewer_url,
            "doc_url":       doc_url,
            "source":        f"SEC EDGAR {company_name}",
            "published":     dates[i],
            "filed_at":      dates[i],
            "cik":           cik_plain,
            "type":          "sec_filing",
            "form_type":     form,
            "company":       company_name,
            "tags_matched":  [],
            "urgency_score": 0.0,
            "urgency_label": "Unscored",
            "summary_unavailable": False,
        })
        count += 1

    print(f"[SEC] {company_name}: {len(articles)} filings")
    return articles


def fetch_all_sec() -> list:
    """Fetch filings for all companies in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    all_filings = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(get_company_filings, company, cik): company
            for company, cik in SEC_HEALTHCARE_CIKS.items()
        }
        for future in as_completed(futures):
            try:
                filings = future.result()
                all_filings.extend(filings)
            except Exception as e:
                print(f"[SEC] Thread error: {e}")

    print(f"[SEC] Total filings: {len(all_filings)}")
    return all_filings


if __name__ == "__main__":
    filings = fetch_all_sec()
    for f in filings[:3]:
        print(f"\n{f['company']} | {f['form_type']} | {f['published']}")
        print(f"  {f['url']}")
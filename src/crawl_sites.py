"""Polite, bounded crawler for already-discovered candidate company websites."""

from __future__ import annotations

import argparse
import csv
import time
from collections import deque
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

USER_AGENT = "VATDiscoveryResearch/0.1 (interview proof-of-concept)"
PREFERRED = ("contact", "about", "terms", "legal", "privacy", "footer", "invoice", "vat")
FIELDS = ["company_number", "company_name", "postcode", "website", "page_url", "status", "content_type",
          "elapsed_ms", "error", "text"]


def canonical_url(url: str) -> str:
    clean, _ = urldefrag(url)
    return clean


def same_host(left: str, right: str) -> bool:
    return urlparse(left).hostname == urlparse(right).hostname


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()
    return " ".join(soup.stripped_strings)


def links(html: str, base: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for anchor in soup.find_all("a", href=True):
        url = canonical_url(urljoin(base, anchor["href"]))
        if url.startswith(("http://", "https://")) and same_host(base, url):
            candidates.append(url)
    return sorted(set(candidates), key=lambda url: (not any(word in url.lower() for word in PREFERRED), url))


def crawl(row: dict[str, str], max_pages: int, delay: float, timeout: float) -> list[dict[str, object]]:
    website = row.get("website", "").strip()
    if not website:
        return []
    if not website.startswith(("http://", "https://")):
        website = "https://" + website
    robot = RobotFileParser(urljoin(website, "/robots.txt"))
    try:
        robot.read()
    except Exception:
        robot = None
    queue, seen, output = deque([canonical_url(website)]), set(), []
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    while queue and len(output) < max_pages:
        url = queue.popleft()
        if url in seen or (robot and not robot.can_fetch(USER_AGENT, url)):
            continue
        seen.add(url)
        started = time.perf_counter()
        record: dict[str, object] = {"company_number": row.get("company_number", ""),
                                    "company_name": row.get("company_name", ""),
                                    "postcode": row.get("postcode", ""),
                                    "website": website, "page_url": url, "status": "", "content_type": "",
                                    "elapsed_ms": "", "error": "", "text": ""}
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            record["status"] = response.status_code
            record["content_type"] = response.headers.get("content-type", "").split(";")[0]
            if response.ok and "html" in str(record["content_type"]):
                record["text"] = page_text(response.text)
                for candidate in links(response.text, response.url):
                    if candidate not in seen:
                        queue.append(candidate)
        except requests.RequestException as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        record["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
        output.append(record)
        if delay:
            time.sleep(delay)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/website_candidates.csv"))
    parser.add_argument("--output", type=Path, default=Path("results/crawl_results.csv"))
    parser.add_argument("--max-pages", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=12)
    parser.add_argument("--allowed-status", action="append", default=["CONFIDENT", "PROVISIONAL"],
                        help="website discovery status eligible for crawling; repeat as needed")
    args = parser.parse_args()
    with args.input.open("r", encoding="utf-8-sig", newline="") as stream:
        all_companies = list(csv.DictReader(stream))
    companies = [row for row in all_companies if row.get("status", "").upper() in args.allowed_status]
    results = [page for company in companies for page in crawl(company, args.max_pages, args.delay, args.timeout)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f"companies={len(companies)} pages_attempted={len(results)}")


if __name__ == "__main__":
    main()

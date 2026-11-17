"""Bring real job postings in: from links to public job pages, or from a CSV file.

Links are fetched by the server, so the fetcher only talks to public internet
addresses (no private, loopback or link-local hosts, checked again on every
redirect), with a size and time limit. A page's schema.org JobPosting data is
used when present (most job boards publish it); otherwise the page's visible text.
"""

from __future__ import annotations

import asyncio
import csv
import io
import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

MAX_URLS = 20
MAX_CSV_ROWS = 200
MAX_CSV_BYTES = 2_000_000
MAX_PAGE_BYTES = 2_000_000
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = 15.0
MIN_TEXT_CHARS = 40
MAX_TEXT_CHARS = 20_000
USER_AGENT = "ObelyticsJobImporter/1.0 (+curriculum skills analysis)"


class ImportFailedError(Exception):
    """A posting could not be imported; the message is shown to the user."""


@dataclass
class ImportedPosting:
    title: str
    employer: str | None
    text: str
    source: str | None


# ── Fetching ─────────────────────────────────────────────────────────────────


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ImportFailedError("Only http and https links can be imported.")
    if parts.port not in (None, 80, 443):
        raise ImportFailedError("Only links on the standard web ports can be imported.")
    if parts.username or parts.password:
        raise ImportFailedError("Links with a user name or password can't be imported.")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            parts.hostname, None, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ImportFailedError("The site could not be found.") from exc
    if not infos or not all(_is_public(info[4][0]) for info in infos):
        raise ImportFailedError("That address is not a public website.")


async def fetch_page(url: str, client: httpx.AsyncClient | None = None) -> tuple[str, str]:
    """Return (final URL, HTML) for a public web page."""
    own = client is None
    client = client or httpx.AsyncClient(
        timeout=TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        current = url.strip()
        for _ in range(MAX_REDIRECTS + 1):
            await _check_url(current)
            async with client.stream("GET", current) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ImportFailedError("The site redirected without saying where.")
                    current = urljoin(current, location)
                    continue
                if response.status_code >= 400:
                    raise ImportFailedError(f"The site answered with error {response.status_code}.")
                kind = response.headers.get("content-type", "")
                if "html" not in kind and "text" not in kind:
                    raise ImportFailedError("The link is not a web page.")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_PAGE_BYTES:
                        raise ImportFailedError("The page is too large.")
                encoding = response.encoding or "utf-8"
                return current, body.decode(encoding, errors="replace")
        raise ImportFailedError("The site redirected too many times.")
    except httpx.HTTPError as exc:
        raise ImportFailedError("The page could not be downloaded.") from exc
    finally:
        if own:
            await client.aclose()


# ── Reading a page ───────────────────────────────────────────────────────────


class _PageText(HTMLParser):
    """Visible text, the <title>, and any JSON-LD blocks of an HTML page."""

    _SKIP = {"script", "style", "noscript", "template", "svg", "nav", "footer", "header", "form"}
    _BREAK = {
        "p",
        "div",
        "br",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "tr",
        "section",
        "article",
        "ul",
        "ol",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self.json_ld: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._in_json_ld = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type", "").lower() == "application/ld+json":
            self._in_json_ld, self._buffer = True, []
            return
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self._in_json_ld and tag == "script":
            self.json_ld.append("".join(self._buffer))
            self._in_json_ld = False
            return
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_json_ld:
            self._buffer.append(data)
        elif self._in_title:
            self.title += data
        elif not self._skip_depth:
            self.parts.append(data)


def _clean(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)  # JobPosting descriptions are often HTML
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _job_postings(node) -> list[dict]:
    """Every schema.org JobPosting object inside a JSON-LD value."""
    found: list[dict] = []
    if isinstance(node, list):
        for item in node:
            found.extend(_job_postings(item))
    elif isinstance(node, dict):
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "JobPosting" in kinds:
            found.append(node)
        for key in ("@graph", "mainEntity", "itemListElement", "item"):
            if key in node:
                found.extend(_job_postings(node[key]))
    return found


def _employer(posting: dict) -> str | None:
    org = posting.get("hiringOrganization")
    if isinstance(org, dict):
        return _clean(str(org.get("name") or "")) or None
    if isinstance(org, str):
        return _clean(org) or None
    return None


def read_page(html: str, url: str) -> ImportedPosting:
    parser = _PageText()
    parser.feed(html)
    parser.close()
    for block in parser.json_ld:
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for posting in _job_postings(data):
            description = _clean(str(posting.get("description") or ""))
            title = _clean(str(posting.get("title") or ""))
            if title and len(description) >= MIN_TEXT_CHARS:
                skills = posting.get("skills") or posting.get("qualifications")
                extra = f"\n\n{_clean(str(skills))}" if isinstance(skills, str) else ""
                return ImportedPosting(
                    title=title[:255],
                    employer=(_employer(posting) or "")[:255] or None,
                    text=(description + extra)[:MAX_TEXT_CHARS],
                    source=url[:500],
                )
    text = _clean("".join(parser.parts))
    title = _clean(parser.title).split(" | ")[0].split(" - ")[0].strip()
    if len(text) < MIN_TEXT_CHARS or not title:
        raise ImportFailedError("No job description was found on the page.")
    return ImportedPosting(
        title=title[:255], employer=None, text=text[:MAX_TEXT_CHARS], source=url[:500]
    )


async def posting_from_url(url: str, client: httpx.AsyncClient | None = None) -> ImportedPosting:
    final_url, html = await fetch_page(url, client)
    return read_page(html, final_url)


# ── CSV ──────────────────────────────────────────────────────────────────────

_COLUMNS = {
    "title": ("title", "job title", "position", "job_title", "role"),
    "employer": ("employer", "company", "organization", "organisation", "company name"),
    "text": (
        "description",
        "text",
        "job description",
        "details",
        "job_description",
        "requirements",
    ),
    "source": ("url", "link", "source", "job url"),
}


def read_csv(data: bytes) -> tuple[list[ImportedPosting], list[str]]:
    """Postings from a CSV export, plus a message for each row that was skipped."""
    if len(data) > MAX_CSV_BYTES:
        raise ImportFailedError("The file is larger than 2 MB.")
    text = data.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = {(h or "").strip().lower(): h for h in reader.fieldnames or []}
    columns = {
        field: next((headers[n] for n in names if n in headers), None)
        for field, names in _COLUMNS.items()
    }
    if not columns["title"] or not columns["text"]:
        raise ImportFailedError("The file needs a title column and a description column.")
    postings: list[ImportedPosting] = []
    skipped: list[str] = []
    for number, row in enumerate(reader, start=2):
        if len(postings) >= MAX_CSV_ROWS:
            skipped.append(f"Rows after {MAX_CSV_ROWS} postings were not read.")
            break
        title = _clean(row.get(columns["title"]) or "")
        body = _clean(row.get(columns["text"]) or "")
        if not title or len(body) < MIN_TEXT_CHARS:
            skipped.append(
                f"Row {number}: needs a title and a description of at least {MIN_TEXT_CHARS} characters."
            )
            continue
        employer = _clean(row.get(columns["employer"]) or "") if columns["employer"] else ""
        source = (row.get(columns["source"]) or "").strip() if columns["source"] else ""
        postings.append(
            ImportedPosting(
                title=title[:255],
                employer=employer[:255] or None,
                text=body[:MAX_TEXT_CHARS],
                source=source[:500] or None,
            )
        )
    return postings, skipped

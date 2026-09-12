import os
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from kizashi.dates import parse_dd_mon_yyyy, parse_mm_dd_yyyy, parse_yyyymm

BMF_URLS = {
    1: "https://www.irs.gov/pub/irs-soi/eo1.csv",
    2: "https://www.irs.gov/pub/irs-soi/eo2.csv",
    3: "https://www.irs.gov/pub/irs-soi/eo3.csv",
    4: "https://www.irs.gov/pub/irs-soi/eo4.csv",
}
POSTCARD_URL = "https://apps.irs.gov/pub/epostcard/data-download-epostcard.zip"
REVOCATION_URL = "https://apps.irs.gov/pub/epostcard/data-download-revocation.zip"


@dataclass(frozen=True)
class BmfRow:
    ein: str
    name: str
    city: str
    state: str
    zip: str
    group: str
    subsection: str
    affiliation: str
    ruling: date | None
    status: str
    tax_period_end: date | None
    filing_req: str
    acct_pd: int | None


@dataclass(frozen=True)
class PostcardRow:
    ein: str
    tax_year: int
    name: str
    terminated: bool
    period_begin: date | None
    period_end: date | None
    city: str
    state: str


@dataclass(frozen=True)
class RevocationRow:
    ein: str
    name: str
    city: str
    state: str
    subsection: str
    revocation_date: date
    posting_date: date | None
    reinstatement_date: date | None


@dataclass(frozen=True)
class SourceMeta:
    name: str
    url: str
    last_modified: str
    rows: int
    path: Path


def fetch(url: str, dest: Path, force: bool = False) -> SourceMeta:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_modified = None
    if dest.exists() and not force and not url.endswith(".zip"):
        last_modified = datetime.fromtimestamp(dest.stat().st_mtime, tz=timezone.utc).date().isoformat()
        rows = sum(1 for _ in open(dest, "rb"))
        return SourceMeta(name=dest.name, url=url, last_modified=last_modified, rows=rows, path=dest)
    extracted = dest.with_suffix(".txt") if url.endswith(".zip") else dest
    if extracted.exists() and not force:
        last_modified = datetime.fromtimestamp(extracted.stat().st_mtime, tz=timezone.utc).date().isoformat()
        rows = sum(1 for _ in open(extracted, "rb"))
        return SourceMeta(name=extracted.name, url=url, last_modified=last_modified, rows=rows, path=extracted)
    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as response:
        response.raise_for_status()
        header_last_modified = response.headers.get("last-modified")
        with open(dest, "wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
    if header_last_modified:
        parsed = datetime.strptime(header_last_modified, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        last_modified = parsed.date().isoformat()
        os.utime(dest, (parsed.timestamp(), parsed.timestamp()))
    else:
        last_modified = datetime.fromtimestamp(dest.stat().st_mtime, tz=timezone.utc).date().isoformat()
    if url.endswith(".zip"):
        with zipfile.ZipFile(dest) as zf:
            names = [n for n in zf.namelist() if n.endswith(".txt")]
            zf.extractall(dest.parent)
        extracted = dest.parent / names[0]
        if header_last_modified:
            os.utime(extracted, (parsed.timestamp(), parsed.timestamp()))
        rows = sum(1 for _ in open(extracted, "rb"))
        return SourceMeta(name=extracted.name, url=url, last_modified=last_modified, rows=rows, path=extracted)
    rows = sum(1 for _ in open(dest, "rb"))
    return SourceMeta(name=dest.name, url=url, last_modified=last_modified, rows=rows, path=dest)


def _empty_to_none(s: str) -> str | None:
    s = s.strip()
    return s if s else None


def read_bmf(path: Path) -> dict[str, BmfRow]:
    import csv

    rows: dict[str, BmfRow] = {}
    with open(path, newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ein = r["EIN"].strip()
            acct_pd_raw = r["ACCT_PD"].strip()
            rows[ein] = BmfRow(
                ein=ein,
                name=r["NAME"].strip(),
                city=r["CITY"].strip(),
                state=r["STATE"].strip(),
                zip=r["ZIP"].strip(),
                group=r["GROUP"].strip(),
                subsection=r["SUBSECTION"].strip(),
                affiliation=r["AFFILIATION"].strip(),
                ruling=parse_yyyymm(r["RULING"]),
                status=r["STATUS"].strip(),
                tax_period_end=parse_yyyymm(r["TAX_PERIOD"]),
                filing_req=r["FILING_REQ_CD"].strip(),
                acct_pd=int(acct_pd_raw) if acct_pd_raw else None,
            )
    return rows


def read_postcards(path: Path) -> dict[str, PostcardRow]:
    rows: dict[str, PostcardRow] = {}
    with open(path, encoding="latin-1", newline="") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("|")
            ein = parts[0].strip()
            rows[ein] = PostcardRow(
                ein=ein,
                tax_year=int(parts[1]),
                name=parts[2].strip(),
                terminated=parts[4].strip() == "T",
                period_begin=parse_mm_dd_yyyy(parts[5]),
                period_end=parse_mm_dd_yyyy(parts[6]),
                city=parts[18].strip() if len(parts) > 18 else "",
                state=parts[20].strip() if len(parts) > 20 else "",
            )
    return rows


def read_revocations(path: Path) -> dict[str, RevocationRow]:
    staged: dict[str, RevocationRow] = {}
    with open(path, encoding="latin-1", newline="") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("|")
            ein = parts[0].strip()
            revocation_date = parse_dd_mon_yyyy(parts[9])
            if revocation_date is None:
                continue
            row = RevocationRow(
                ein=ein,
                name=parts[1].strip(),
                city=parts[4].strip(),
                state=parts[5].strip(),
                subsection=parts[8].strip(),
                revocation_date=revocation_date,
                posting_date=parse_dd_mon_yyyy(parts[10]) if len(parts) > 10 else None,
                reinstatement_date=parse_dd_mon_yyyy(parts[11]) if len(parts) > 11 else None,
            )
            existing = staged.get(ein)
            if existing is None or row.revocation_date > existing.revocation_date:
                staged[ein] = row
    return staged

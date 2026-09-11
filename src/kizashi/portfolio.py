import csv
from dataclasses import dataclass
from pathlib import Path

from kizashi.sources import BmfRow


@dataclass(frozen=True)
class Portfolio:
    name: str
    source: str
    eins: list[str]


def load_portfolio_csv(path: Path, name: str) -> Portfolio:
    eins: list[str] = []
    seen: set[str] = set()
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            cell = row[0].strip()
            if not cell.isdigit():
                continue
            if cell not in seen:
                seen.add(cell)
                eins.append(cell)
    return Portfolio(name=name, source=str(path), eins=eins)


def build_portfolio_from_bmf(bmf: dict[str, BmfRow], state: str, zip3: str, filing_req: str = "02") -> Portfolio:
    eins = [
        r.ein
        for r in bmf.values()
        if r.state == state and r.zip.startswith(zip3) and r.filing_req == filing_req
    ]
    name = f"{state} zip3={zip3} small nonprofits"
    source = f"bmf state={state} zip3={zip3} filing_req={filing_req}"
    return Portfolio(name=name, source=source, eins=eins)

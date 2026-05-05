"""Parse every VA SCC Bureau of Insurance annual report PDF into two parquets:

  va_complaints_yearly.parquet           — per-line workload (P&C / L&H received)
  va_external_review_yearly.parquet      — health-appeals disposition table

The PDFs are tiny (2 pages each, 4 years currently). Page 2 has a flat list of
"Activity: NUMBER" lines (1-per-row) and a separate "External Review" block.
We regex-match lines for fixed labels.

Mapping of the External Review dispositions onto the project's canonical
4-bucket outcome taxonomy:

  against_insurer = Overturned + Reversed-Itself   (regulator action favored consumer)
  for_insurer     = Upheld                         (regulator agreed with carrier denial)
  mixed           = Modified or Partially Overturned
  no_decision     = Ineligible + Terminated/withdrawn

Note: the External Review block covers health-coverage appeals only, not all
VA insurance complaints. The workload parquet captures the headline P&C and
L&H complaints-received scalars; those have no published outcome breakdown
and stay in line-chart mode.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "va_scc" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "va_scc" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Workload labels we expect on each report's activity page.
WORKLOAD_PATTERNS = {
    "property_and_casualty": re.compile(
        r"Property\s+and\s+Casualty\s+insurance\s+complaints\s+received\s+([\d,]+)",
        re.IGNORECASE,
    ),
    "life_and_health": re.compile(
        r"Life\s+and\s+Health\s+insurance\s+complaints\s+received\s+([\d,]+)",
        re.IGNORECASE,
    ),
}

# External Review (health-appeal) labels. The OCR sometimes mis-reads "1" as
# "I" in the FY2023 report; we accept either.
ER_PATTERNS = {
    "total_reviewed":     re.compile(r"Number\s+of\s+External\s+Review.*?Reviewed\s+([\d,]+)", re.IGNORECASE),
    "eligible":           re.compile(r"\bEligible\s+ER\s+Requests\s+([\d,]+)", re.IGNORECASE),
    "ineligible":         re.compile(r"Ineligible\s+ER\s+Requests\s+([\d,]+)", re.IGNORECASE),
    "upheld":             re.compile(r"Final\s+Adverse\s+Decision\s+Upheld\s+by\s+Reviewer\s+([\d,IiOo]+)", re.IGNORECASE),
    "overturned":         re.compile(r"Final\s+Adverse\s+Decision\s+Overturned\s+by\s+Reviewer\s+([\d,IiOo]+)", re.IGNORECASE),
    "modified":           re.compile(r"Final\s+Adverse\s+Decision\s+Modified\s+or\s+Partially\s+Overturned\s+([\d,IiOo]+)", re.IGNORECASE),
    "reversed_self":      re.compile(r"Health\s+Carrier\s+Reversed\s+Itself\s+([\d,IiOo]+)", re.IGNORECASE),
    "terminated":         re.compile(r"Terminated\s+or\s+withdrawn\s+([\d,IiOo]+)", re.IGNORECASE),
}


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def parse_int_with_ocr_quirks(s: str) -> int:
    """Convert a captured number-like string to int, normalizing OCR-misread
    'I' → '1' and 'O' → '0'. Strip thousands separators."""
    if s is None:
        return None
    norm = s.replace(",", "").replace("I", "1").replace("i", "1").replace("O", "0").replace("o", "0")
    return int(norm)


def parse_pdf(path: Path, fy: int) -> tuple[dict, dict]:
    """Returns (workload_dict, er_dict) where each maps a metric name to int."""
    import pdfplumber

    full_text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            full_text.append(page.extract_text() or "")
    text = "\n".join(full_text)

    workload: dict[str, int] = {}
    for line_slug, pat in WORKLOAD_PATTERNS.items():
        m = pat.search(text)
        if m is None:
            raise RuntimeError(
                f"FY{fy}: missing workload pattern for {line_slug!r}; "
                f"VA SCC report layout may have changed."
            )
        workload[line_slug] = parse_int_with_ocr_quirks(m.group(1))

    er: dict[str, int] = {}
    for slug, pat in ER_PATTERNS.items():
        m = pat.search(text)
        if m is None:
            raise RuntimeError(
                f"FY{fy}: missing external-review pattern for {slug!r}; "
                f"layout may have changed."
            )
        er[slug] = parse_int_with_ocr_quirks(m.group(1))

    return workload, er


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found. Run 01_download.py first.", file=sys.stderr)
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST_PATH.read_text())
    files = manifest["files"]

    workload_rows: list[dict] = []
    er_rows: list[dict] = []

    with LOG_PATH.open("a") as logf:
        log(f"\n=== run started {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)

        for f in files:
            path = FILES_DIR / f["filename"]
            fy = f["fiscal_year"]
            try:
                workload, er = parse_pdf(path, fy)
            except Exception as e:
                log(f"  HARD FAILURE parsing {path.name}: {e}", logf)
                return 3

            for line_slug, n in workload.items():
                workload_rows.append({
                    "fiscal_year": fy,
                    "line": line_slug,
                    "complaints_received": n,
                    "source_file": path.name,
                })

            er_row = {
                "fiscal_year": fy,
                "total_reviewed": er["total_reviewed"],
                "eligible": er["eligible"],
                "ineligible": er["ineligible"],
                "upheld": er["upheld"],
                "overturned": er["overturned"],
                "modified": er["modified"],
                "reversed_self": er["reversed_self"],
                "terminated": er["terminated"],
                "source_file": path.name,
            }
            # Canonical 4-bucket projection (see module docstring for mapping).
            er_row["against_insurer"] = er["overturned"] + er["reversed_self"]
            er_row["for_insurer"] = er["upheld"]
            er_row["mixed"] = er["modified"]
            er_row["no_decision"] = er["ineligible"] + er["terminated"]
            er_row["on_merits"] = (
                er_row["against_insurer"] + er_row["for_insurer"] + er_row["mixed"]
            )
            er_row["against_rate_of_decided"] = (
                er_row["against_insurer"] / er_row["on_merits"]
                if er_row["on_merits"] > 0 else None
            )
            er_rows.append(er_row)

            log(f"  FY{fy}: P&C={workload['property_and_casualty']:,} "
                f"L&H={workload['life_and_health']:,} "
                f"ER reviewed={er['total_reviewed']:,} "
                f"(against={er_row['against_insurer']}, "
                f"for={er_row['for_insurer']}, "
                f"mixed={er_row['mixed']}, "
                f"no_dec={er_row['no_decision']})", logf)

        if not workload_rows or not er_rows:
            log("HARD FAILURE: no rows parsed", logf)
            return 4

        # Sanity: eligible == upheld + overturned + modified + reversed_self + terminated.
        # Some years have a small discrepancy (FY2024 +10); we don't fail on it
        # but log a warning.
        for r in er_rows:
            sum_dispositions = r["upheld"] + r["overturned"] + r["modified"] + r["reversed_self"] + r["terminated"]
            if sum_dispositions != r["eligible"]:
                log(f"  WARNING FY{r['fiscal_year']}: sum(dispositions)={sum_dispositions} "
                    f"vs eligible={r['eligible']} (delta={sum_dispositions - r['eligible']})", logf)

        # ---- Output 1: per-line workload ----
        wk = pl.DataFrame(workload_rows, schema={
            "fiscal_year": pl.Int32,
            "line": pl.String,
            "complaints_received": pl.Int64,
            "source_file": pl.String,
        }).sort(["fiscal_year", "line"])
        wk_pq = OUTPUT_DIR / "va_complaints_yearly.parquet"
        wk_csv = OUTPUT_DIR / "va_complaints_yearly.csv"
        wk.write_parquet(wk_pq)
        wk.write_csv(wk_csv)
        log(f"Wrote {wk_pq.name} ({len(wk)} rows)", logf)

        # ---- Output 2: external-review disposition ----
        er_df = pl.DataFrame(er_rows, schema={
            "fiscal_year": pl.Int32,
            "total_reviewed": pl.Int64,
            "eligible": pl.Int64,
            "ineligible": pl.Int64,
            "upheld": pl.Int64,
            "overturned": pl.Int64,
            "modified": pl.Int64,
            "reversed_self": pl.Int64,
            "terminated": pl.Int64,
            "source_file": pl.String,
            "against_insurer": pl.Int64,
            "for_insurer": pl.Int64,
            "mixed": pl.Int64,
            "no_decision": pl.Int64,
            "on_merits": pl.Int64,
            "against_rate_of_decided": pl.Float64,
        }).sort("fiscal_year")
        er_pq = OUTPUT_DIR / "va_external_review_yearly.parquet"
        er_csv = OUTPUT_DIR / "va_external_review_yearly.csv"
        er_df.write_parquet(er_pq)
        er_df.write_csv(er_csv)
        log(f"Wrote {er_pq.name} ({len(er_df)} rows)", logf)

        # ---- Soft sanity: lifetime aggregate ----
        a = er_df["against_insurer"].sum()
        m = er_df["on_merits"].sum()
        log(f"\nLifetime ER aggregate: {a}/{m} = {a/m*100:.2f}% against-insurer (of decided)", logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Parse CDI Annual Reports + Consumer Complaint Studies into tidy outputs.

Inputs (from 01_download.py):
  ca_cdi/interim/annual_reports/{YYYY}.pdf  (5 files, 2020-2024)
  ca_cdi/interim/composites/{YYYY}-{auto|home|life}.pdf  (9 files)

Outputs:
  ca_cdi/output/ca_complaints_state_yearly.{parquet,csv}
  ca_cdi/output/ca_complaints_state_by_line_pct.{parquet,csv}
  ca_cdi/output/ca_complaints_company_yearly.{parquet,csv}
  ca_cdi/output/ca_complaints_yearly_justified.{parquet,csv}
  ca_cdi/output/run_log.txt   (appended)
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM = PROJECT_ROOT / "ca_cdi" / "interim"
AR_DIR = INTERIM / "annual_reports"
COMP_DIR = INTERIM / "composites"
OUTPUT = PROJECT_ROOT / "ca_cdi" / "output"
LOG_PATH = OUTPUT / "run_log.txt"


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


# ----------------- Annual Report parsing -----------------

LINE_PCT_HEADER = "PERCENTAGE OF COMPLAINTS BY LINES OF COVERAGE"

# The 8 coverage labels CDI uses, exactly as printed on the page.
AR_COVERAGE_LABELS = [
    "Automobile",
    "Accident & Health",
    "Homeowners",
    "Misc./Other",
    "Life & Annuity",
    "Fire, Allied Lines & CMP",
    "Liability",
    "Earthquake",
]


def parse_annual_report(year: int, pdf_path: Path):
    """Returns (state_yearly_row, list_of_line_pct_rows)."""
    state_row = {"year": year}
    line_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        all_text = []
        for page in pdf.pages:
            all_text.append(page.extract_text() or "")
        joined = "\n".join(all_text)

    # 1. Complaint Cases Opened/Closed and Dollars Recovered.
    m = re.search(r"Complaint Cases Opened\s+([\d,]+)", joined)
    if m:
        state_row["complaints_opened"] = int(m.group(1).replace(",", ""))
    m = re.search(r"Complaint Cases Closed\s+([\d,]+)", joined)
    if m:
        state_row["complaints_closed"] = int(m.group(1).replace(",", ""))
    m = re.search(r"Total Amount of Consumer Dollars Recovered\s+\$?([\d,]+)", joined)
    if m:
        state_row["consumer_dollars_recovered"] = int(m.group(1).replace(",", ""))
    m = re.search(r"Consumer Telephone Calls and In[- ]Person Assistance\s+([\d,]+)", joined)
    if m:
        state_row["telephone_and_in_person_assistance"] = int(m.group(1).replace(",", ""))

    # 2. Percentage by line of coverage. The table starts with LINE_PCT_HEADER and
    #    is followed by a "Coverage Type YYYY YYYY YYYY YYYY" header line, then
    #    one row per coverage label. Each row: <label> + 4 percentage tokens.
    idx = joined.find(LINE_PCT_HEADER)
    if idx == -1:
        return state_row, line_rows
    chunk = joined[idx : idx + 1500]
    # Find the year header.
    year_hdr = re.search(r"Coverage Type\s+((?:\d{4}\s+){3,4}\d{4})", chunk)
    if year_hdr is None:
        return state_row, line_rows
    years = [int(y) for y in year_hdr.group(1).split()]
    # For each coverage label, find a row in the chunk that starts with the label
    # and is followed by len(years) percentage tokens.
    for label in AR_COVERAGE_LABELS:
        # Escape label and use as a regex literal.
        # The PDF text sometimes has slight variations; we tolerate trailing
        # whitespace and look for percentages immediately after.
        pat = re.escape(label) + r"\s+" + r"\s+".join([r"([\d.]+)\s*%"] * len(years))
        m = re.search(pat, chunk)
        if not m:
            continue
        for i, y in enumerate(years):
            line_rows.append({
                "year": y,
                "coverage_type": label,
                "percentage": float(m.group(i + 1)),
                "source_ar_year": year,
            })
    return state_row, line_rows


# ----------------- Composite Study parsing -----------------

# The composite per-company row pattern: rank, name, exposure, 3 ratios, 3 counts.
# Exposure is comma-grouped (e.g., 1,234,567). Ratios are decimals. Counts are
# integers. Anchoring on the last 7 numeric tokens makes us robust to spaces in
# company names.
ROW_RE = re.compile(
    r"^\s*(\d+)\s+(.+?)\s+([\d,]+)\s+"
    r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s*$"
)


def parse_composite(study_year: int, line: str, pdf_path: Path) -> list[dict]:
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            for ln in txt.split("\n"):
                m = ROW_RE.match(ln)
                if not m:
                    continue
                rank = int(m.group(1))
                name = m.group(2).strip()
                exposure = int(m.group(3).replace(",", ""))
                ratios = [float(m.group(i)) for i in (4, 5, 6)]
                counts = [int(m.group(i)) for i in (7, 8, 9)]
                # The 3 columns map to study_year-1, study_year-2, study_year-3.
                # E.g., the 2025 study reports "Complaint Years 2024, 2023, 2022".
                for offset, (ratio, count) in enumerate(zip(ratios, counts)):
                    data_year = study_year - 1 - offset
                    rows.append({
                        "study_year": study_year,
                        "data_year": data_year,
                        "line": line,
                        "rank_in_study": rank,
                        "company_name": name,
                        "exposure": exposure,
                        "justified_ratio": ratio,
                        "justified_count": count,
                    })
    return rows


def normalize_company_name(name: str) -> str:
    """Collapse whitespace + uppercase. Companies sometimes appear in title
    case in older studies and ALL CAPS in newer ones; uppercasing makes the
    dedup join across studies behave."""
    return re.sub(r"\s+", " ", name).strip().upper()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a") as logf:
        run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log(f"\n=== run started {run_started} ===", logf)

        # ---- Annual Reports ----
        log("Parsing Annual Reports:", logf)
        state_rows = []
        line_pct_rows = []
        for year in (2020, 2021, 2022, 2023, 2024):
            pdf_path = AR_DIR / f"{year}.pdf"
            sr, lr = parse_annual_report(year, pdf_path)
            log(f"  {year}: closed={sr.get('complaints_closed')}, opened={sr.get('complaints_opened')}, line_pct_rows={len(lr)}", logf)
            state_rows.append(sr)
            line_pct_rows.extend(lr)

        state_yr = pl.DataFrame(state_rows).sort("year")
        # Dedup line_pct: keep the most recent source_ar_year per (year, coverage_type).
        line_pct = (
            pl.DataFrame(line_pct_rows)
            .sort("source_ar_year", descending=True)
            .unique(subset=["year", "coverage_type"], keep="first")
            .sort(["year", "coverage_type"])
        )
        state_yr.write_parquet(OUTPUT / "ca_complaints_state_yearly.parquet")
        state_yr.write_csv(OUTPUT / "ca_complaints_state_yearly.csv")
        line_pct.write_parquet(OUTPUT / "ca_complaints_state_by_line_pct.parquet")
        line_pct.write_csv(OUTPUT / "ca_complaints_state_by_line_pct.csv")
        log(f"Wrote ca_complaints_state_yearly.parquet ({len(state_yr)} rows)", logf)
        log(f"Wrote ca_complaints_state_by_line_pct.parquet ({len(line_pct)} rows)", logf)

        # ---- Composite Studies ----
        log("\nParsing Consumer Complaint Studies:", logf)
        all_company_rows = []
        for study_year in (2023, 2024, 2025):
            for line in ("auto", "home", "life"):
                pdf_path = COMP_DIR / f"{study_year}-{line}.pdf"
                rows = parse_composite(study_year, line, pdf_path)
                # Each PDF should contain 50 companies × 3 data years = 150 rows.
                n_companies = len({(r["line"], r["company_name"]) for r in rows})
                log(f"  {study_year}-{line}: {len(rows)} rows ({n_companies} companies)", logf)
                if n_companies < 45:
                    log(f"    WARN: expected ~50 companies, got {n_companies}", logf)
                all_company_rows.extend(rows)

        comp = pl.DataFrame(all_company_rows)
        comp = comp.with_columns(
            pl.col("company_name")
            .map_elements(normalize_company_name, return_dtype=pl.String)
            .alias("company_canonical")
        )

        # Dedup: for each (data_year, line, company_canonical), keep the row from
        # the most recent study_year (CDI's most recent calculation wins on conflict).
        company_yearly = (
            comp.sort("study_year", descending=True)
            .unique(subset=["data_year", "line", "company_canonical"], keep="first")
            .sort(["data_year", "line", "rank_in_study"])
            .rename({"data_year": "year"})
            .select([
                "year", "line", "rank_in_study", "company_canonical", "company_name",
                "exposure", "justified_ratio", "justified_count",
                "study_year",
            ])
        )
        company_yearly.write_parquet(OUTPUT / "ca_complaints_company_yearly.parquet")
        company_yearly.write_csv(OUTPUT / "ca_complaints_company_yearly.csv")
        log(f"\nWrote ca_complaints_company_yearly.parquet ({len(company_yearly)} rows)", logf)

        # ---- Aggregate: per-line per-year sum across the top-50 from the
        # MOST RECENT study covering that year. Using the deduped
        # company_yearly would include companies from every study that ever
        # ranked them — a union across rolling windows that inflates the count.
        # Instead, group `comp` (pre-dedup) by (year, line, study_year), keep
        # the rows from the max study_year per (year, line), and sum those.
        latest_study_per_year_line = (
            comp.group_by(["data_year", "line"])
            .agg(pl.col("study_year").max().alias("latest_study"))
            .rename({"data_year": "year"})
        )
        agg = (
            comp.rename({"data_year": "year"})
            .join(
                latest_study_per_year_line,
                left_on=["year", "line", "study_year"],
                right_on=["year", "line", "latest_study"],
                how="inner",
            )
            .group_by(["year", "line", "study_year"])
            .agg(
                pl.col("justified_count").sum().alias("total_justified_top50"),
                pl.col("exposure").sum().alias("total_exposure_top50"),
                pl.len().alias("n_companies"),
            )
            .with_columns(
                justified_per_100k_exposure=(
                    pl.col("total_justified_top50") / pl.col("total_exposure_top50") * 100_000
                )
            )
            .rename({"study_year": "source_study_year"})
            .sort(["year", "line"])
        )
        agg.write_parquet(OUTPUT / "ca_complaints_yearly_justified.parquet")
        agg.write_csv(OUTPUT / "ca_complaints_yearly_justified.csv")
        log(f"Wrote ca_complaints_yearly_justified.parquet ({len(agg)} rows)", logf)

        # ---- Soft sanity table to log ----
        log("\n--- ca_complaints_state_yearly ---", logf)
        with pl.Config(tbl_rows=20):
            log(str(state_yr), logf)
        log("\n--- ca_complaints_yearly_justified ---", logf)
        with pl.Config(tbl_rows=20):
            log(str(agg), logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Parse WA OIC IFCA PDFs + Annual Report PDFs into tidy outputs.

Inputs (from 01_download.py):
  wa_oic/interim/ifca/{2025,2026}.pdf
  wa_oic/interim/annual_reports/{2020..2024}.pdf

Outputs:
  wa_oic/output/wa_ifca_notices.{parquet,csv}
  wa_oic/output/wa_ifca_notices_yearly.{parquet,csv}
  wa_oic/output/wa_complaints_state_yearly.{parquet,csv}
  wa_oic/output/run_log.txt   (appended)
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM = PROJECT_ROOT / "wa_oic" / "interim"
IFCA_DIR = INTERIM / "ifca"
AR_DIR = INTERIM / "annual_reports"
OUTPUT = PROJECT_ROOT / "wa_oic" / "output"
LOG_PATH = OUTPUT / "run_log.txt"

IFCA_COLUMNS = [
    "ifca_number",
    "date_received",
    "postmark_date",
    "insurance_company",
    "complainant_individual",
    "complainant_business",
    "complainant_attorney",
    "line_of_insurance",
    "rcw_wac_cited",
    "notes",
]


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def flatten_cell(v) -> str:
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v).replace("\n", " ").strip())


# Lightweight line normalization. The IFCA "Line of Insurance" column is
# free-text-ish; we coalesce common variations into a small canonical set.
LINE_NORMALIZATION = [
    (re.compile(r"\b(uim|under[- ]?insured\s+motorist)\b", re.I), "UIM"),
    (re.compile(r"\b(um\b|uninsured\s+motorist)\b", re.I), "UM"),
    (re.compile(r"\bpip\b|personal\s+injury\s+protection", re.I), "PIP"),
    (re.compile(r"motor\s+vehicle|auto(?:mobile)?(?:[ -]+(?!\bglass\b))?", re.I), "Auto"),
    (re.compile(r"homeowner|home owners", re.I), "Homeowners"),
    (re.compile(r"\bproperty\b", re.I), "Property"),
    (re.compile(r"liability", re.I), "Liability"),
    (re.compile(r"health|medical", re.I), "Health"),
    (re.compile(r"life", re.I), "Life"),
    (re.compile(r"title", re.I), "Title"),
    (re.compile(r"workers?\s*comp", re.I), "Workers Comp"),
]


def normalize_line(raw: str) -> str:
    if not raw:
        return "Unknown"
    s = raw.strip()
    for pat, label in LINE_NORMALIZATION:
        if pat.search(s):
            return label
    return "Other"


def parse_ifca_pdf(year: int, pdf_path: Path, logf) -> list[dict]:
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for t in tables:
                if not t:
                    continue
                # Detect header row.
                start = 0
                if t[0] and t[0][0] and "IFCA" in (t[0][0] or "") and t[0][0].strip().startswith("IFCA"):
                    start = 1
                for raw_row in t[start:]:
                    if not raw_row:
                        continue
                    # Pad/trim to 10 columns; some pages have an extra trailing empty col.
                    cells = [flatten_cell(v) for v in raw_row[:10]]
                    while len(cells) < 10:
                        cells.append("")
                    # Skip rows where IFCA # is empty.
                    if not cells[0] or not cells[0].strip():
                        continue
                    # Validate IFCA # shape: NNNN.YY
                    if not re.match(r"^\d{1,5}\.\d{2}$", cells[0]):
                        continue
                    rows.append({k: v for k, v in zip(IFCA_COLUMNS, cells)})
        logf.write(f"  ifca {year}: {len(rows)} notices from {len(pdf.pages)} pages\n")
    return rows


# ---------------- Annual Report parsing ----------------

# Match: "Processed 10,127 consumer complaints, resulting in recovery of over $27.4 million..."
COMPLAINTS_RE = re.compile(r"Processed\s+([\d,]+)\s+consumer\s+complaints", re.I)
RECOVERY_RE = re.compile(r"recovery\s+of\s+over\s+\$([\d.]+)\s*million", re.I)


def parse_annual_report(year: int, pdf_path: Path, logf) -> dict:
    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text.append(page.extract_text() or "")
    joined = "\n".join(full_text)

    m_c = COMPLAINTS_RE.search(joined)
    m_r = RECOVERY_RE.search(joined)
    return {
        "year": year,
        "total_complaints": int(m_c.group(1).replace(",", "")) if m_c else None,
        "recoveries_millions": float(m_r.group(1)) if m_r else None,
    }


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as logf:
        run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log(f"\n=== run started {run_started} ===", logf)

        # ---- IFCA ----
        log("\n[ifca]", logf)
        ifca_rows: list[dict] = []
        for year in (2025, 2026):
            pdf_path = IFCA_DIR / f"{year}.pdf"
            ifca_rows.extend(parse_ifca_pdf(year, pdf_path, logf))
        if not ifca_rows:
            log("HARD FAIL: no IFCA rows parsed", logf)
            return 2

        df_ifca = pl.DataFrame(ifca_rows)
        # Derive data_year from the IFCA # suffix.
        df_ifca = df_ifca.with_columns(
            data_year=(
                pl.col("ifca_number")
                .str.extract(r"\.(\d{2})$", 1)
                .cast(pl.Int32)
                + 2000
            ),
            line_normalized=pl.col("line_of_insurance").map_elements(
                normalize_line, return_dtype=pl.String
            ),
            date_received_dt=pl.col("date_received").str.to_date(
                "%m/%d/%Y", strict=False
            ),
        )

        # Sanity: every row's data_year is within the expected set.
        bad_years = df_ifca.filter(~pl.col("data_year").is_in([2025, 2026])).height
        if bad_years > 0:
            log(f"  WARN: {bad_years} IFCA rows with unexpected data_year", logf)

        # Soft check: IFCA # sequence completeness per year.
        for y in (2025, 2026):
            seq = (
                df_ifca.filter(pl.col("data_year") == y)
                .with_columns(
                    seq=pl.col("ifca_number").str.extract(r"^(\d+)\.", 1).cast(pl.Int32)
                )
                .sort("seq")
            )
            if seq.height:
                lo, hi = int(seq["seq"].min()), int(seq["seq"].max())
                expected = hi - lo + 1
                gap = expected - seq.height
                log(
                    f"  ifca {y}: seq {lo:04d}..{hi:04d} ({seq.height} rows, "
                    f"expected {expected}, missing {gap})",
                    logf,
                )

        df_ifca.write_parquet(OUTPUT / "wa_ifca_notices.parquet")
        df_ifca.write_csv(OUTPUT / "wa_ifca_notices.csv")
        log(f"Wrote wa_ifca_notices.parquet ({len(df_ifca)} rows)", logf)

        # Yearly rollup.
        per_line = (
            df_ifca.group_by(["data_year", "line_normalized"])
            .agg(pl.len().alias("count"))
            .rename({"line_normalized": "line", "data_year": "year"})
            .sort(["year", "line"])
        )
        per_year = (
            df_ifca.group_by("data_year")
            .agg(pl.len().alias("count"))
            .with_columns(line=pl.lit("ALL"))
            .rename({"data_year": "year"})
            .select(["year", "line", "count"])
        )
        yearly = pl.concat([per_year, per_line]).sort(["year", "line"])
        yearly.write_parquet(OUTPUT / "wa_ifca_notices_yearly.parquet")
        yearly.write_csv(OUTPUT / "wa_ifca_notices_yearly.csv")
        log(f"Wrote wa_ifca_notices_yearly.parquet ({len(yearly)} rows)", logf)
        with pl.Config(tbl_rows=40):
            log(str(yearly), logf)

        # ---- Annual Reports ----
        log("\n[annual reports]", logf)
        ar_rows: list[dict] = []
        for year in (2020, 2021, 2022, 2023, 2024):
            pdf_path = AR_DIR / f"{year}.pdf"
            row = parse_annual_report(year, pdf_path, logf)
            log(f"  AR {year}: complaints={row['total_complaints']}, recoveries_M={row['recoveries_millions']}", logf)
            if row["total_complaints"] is None:
                log(f"  HARD FAIL: AR {year} did not match the complaints regex", logf)
                return 3
            ar_rows.append(row)
        df_ar = pl.DataFrame(ar_rows)
        df_ar.write_parquet(OUTPUT / "wa_complaints_state_yearly.parquet")
        df_ar.write_csv(OUTPUT / "wa_complaints_state_yearly.csv")
        log(f"Wrote wa_complaints_state_yearly.parquet ({len(df_ar)} rows)", logf)
        with pl.Config(tbl_rows=10):
            log(str(df_ar), logf)

        log(
            f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===",
            logf,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

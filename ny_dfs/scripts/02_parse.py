"""Parse NY DFS auto + health PDFs into tidy outputs.

Inputs (from 01_download.py):
  ny_dfs/interim/h2wd-9xfe.parquet
  ny_dfs/interim/health/{guide_year}.pdf  (10 files)

Outputs:
  ny_dfs/output/ny_auto_complaints_company_year.{parquet,csv}
  ny_dfs/output/ny_auto_complaints_yearly.{parquet,csv}
  ny_dfs/output/ny_health_complaints_company_year.{parquet,csv}
  ny_dfs/output/ny_health_complaints_yearly.{parquet,csv}
  ny_dfs/output/run_log.txt   (appended)
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM = PROJECT_ROOT / "ny_dfs" / "interim"
HEALTH_DIR = INTERIM / "health"
AUTO_PARQUET = INTERIM / "h2wd-9xfe.parquet"
OUTPUT = PROJECT_ROOT / "ny_dfs" / "output"
LOG_PATH = OUTPUT / "run_log.txt"

NUM = r"[\d,]+(?:\.\d+)?"
HMO_ROW_RE = re.compile(r"^(.+?)\s+" + r"\s+".join([f"({NUM})"] * 7) + r"\s*$")
PLAN_ROW_RE = re.compile(r"^(.+?)\s+" + r"\s+".join([f"({NUM})"] * 5) + r"\s*$")
TOTAL_HMO_RE = re.compile(r"^Total\s+" + r"\s+".join([f"({NUM})"] * 5) + r"\s*$")
TOTAL_PLAN_RE = re.compile(r"^Total\s+" + r"\s+".join([f"({NUM})"] * 4) + r"\s*$")

# Detect table title and data year. Em-dash or hyphen between "Complaints" and type.
TITLE_RE = re.compile(
    r"Complaints[—–\-]\s*(HMOs?|EPO/PPO[^\n]*?Plans?|Commercial[^\n]*?Companies?)\s+(\d{4})"
)


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def parse_num(s: str) -> float:
    return float(s.replace(",", ""))


# ----------------- Auto -----------------

def parse_auto(logf) -> tuple[pl.DataFrame, pl.DataFrame]:
    raw = pl.read_parquet(AUTO_PARQUET)
    log(f"Auto: loaded {len(raw):,} rows", logf)
    df = raw.with_columns(
        pl.col("naic").cast(pl.Int64, strict=False),
        pl.col("filing_year").cast(pl.Int32, strict=False),
        pl.col("ratio").cast(pl.Float64, strict=False),
        pl.col("upheld_complaints").cast(pl.Int64, strict=False),
        pl.col("question_of_fact_complaints").cast(pl.Int64, strict=False),
        pl.col("not_upheld_complaints").cast(pl.Int64, strict=False),
        pl.col("total_complaints").cast(pl.Int64, strict=False),
        pl.col("premiums_written_in_millions").cast(pl.Float64, strict=False),
        pl.col("rank").cast(pl.Int32, strict=False),
    ).sort(["filing_year", "rank"])

    # Soft check: total_complaints should equal upheld + question_of_fact + not_upheld within ±1.
    mismatch = df.with_columns(
        delta=(
            pl.col("total_complaints")
            - pl.col("upheld_complaints")
            - pl.col("question_of_fact_complaints")
            - pl.col("not_upheld_complaints")
        )
    ).filter(pl.col("delta").abs() > 1)
    if len(mismatch) > 0:
        log(f"Auto soft-warn: {len(mismatch)} rows where total ≠ upheld+QoF+not_upheld (±1)", logf)

    yearly = (
        df.group_by("filing_year")
        .agg(
            pl.col("upheld_complaints").sum().alias("total_upheld_2yr"),
            pl.col("question_of_fact_complaints").sum().alias("total_question_of_fact_2yr"),
            pl.col("not_upheld_complaints").sum().alias("total_not_upheld_2yr"),
            pl.col("total_complaints").sum().alias("total_complaints_2yr"),
            pl.col("premiums_written_in_millions").sum().alias("total_premiums_millions_2yr_avg"),
            pl.len().alias("n_companies"),
        )
        .with_columns(
            statewide_complaint_ratio=(
                pl.col("total_upheld_2yr") / pl.col("total_premiums_millions_2yr_avg")
            )
        )
        .sort("filing_year")
        .rename({"filing_year": "year"})
    )
    return df, yearly


# ----------------- Health -----------------

PLAN_TYPE_MAP = {
    "hmo": "HMO",
    "epo/ppo": "EPO/PPO",
    "commercial": "Commercial",
}


def normalize_plan_type(raw: str) -> str:
    r = raw.lower()
    if r.startswith("hmo"):
        return "HMO"
    if "epo/ppo" in r or "epo / ppo" in r or r.startswith("epo"):
        return "EPO/PPO"
    if "commercial" in r:
        return "Commercial"
    return raw


def parse_health(guide_year: int, pdf_path: Path, logf) -> list[dict]:
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            m = TITLE_RE.search(txt)
            if not m:
                continue
            plan_type = normalize_plan_type(m.group(1))
            data_year = int(m.group(2))
            # Walk through subsequent lines on this page, parsing data rows.
            lines = txt.split("\n")
            # Find the line index where the title is, skip header.
            title_idx = next(
                (i for i, ln in enumerate(lines) if TITLE_RE.search(ln)), 0
            )
            row_re = HMO_ROW_RE if plan_type == "HMO" else PLAN_ROW_RE
            total_re = TOTAL_HMO_RE if plan_type == "HMO" else TOTAL_PLAN_RE
            n_data_rows = 0
            for ln in lines[title_idx + 1:]:
                ln_strip = ln.strip()
                if not ln_strip or ln_strip.lower().startswith("total"):
                    # Skip the Total summary; we sum from data rows.
                    if total_re.match(ln_strip):
                        continue
                    continue
                m = row_re.match(ln_strip)
                if not m:
                    continue
                groups = m.groups()
                name = groups[0].strip()
                # Strip trailing footnote markers like "2,3" off plan names.
                name = re.sub(r"\s*\d+(?:,\d+)*$", "", name)
                if plan_type == "HMO":
                    row = {
                        "data_year": data_year,
                        "guide_year": guide_year,
                        "plan_type": plan_type,
                        "plan_name": name,
                        "rank": int(parse_num(groups[1])),
                        "total_complaints_dfs": int(parse_num(groups[2])),
                        "upheld_complaints_dfs": int(parse_num(groups[3])),
                        "premiums_millions": parse_num(groups[4]),
                        "complaint_ratio_dfs": parse_num(groups[5]),
                        "total_complaints_doh": int(parse_num(groups[6])),
                        "upheld_complaints_doh": int(parse_num(groups[7])),
                    }
                else:
                    row = {
                        "data_year": data_year,
                        "guide_year": guide_year,
                        "plan_type": plan_type,
                        "plan_name": name,
                        "rank": int(parse_num(groups[1])),
                        "total_complaints_dfs": int(parse_num(groups[2])),
                        "upheld_complaints_dfs": int(parse_num(groups[3])),
                        "premiums_millions": parse_num(groups[4]),
                        "complaint_ratio_dfs": parse_num(groups[5]),
                        "total_complaints_doh": None,
                        "upheld_complaints_doh": None,
                    }
                rows.append(row)
                n_data_rows += 1
            log(f"  guide={guide_year} page={page_idx + 1} {plan_type} {data_year}: {n_data_rows} rows", logf)
    return rows


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as logf:
        run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log(f"\n=== run started {run_started} ===", logf)

        # ---- Auto ----
        log("\n[auto]", logf)
        auto_company_year, auto_yearly = parse_auto(logf)
        auto_company_year.write_parquet(OUTPUT / "ny_auto_complaints_company_year.parquet")
        auto_company_year.write_csv(OUTPUT / "ny_auto_complaints_company_year.csv")
        auto_yearly.write_parquet(OUTPUT / "ny_auto_complaints_yearly.parquet")
        auto_yearly.write_csv(OUTPUT / "ny_auto_complaints_yearly.csv")
        log(f"Wrote ny_auto_complaints_company_year.parquet ({len(auto_company_year)} rows)", logf)
        log(f"Wrote ny_auto_complaints_yearly.parquet ({len(auto_yearly)} rows)", logf)
        with pl.Config(tbl_rows=20):
            log(str(auto_yearly), logf)

        # ---- Health ----
        log("\n[health]", logf)
        all_health: list[dict] = []
        for guide_year in range(2016, 2026):
            pdf_path = HEALTH_DIR / f"{guide_year}.pdf"
            if not pdf_path.exists():
                log(f"  WARN: missing {pdf_path}", logf)
                continue
            rows = parse_health(guide_year, pdf_path, logf)
            if not rows:
                log(f"  HARD FAIL: 0 rows from {guide_year} guide", logf)
                return 2
            all_health.extend(rows)

        # Dedup: each (data_year, plan_type, plan_name) may appear in 1-2 guides
        # (same data is sometimes reprinted next year). Keep the most recent guide_year.
        comp = pl.DataFrame(all_health)
        n_raw = len(comp)
        comp = (
            comp.sort("guide_year", descending=True)
            .unique(subset=["data_year", "plan_type", "plan_name"], keep="first")
            .sort(["data_year", "plan_type", "rank"])
        )
        log(f"Health: {n_raw} raw rows -> {len(comp)} after dedup", logf)
        comp.write_parquet(OUTPUT / "ny_health_complaints_company_year.parquet")
        comp.write_csv(OUTPUT / "ny_health_complaints_company_year.csv")
        log(f"Wrote ny_health_complaints_company_year.parquet ({len(comp)} rows)", logf)

        # Yearly health rollup by plan_type.
        yearly = (
            comp.group_by(["data_year", "plan_type"])
            .agg(
                pl.col("total_complaints_dfs").sum().alias("total_complaints_dfs"),
                pl.col("upheld_complaints_dfs").sum().alias("upheld_complaints_dfs"),
                pl.col("premiums_millions").sum().alias("premiums_millions"),
                pl.col("total_complaints_doh").sum().alias("total_complaints_doh"),
                pl.col("upheld_complaints_doh").sum().alias("upheld_complaints_doh"),
                pl.len().alias("n_plans"),
            )
            .with_columns(
                upheld_per_million_premium=(
                    pl.col("upheld_complaints_dfs") / pl.col("premiums_millions")
                )
            )
            .sort(["data_year", "plan_type"])
            .rename({"data_year": "year"})
        )
        yearly.write_parquet(OUTPUT / "ny_health_complaints_yearly.parquet")
        yearly.write_csv(OUTPUT / "ny_health_complaints_yearly.csv")
        log(f"Wrote ny_health_complaints_yearly.parquet ({len(yearly)} rows)", logf)
        with pl.Config(tbl_rows=40):
            log(str(yearly), logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())

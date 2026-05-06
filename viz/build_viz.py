"""Build a unified self-contained HTML data viewer.

Discovers every <dataset>/viz_manifest.json under the project root, loads each
entry's parquet, pivots to a uniform shape, and emits viz/index.html with the
master payload embedded inline.

Adding a new dataset = drop in folder + add manifest + rerun this script.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_HTML = PROJECT_ROOT / "viz" / "index.html"

# User-curated taxonomy. Maps each manifest entry id to one of three buckets
# the sidebar groups by:
#   complaints_with_outcomes — entries with a 4-bucket outcome breakdown
#   complaint_volume         — regulator complaint counts/indexes/recoveries
#                              (FL CRN included: regulator-mediated pre-suit)
#   lawsuit_volume           — federal filings + WA IFCA pre-suit notices
# Why explicit: FL CRN and WA IFCA share `category=plaintiff_allegation` but
# split across buckets, so derivation from category alone won't work.
PLOT_TYPE_BY_ENTRY_ID = {
    # complaints_with_outcomes
    "ct_cid":         "complaints_with_outcomes",
    "tx_tdi":         "complaints_with_outcomes",
    "or_dfr":         "complaints_with_outcomes",
    "md_mia":         "complaints_with_outcomes",
    "ny_dfs_auto":    "complaints_with_outcomes",
    "ny_dfs_health":  "complaints_with_outcomes",
    "va_scc_er":      "complaints_with_outcomes",
    "mo_dci":         "complaints_with_outcomes",
    # ca_cdi_top50 has outcome_buckets in its manifest, but only the
    # against_insurer bucket is populated — there's no on-merits denominator,
    # so the rate panel can't render. Treat it as a complaint-volume series.
    "ca_cdi_top50":   "complaint_volume",
    # complaint_volume
    "id_doi":              "complaint_volume",
    "ks_kid":              "complaint_volume",
    "il_idoi":             "complaint_volume",
    "in_idoi":             "complaint_volume",
    "mi_difs_yearly":      "complaint_volume",
    "co_doi_workload":     "complaint_volume",
    "co_doi_recoveries":   "complaint_volume",
    "va_scc_workload":     "complaint_volume",
    "wa_oic_ar":           "complaint_volume",
    "la_ldi":              "complaint_volume",
    "fl_crn":              "complaint_volume",
    "ca_cdi_state":        "complaint_volume",
    "wi_oci":              "complaint_volume",
    "naic_idrr":           "complaint_volume",
    # (ca_cdi_top50 declared above, near outcome group, with comment)
    # lawsuit_volume
    "wa_ifca": "lawsuit_volume",
    "fjc_idb": "lawsuit_volume",
}

# Entries whose `jurisdiction` is `["US"]` but whose `group_field` enumerates
# states. State pages slice these to one state's series; the Nationwide page
# shows them in their full national form.
MULTI_STATE_ENTRY_IDS = {"fjc_idb", "naic_idrr"}


def collect_manifests() -> list[Path]:
    paths = sorted(PROJECT_ROOT.glob("*/viz_manifest.json"))
    return paths


def build_entry_payload(manifest_path: Path, entry: dict) -> dict:
    """For a single entry: load its parquet, pivot to {group: [values_aligned_to_years]}
    per metric, and return a payload dict."""
    parquet_rel = entry["parquet"]
    df = pl.read_parquet(PROJECT_ROOT / parquet_rel)

    x_field = entry["x_field"]
    group_field = entry.get("group_field")  # may be None for state-level scalar series
    filter_field = entry.get("filter_field")  # optional secondary categorical filter
    metrics = entry["metrics"]
    metric_columns = [m["column"] for m in metrics]

    # Cast x to int year. Different parquets use different x dtypes; coerce.
    df = df.with_columns(pl.col(x_field).cast(pl.Int32, strict=False))

    # Build the universe of years.
    years = sorted({int(y) for y in df[x_field].unique() if y is not None})

    # If there's a filter_field, the JS-side filter shows different group sets per
    # filter value. Build the data partitioned by filter value.
    filter_values: list[str | None] = [None]
    if filter_field is not None:
        filter_values = sorted(
            {v for v in df[filter_field].unique().to_list() if v is not None}
        )

    # group_field may be None — we treat that as a single group "ALL_SERIES".
    has_group = group_field is not None

    data_by_filter: dict[str, dict] = {}
    for fv in filter_values:
        sub = df if filter_field is None else df.filter(pl.col(filter_field) == fv)

        if has_group:
            groups = sorted(
                {g for g in sub[group_field].unique().to_list() if g is not None}
            )
        else:
            groups = ["__series__"]

        # For each metric × group, build a values array aligned to years.
        metrics_data: dict[str, dict[str, list]] = {}
        for col in metric_columns:
            metrics_data[col] = {}
            if has_group:
                for g in groups:
                    g_rows = sub.filter(pl.col(group_field) == g)
                    by_year = dict(zip(g_rows[x_field].to_list(), g_rows[col].to_list()))
                    metrics_data[col][g] = [
                        _to_jsonable(by_year.get(y)) for y in years
                    ]
            else:
                by_year = dict(zip(sub[x_field].to_list(), sub[col].to_list()))
                metrics_data[col]["__series__"] = [
                    _to_jsonable(by_year.get(y)) for y in years
                ]

        data_by_filter[str(fv) if fv is not None else "__no_filter__"] = {
            "groups": groups,
            "metrics_data": metrics_data,
        }

    # Compute "top_n_by_metric" default groups if requested.
    default_groups = entry.get("default_groups")
    if default_groups is None and entry.get("default_groups_strategy") == "top_n_by_metric":
        n = int(entry.get("default_groups_n", 10))
        metric_col = entry["default_groups_metric"]
        # If filter_field present, compute defaults per filter value separately;
        # JS code chooses the right list based on the active filter value.
        default_groups_per_filter = {}
        for fv in filter_values:
            sub = df if filter_field is None else df.filter(pl.col(filter_field) == fv)
            if has_group:
                ranked = (
                    sub.group_by(group_field)
                    .agg(pl.col(metric_col).sum().alias("__rank__"))
                    .sort("__rank__", descending=True)
                    .head(n)[group_field]
                    .to_list()
                )
            else:
                ranked = ["__series__"]
            default_groups_per_filter[
                str(fv) if fv is not None else "__no_filter__"
            ] = ranked
        default_groups = default_groups_per_filter

    # Outcome-bucket data (for stacked / two-panel chart modes). Reads from a
    # separate parquet if `outcome_buckets.parquet` is given, otherwise reuses
    # the entry's main parquet. Returns None when the entry has no outcome
    # buckets configured (most datasets — workload counts, indexes, federal
    # filings — fall here).
    ob = entry.get("outcome_buckets")
    outcome_data_by_filter = None
    outcome_buckets_meta = None
    if ob:
        ob_parquet_rel = ob.get("parquet", parquet_rel)
        ob_x_field = ob.get("x_field", x_field)
        ob_filter_field = ob.get("filter_field", filter_field)
        ob_df = pl.read_parquet(PROJECT_ROOT / ob_parquet_rel).with_columns(
            pl.col(ob_x_field).cast(pl.Int32, strict=False)
        )
        if ob_filter_field is not None:
            ob_filter_values = sorted(
                {v for v in ob_df[ob_filter_field].unique().to_list() if v is not None}
            )
        else:
            ob_filter_values = []
        outcome_data_by_filter = build_outcome_data(
            entry, ob_df, ob_x_field, ob_filter_field, ob_filter_values or [None],
        )
        # Meta: bucket id → label (preserved for legends & tooltips).
        outcome_buckets_meta = {
            bid: (spec or {}).get("label", bid)
            for bid, spec in ob["buckets"].items()
        }

    return {
        "id": entry["id"],
        "name": entry["name"],
        "short_name": entry.get("short_name", entry["name"]),
        "category": entry["category"],
        "plot_type": PLOT_TYPE_BY_ENTRY_ID.get(entry["id"], "complaint_volume"),
        "jurisdiction": entry["jurisdiction"],
        "year_field_label": entry.get("year_field_label", "Year"),
        "y_axis_label": entry.get("y_axis_label", "Value"),
        "caveat_short": entry["caveat_short"],
        "provenance_url": entry["provenance_url"],
        "x_field": x_field,
        "group_field": group_field,
        "group_field_label": entry.get("group_field_label", "Series"),
        "filter_field": filter_field,
        "filter_field_label": entry.get("filter_field_label"),
        "filter_default": entry.get("filter_default"),
        "filter_values": [v for v in filter_values if v is not None] if filter_field else [],
        "metrics": metrics,
        "default_metric": entry["default_metric"],
        "default_groups": default_groups,
        "group_presets": entry.get("group_presets", []),
        "partial_year": entry.get("partial_year"),
        "partial_year_note": entry.get("partial_year_note"),
        "years": years,
        "data_by_filter": data_by_filter,
        "outcome_data_by_filter": outcome_data_by_filter,
        "outcome_buckets_meta": outcome_buckets_meta,
        "default_chart_mode": entry.get("default_chart_mode", "line"),
        "notes": entry.get("notes"),
        "national_rollup": bool(entry.get("national_rollup", False)),
        "national_rollup_label": entry.get("national_rollup_label", "National total"),
        "national_rollup_short_label": entry.get("national_rollup_short_label", "US total"),
        "national_rollup_per_state_label": entry.get("national_rollup_per_state_label", "Per-state"),
        "source_manifest": str(manifest_path.relative_to(PROJECT_ROOT)),
    }


def build_outcome_data(entry: dict, df: pl.DataFrame, x_field: str,
                       filter_field: str | None,
                       filter_values: list) -> dict | None:
    """For an entry with `outcome_buckets`, build a per-(filter, year, bucket)
    aggregate suitable for the stacked-bar / two-panel chart modes.

    Returns a dict keyed by filter value (or `__no_filter__`) holding:
      {"years": [...], "buckets": {bucket_id: [count_aligned_to_years]}}

    Bucket configs in the manifest use one of:
      {"column": "bad_faith"}                     # direct lookup
      {"derive": "total_complaints - upheld"}     # subtraction expression (one operator)
      null                                        # bucket not present in this dataset
    """
    ob = entry.get("outcome_buckets")
    if not ob:
        return None

    buckets_cfg = ob["buckets"]
    aggregation = ob.get("aggregation", {})
    filter_to_group = aggregation.get("filter_to_group")
    sum_across_groups = aggregation.get("sum_across_groups", False)

    group_field = entry.get("group_field")

    fvs = filter_values if filter_field is not None else [None]
    out: dict[str, dict] = {}

    for fv in fvs:
        sub = df if filter_field is None else df.filter(pl.col(filter_field) == fv)

        # Reduce to one row per year.
        if filter_to_group is not None and group_field is not None:
            sub = sub.filter(pl.col(group_field) == filter_to_group)
        elif sum_across_groups and group_field is not None:
            # Sum every numeric column across groups, grouped by the x_field.
            numeric_cols = [
                c for c, t in sub.schema.items()
                if c != x_field and c != group_field
                and t in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                          pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
                          pl.Float32, pl.Float64)
            ]
            agg_exprs = [pl.col(c).sum().alias(c) for c in numeric_cols]
            sub = sub.group_by(x_field).agg(agg_exprs)
        # else: assume sub is already one row per year (no group dim).

        years = sorted({int(y) for y in sub[x_field].unique() if y is not None})
        # Map year → row.
        row_by_year: dict[int, dict] = {}
        for r in sub.iter_rows(named=True):
            yr = r.get(x_field)
            if yr is None:
                continue
            row_by_year[int(yr)] = r

        bucket_data: dict[str, list] = {}
        for bucket_id, spec in buckets_cfg.items():
            if spec is None:
                bucket_data[bucket_id] = [None] * len(years)
                continue
            col = spec.get("column")
            derive = spec.get("derive")
            vals: list = []
            for y in years:
                row = row_by_year.get(y)
                if row is None:
                    vals.append(None)
                    continue
                if col is not None:
                    v = row.get(col)
                    vals.append(_to_jsonable(v))
                elif derive is not None:
                    # Single subtraction: "a - b". Keep parsing minimal — fail
                    # loudly if the manifest writes anything more complex.
                    if " - " not in derive:
                        raise ValueError(
                            f"Bucket {bucket_id} derive='{derive}' must be 'a - b'"
                        )
                    a_col, b_col = [s.strip() for s in derive.split(" - ", 1)]
                    a = row.get(a_col)
                    b = row.get(b_col)
                    if a is None or b is None:
                        vals.append(None)
                    else:
                        vals.append(_to_jsonable(int(a) - int(b)))
                else:
                    vals.append(None)
            bucket_data[bucket_id] = vals

        key = "__no_filter__" if fv is None else str(fv)
        out[key] = {"years": years, "buckets": bucket_data}

    return out


def _to_jsonable(v):
    if v is None:
        return None
    # Polars sometimes returns numpy scalar types; coerce.
    if isinstance(v, (int, float, bool, str)):
        return v
    try:
        return float(v) if "." in str(v) or "e" in str(v).lower() else int(v)
    except Exception:
        return str(v)


def build_state_index(entries: list[dict]) -> dict:
    """Build a map `{state_code: [plot_spec, ...]}` driving the per-state pages.

    Each plot_spec is either a native entry reference, or a sliced reference to
    a multi-state entry (FJC IDB / NAIC IDRR) that filters one state's series.

    Plot specs are ordered: outcomes → volume → lawsuits, with native entries
    before sliced multi-state ones inside each bucket.
    """
    PLOT_TYPE_ORDER = {
        "complaints_with_outcomes": 0,
        "complaint_volume": 1,
        "lawsuit_volume": 2,
    }

    states: dict[str, list[dict]] = {}

    # Collect native (single-state) entries.
    for e in entries:
        if e["id"] in MULTI_STATE_ENTRY_IDS:
            continue
        for st in e["jurisdiction"]:
            if st == "US":
                continue
            states.setdefault(st, []).append({
                "entry_id": e["id"],
                "plot_type": e["plot_type"],
                "slice_group": None,
                "is_native": True,
            })

    # For each multi-state entry, find the union of state codes appearing in
    # its data and add a sliced reference to each.
    for e in entries:
        if e["id"] not in MULTI_STATE_ENTRY_IDS:
            continue
        # Gather every group value across every filter slice.
        codes: set[str] = set()
        for slice_data in e["data_by_filter"].values():
            for g in slice_data["groups"]:
                if isinstance(g, str) and len(g) == 2 and g.isalpha():
                    codes.add(g)
        for st in codes:
            states.setdefault(st, []).append({
                "entry_id": e["id"],
                "plot_type": e["plot_type"],
                "slice_group": st,
                "is_native": False,
            })

    # Sort each state's plot list by (plot_type_order, native_first, entry_id).
    for st, specs in states.items():
        specs.sort(key=lambda s: (
            PLOT_TYPE_ORDER.get(s["plot_type"], 99),
            0 if s["is_native"] else 1,
            s["entry_id"],
        ))

    return states


def build_nationwide_index(entries: list[dict]) -> list[dict]:
    """The Nationwide page shows multi-state entries in their full national
    form (no slice). Native entries don't appear there."""
    out = []
    for e in entries:
        if e["id"] in MULTI_STATE_ENTRY_IDS:
            out.append({
                "entry_id": e["id"],
                "plot_type": e["plot_type"],
                "slice_group": None,
                "is_native": False,
            })
    out.sort(key=lambda s: ({"complaint_volume": 1, "lawsuit_volume": 2}.get(s["plot_type"], 9),
                            s["entry_id"]))
    return out


def build_payload() -> dict:
    manifest_paths = collect_manifests()
    entries: list[dict] = []
    for mp in manifest_paths:
        manifest = json.loads(mp.read_text())
        for entry in manifest.get("entries", []):
            print(f"  {mp.relative_to(PROJECT_ROOT)} :: {entry['id']}")
            payload = build_entry_payload(mp, entry)
            entries.append(payload)
    state_index = build_state_index(entries)
    nationwide_index = build_nationwide_index(entries)
    return {
        "schema_version": 1,
        "build_info": {
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n_entries": len(entries),
            "n_states": len(state_index),
        },
        "entries": entries,
        "state_index": state_index,
        "nationwide_index": nationwide_index,
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Insurance Complaint Rates — Data Viewer</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js" charset="utf-8"></script>
<style>
  :root {
    --fg: #222;
    --muted: #666;
    --border: #ddd;
    --bg: #fafafa;
    --panel-bg: #fff;
    --accent: #1f4e79;
    --plaintiff-bg: #fff8e1;
    --plaintiff-border: #f0b800;
    --regulator-bg: #eaf3ea;
    --regulator-border: #6aa86a;
    --index-bg: #f4f0e6;
    --index-border: #b39c5a;
    --federal-bg: #eaf0fb;
    --federal-border: #5a82c2;
  }
  html, body {
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    color: var(--fg);
    background: #fff;
    font-size: 14px;
  }
  .layout {
    display: grid;
    grid-template-columns: 280px 1fr;
    min-height: 100vh;
  }
  aside.sidebar {
    background: var(--bg);
    border-right: 1px solid var(--border);
    padding: 14px 14px 24px;
    overflow-y: auto;
  }
  aside.sidebar h2 {
    font-size: 11px; text-transform: uppercase; color: var(--muted);
    margin: 14px 0 6px; letter-spacing: 0.05em;
  }
  aside.sidebar h2:first-child { margin-top: 0; }
  .picker-group { margin-bottom: 8px; }
  .picker-group .group-label {
    font-size: 11px; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.05em;
    padding: 4px 6px;
  }
  .picker-item {
    display: block; width: 100%;
    padding: 6px 8px; margin: 1px 0;
    border: 0; background: transparent; text-align: left; cursor: pointer;
    font-size: 13px; border-radius: 4px;
    color: var(--fg);
  }
  .picker-item:hover { background: #eef; }
  .picker-item.active { background: var(--accent); color: white; font-weight: 600; }
  .picker-item .warn { color: #b07000; font-weight: 700; margin-right: 4px; }
  .picker-item.active .warn { color: #ffd54f; }
  main.main {
    padding: 16px 24px 32px;
    max-width: 1100px;
  }
  header.title {
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px; margin-bottom: 14px;
  }
  header.title h1 { font-size: 18px; margin: 0 0 4px; }
  header.title .sub { color: var(--muted); font-size: 12px; }
  .caveat {
    border: 1px solid var(--border);
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 14px;
    font-size: 13px;
    line-height: 1.45;
  }
  .caveat.plaintiff_allegation { background: var(--plaintiff-bg); border-color: var(--plaintiff-border); border-left-width: 4px; }
  .caveat.regulator_finding { background: var(--regulator-bg); border-color: var(--regulator-border); border-left-width: 4px; }
  .caveat.regulator_complaint_index { background: var(--index-bg); border-color: var(--index-border); border-left-width: 4px; }
  .caveat.federal_lawsuit { background: var(--federal-bg); border-color: var(--federal-border); border-left-width: 4px; }
  .caveat-tag {
    display: inline-block;
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; padding: 2px 6px; border-radius: 3px;
    margin-right: 8px; vertical-align: middle;
    background: rgba(0,0,0,0.08);
  }
  .meta {
    color: var(--muted); font-size: 12px; margin-bottom: 12px;
  }
  .controls {
    display: grid; grid-template-columns: 1fr; gap: 8px;
    background: var(--panel-bg); padding: 10px 12px;
    border: 1px solid var(--border); border-radius: 6px; margin-bottom: 14px;
  }
  .row { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; }
  /* Stacked variant: group-label on top, each option on its own line. */
  .row.stack { flex-direction: column; align-items: flex-start; gap: 2px; }
  .row.stack .group-label { min-width: 0; padding: 0; margin-bottom: 2px; }
  .row.stack label { padding-left: 4px; }
  .row .group-label {
    font-size: 11px; color: var(--muted); font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.05em;
    min-width: 80px;
  }
  .row label { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; }
  select[multiple] {
    width: 100%; min-height: 96px; max-height: 160px;
    padding: 4px;
    border: 1px solid var(--border); border-radius: 4px;
    font-size: 12px;
  }
  .quick-presets button {
    margin-right: 6px; padding: 3px 8px;
    background: #fff; border: 1px solid var(--border); border-radius: 4px;
    cursor: pointer; font-size: 12px;
  }
  .quick-presets button:hover { background: #eef; }
  #plot { width: 100%; height: 600px; background: #fff; }
  /* state-page mode: vertically stacked plots, full width */
  #state-page { width: 100%; }
  #state-page.hidden, #plot.hidden { display: none; }
  #state-page .section-heading {
    font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em;
    color: var(--accent); font-weight: 700;
    margin: 18px 0 8px; padding-bottom: 4px;
    border-bottom: 2px solid var(--accent);
  }
  #state-page .section-heading:first-child { margin-top: 0; }
  #state-page .chart-heading {
    font-size: 15px; font-weight: 600; color: var(--fg);
    margin: 14px 0 4px;
  }
  #state-page .subchart-label {
    font-size: 12px; color: var(--muted); font-style: italic;
    margin: 12px 0 2px;
  }
  #state-page .state-plot { width: 100%; height: 420px; background: #fff; margin-bottom: 6px; }
  #state-page .state-plot.tall { height: 480px; }
  #state-page .state-plot.short { height: 320px; }
  #state-page .empty {
    color: var(--muted); padding: 20px; text-align: center; font-style: italic;
  }
  /* sidebar "By state" grid */
  .state-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    margin-top: 4px;
  }
  .state-grid .picker-item {
    text-align: center;
    padding: 6px 4px;
    font-weight: 600;
    letter-spacing: 0.04em;
  }
  .nationwide-btn { margin-bottom: 6px; font-weight: 700 !important; }
  footer {
    margin-top: 16px; padding-top: 10px; border-top: 1px solid var(--border);
    font-size: 12px; color: var(--muted); line-height: 1.55;
  }
  footer a { color: var(--accent); }
  footer code { font-size: 11px; }
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <h2>By plot type</h2>
    <div id="picker-types"></div>

    <h2>By state</h2>
    <div id="picker-states"></div>

    <h2 id="filters-heading">Data viewer controls</h2>
    <div id="filters"></div>

    <h2 id="display-heading">Display</h2>
    <div id="display-controls">
      <div class="row" style="margin-bottom:6px;">
        <label id="lbl-exclude-partial"><input type="checkbox" id="opt-exclude-partial" checked> Exclude partial year</label>
        <label id="lbl-point-labels" style="display:none;"><input type="checkbox" id="opt-point-labels" checked> Per-year rate labels</label>
      </div>
      <div class="row" id="row-yaxis" style="margin-bottom:6px;">
        <span class="group-label" style="min-width:50px;">Y-axis</span>
        <label><input type="radio" name="yaxis" value="linear" checked> Linear</label>
        <label><input type="radio" name="yaxis" value="log"> Log</label>
      </div>
      <div class="row stack" id="row-per-series" style="margin-bottom:6px;">
        <span class="group-label">Per-series</span>
        <label><input type="checkbox" id="ovl-avg"> Average</label>
        <label><input type="checkbox" id="ovl-ma3"> 3-yr MA</label>
        <label><input type="checkbox" id="ovl-ma5"> 5-yr MA</label>
      </div>
      <div class="row stack" id="row-cross-series">
        <span class="group-label">Cross-series</span>
        <label><input type="checkbox" id="ovl-mean"> Mean</label>
        <label><input type="checkbox" id="ovl-sum"> Sum</label>
        <label><input type="checkbox" id="ovl-median"> Median</label>
      </div>
    </div>
  </aside>

  <main class="main">
    <header class="title">
      <h1>Insurance Complaint Rates — Data Viewer</h1>
      <div class="sub">
        Multiple datasets from federal courts and state insurance regulators, presented with category-aware caveats.
        Built <span id="hdr-build">…</span>.
      </div>
    </header>
    <div id="caveat" class="caveat">…</div>
    <div class="meta" id="meta">…</div>
    <div id="plot"></div>
    <div id="state-page" class="hidden"></div>
    <footer>
      <div id="footer-source">…</div>
      <div style="margin-top:6px;">
        Source code: <a href="../">project root</a>
        · standalone single-state FJC viz: <a href="../fjc_idb/viz/index.html">fjc_idb/viz/index.html</a>
        · per-dataset PROVENANCE links above.
      </div>
      <div style="margin-top:6px;">
        <strong>Caveat categories:</strong>
        <span style="background:var(--regulator-bg);border-left:3px solid var(--regulator-border);padding:1px 6px;">Regulator finding</span>
        <span style="background:var(--index-bg);border-left:3px solid var(--index-border);padding:1px 6px;">Regulator complaint index</span>
        <span style="background:var(--plaintiff-bg);border-left:3px solid var(--plaintiff-border);padding:1px 6px;">Plaintiff allegation</span>
        <span style="background:var(--federal-bg);border-left:3px solid var(--federal-border);padding:1px 6px;">Federal lawsuit</span>
      </div>
    </footer>
  </main>
</div>

<script>
const PAYLOAD = __PAYLOAD_JSON__;

// ----------------------- color cycle -----------------------
const PALETTE = [
  "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
  "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
  "#5254a3", "#8ca252", "#bd9e39", "#ad494a", "#a55194",
  "#6b6ecf", "#b5cf6b", "#e7ba52", "#d6616b", "#ce6dbd",
  "#9c9ede", "#cedb9c", "#e7cb94", "#e7969c", "#de9ed6",
];
function colorFor(entry, group) {
  // Deterministic per-(entry, group) using stable index in entry's group list.
  const fv = RENDER_OVERRIDE ? RENDER_OVERRIDE.filter_value : state.filter_value;
  const filterKey = fv === null ? "__no_filter__" : String(fv);
  const slice = entry.data_by_filter[filterKey] || entry.data_by_filter["__no_filter__"];
  const groups = slice ? slice.groups : [];
  const idx = groups.indexOf(group);
  return PALETTE[idx >= 0 ? idx % PALETTE.length : 0];
}

// ----------------------- math helpers -----------------------
function trailingMA(values, window) {
  const out = new Array(values.length).fill(null);
  for (let i = window - 1; i < values.length; i++) {
    let sum = 0, n = 0, ok = true;
    for (let k = 0; k < window; k++) {
      const v = values[i - k];
      if (v === null || v === undefined) { ok = false; break; }
      sum += v; n++;
    }
    if (ok && n === window) out[i] = sum / n;
  }
  return out;
}

function seriesMean(values) {
  let sum = 0, n = 0;
  for (const v of values) {
    if (v !== null && v !== undefined) { sum += v; n++; }
  }
  return n > 0 ? sum / n : null;
}

function median(arr) {
  const s = arr.filter(v => v !== null && v !== undefined).slice().sort((a, b) => a - b);
  if (!s.length) return null;
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : 0.5 * (s[mid - 1] + s[mid]);
}

function maybeExcludePartial(years, ...arrays) {
  // Drop the single row tagged as partial_year (anywhere in the series).
  // Trailing partial year is the common case (TX 2026, FL 2026), but MD MIA's
  // partial year is the first row (FY 2008), so we can't slice; we splice.
  const exclude = readOverlay("opt-exclude-partial");
  const entry = activeEntry();
  if (!exclude || entry.partial_year === null || entry.partial_year === undefined) {
    return [years, ...arrays];
  }
  const idx = years.indexOf(entry.partial_year);
  if (idx === -1) return [years, ...arrays];
  const drop = (a) => a.slice(0, idx).concat(a.slice(idx + 1));
  return [drop(years), ...arrays.map(drop)];
}

// ----------------------- state -----------------------
const state = {
  view_mode: "entry",      // "entry" (single chart) or "state" (per-state page)
  active_entry_id: PAYLOAD.entries[0].id,
  active_state_code: null, // string state code (or "Nationwide") in state mode
  // per-entry sub-state, keyed by entry id, persists when switching back
  per_entry: {},
  filter_value: null,
};

// Render-time override: lets state-page rendering temporarily swap in a
// different entry + sub-state for a single chart's traces/layout build,
// without disturbing the user's interactive state in entry mode. The
// `overlays` map (id → bool) lets state-page renders force overlay
// checkboxes off (or on) regardless of the actual DOM state.
let RENDER_OVERRIDE = null;  // {entry, sub, filter_value, overlays?} | null

function readOverlay(id) {
  if (RENDER_OVERRIDE && RENDER_OVERRIDE.overlays && id in RENDER_OVERRIDE.overlays) {
    return RENDER_OVERRIDE.overlays[id];
  }
  const el = document.getElementById(id);
  return el ? el.checked : false;
}

function activeEntry() {
  if (RENDER_OVERRIDE) return RENDER_OVERRIDE.entry;
  return PAYLOAD.entries.find(e => e.id === state.active_entry_id);
}

function entryState(entry_id) {
  if (RENDER_OVERRIDE && RENDER_OVERRIDE.entry.id === entry_id) {
    return RENDER_OVERRIDE.sub;
  }
  if (!state.per_entry[entry_id]) {
    const e = PAYLOAD.entries.find(x => x.id === entry_id);
    state.per_entry[entry_id] = {
      metric: e.default_metric,
      selected: null,         // resolved when entry is activated
      filter_value: null,
      // null until the user picks; activateEntry resolves the manifest default.
      chart_mode: null,
    };
  }
  return state.per_entry[entry_id];
}

// ----------------------- picker rendering -----------------------
const PLOT_TYPE_LABELS = {
  "complaints_with_outcomes": "Complaints with outcomes",
  "complaint_volume":         "Complaint volume",
  "lawsuit_volume":           "Lawsuit volume",
};
const PLOT_TYPE_ORDER = ["complaints_with_outcomes", "complaint_volume", "lawsuit_volume"];

function renderPicker() {
  // ── By plot type ─────────────────────────────────────────────────────
  const typesEl = document.getElementById("picker-types");
  typesEl.innerHTML = "";
  const byType = {};
  for (const e of PAYLOAD.entries) {
    if (!byType[e.plot_type]) byType[e.plot_type] = [];
    byType[e.plot_type].push(e);
  }
  for (const pt of PLOT_TYPE_ORDER) {
    const entries = byType[pt];
    if (!entries) continue;
    const grp = document.createElement("div");
    grp.className = "picker-group";
    const lbl = document.createElement("div");
    lbl.className = "group-label";
    lbl.textContent = PLOT_TYPE_LABELS[pt];
    grp.appendChild(lbl);
    for (const e of entries) {
      const btn = document.createElement("button");
      btn.className = "picker-item";
      btn.dataset.entryId = e.id;
      const warn = e.category === "plaintiff_allegation" ? "<span class='warn'>⚠</span>" : "";
      btn.innerHTML = warn + escapeHtml(e.short_name);
      btn.title = e.name;
      btn.addEventListener("click", () => {
        state.view_mode = "entry";
        state.active_entry_id = e.id;
        state.active_state_code = null;
        activateView();
      });
      grp.appendChild(btn);
    }
    typesEl.appendChild(grp);
  }

  // ── By state ─────────────────────────────────────────────────────────
  const statesEl = document.getElementById("picker-states");
  statesEl.innerHTML = "";

  // "Nationwide" pinned at the top, full-width.
  const nb = document.createElement("button");
  nb.className = "picker-item nationwide-btn";
  nb.dataset.stateCode = "Nationwide";
  nb.textContent = "Nationwide";
  nb.title = "Federal lawsuits + NAIC IDRR national totals";
  nb.addEventListener("click", () => {
    state.view_mode = "state";
    state.active_state_code = "Nationwide";
    activateView();
  });
  statesEl.appendChild(nb);

  // State grid — alphabetical 2-letter codes.
  const codes = Object.keys(PAYLOAD.state_index).sort();
  const grid = document.createElement("div");
  grid.className = "state-grid";
  for (const code of codes) {
    const btn = document.createElement("button");
    btn.className = "picker-item";
    btn.dataset.stateCode = code;
    btn.textContent = code;
    btn.title = `${code}: ${PAYLOAD.state_index[code].length} plot(s)`;
    btn.addEventListener("click", () => {
      state.view_mode = "state";
      state.active_state_code = code;
      activateView();
    });
    grid.appendChild(btn);
  }
  statesEl.appendChild(grid);
}

function syncPickerActive() {
  for (const btn of document.querySelectorAll(".picker-item")) {
    if (btn.dataset.entryId !== undefined) {
      btn.classList.toggle("active",
        state.view_mode === "entry" && btn.dataset.entryId === state.active_entry_id);
    } else if (btn.dataset.stateCode !== undefined) {
      btn.classList.toggle("active",
        state.view_mode === "state" && btn.dataset.stateCode === state.active_state_code);
    }
  }
}

// ----------------------- filters / metric / groups rendering -----------------------
function renderFilters() {
  const entry = activeEntry();
  const sub = entryState(entry.id);
  const filtersEl = document.getElementById("filters");
  filtersEl.innerHTML = "";

  // 1) Optional secondary filter (e.g. plan_type for NY health).
  if (entry.filter_field) {
    const wrap = document.createElement("div");
    wrap.className = "row";
    wrap.style.marginBottom = "8px";
    const lab = document.createElement("span");
    lab.className = "group-label";
    lab.textContent = entry.filter_field_label || entry.filter_field;
    wrap.appendChild(lab);
    for (const fv of entry.filter_values) {
      const id = `flt-${entry.id}-${fv.replace(/\W+/g,'_')}`;
      const lbl = document.createElement("label");
      const r = document.createElement("input");
      r.type = "radio";
      r.name = `flt-${entry.id}`;
      r.id = id;
      r.value = fv;
      r.checked = (sub.filter_value || entry.filter_default) === fv;
      r.addEventListener("change", () => {
        sub.filter_value = fv;
        state.filter_value = fv;
        // Reset selected groups when filter changes (different group set).
        sub.selected = null;
        renderGroupSelect();
        recompute();
      });
      lbl.appendChild(r);
      lbl.appendChild(document.createTextNode(" " + fv));
      wrap.appendChild(lbl);
    }
    filtersEl.appendChild(wrap);
    if (!sub.filter_value) sub.filter_value = entry.filter_default;
    state.filter_value = sub.filter_value;
  } else {
    state.filter_value = null;
  }

  // 2) Group multi-select (only if entry has a group_field).
  if (entry.group_field) {
    const wrap = document.createElement("div");
    wrap.style.marginBottom = "8px";
    const lab = document.createElement("div");
    lab.className = "group-label";
    lab.textContent = entry.group_field_label || "Series";
    lab.style.marginBottom = "4px";
    wrap.appendChild(lab);

    // National-rollup checkbox: overlay a single trace summing across all
    // jurisdictions, on top of whatever per-state series are selected.
    if (entry.national_rollup) {
      const modeRow = document.createElement("div");
      modeRow.style.marginBottom = "6px";
      const lbl = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.id = `natl-${entry.id}`;
      cb.checked = !!sub.show_national;
      cb.addEventListener("change", () => {
        sub.show_national = cb.checked;
        recompute();
      });
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(" " + (entry.national_rollup_label || "National total")));
      modeRow.appendChild(lbl);
      wrap.appendChild(modeRow);
    }

    // Quick presets row.
    if (entry.group_presets && entry.group_presets.length) {
      const presetsRow = document.createElement("div");
      presetsRow.className = "quick-presets";
      presetsRow.style.marginBottom = "4px";
      for (const preset of entry.group_presets) {
        const btn = document.createElement("button");
        btn.textContent = preset.label;
        btn.addEventListener("click", () => applyPreset(preset));
        presetsRow.appendChild(btn);
      }
      wrap.appendChild(presetsRow);
    }

    const sel = document.createElement("select");
    sel.id = "group-select";
    sel.multiple = true;
    sel.size = 8;
    wrap.appendChild(sel);

    filtersEl.appendChild(wrap);
    renderGroupSelect();
  }

  // 3) Metric selector.
  if (entry.metrics.length > 1) {
    const wrap = document.createElement("div");
    wrap.className = "row";
    wrap.id = "row-metric";
    wrap.style.marginTop = "6px";
    const lab = document.createElement("span");
    lab.className = "group-label";
    lab.textContent = "Metric";
    wrap.appendChild(lab);
    for (const m of entry.metrics) {
      const lbl = document.createElement("label");
      const r = document.createElement("input");
      r.type = "radio";
      r.name = `metric-${entry.id}`;
      r.value = m.id;
      r.checked = (sub.metric || entry.default_metric) === m.id;
      r.addEventListener("change", () => {
        sub.metric = m.id;
        recompute();
      });
      lbl.appendChild(r);
      lbl.appendChild(document.createTextNode(" " + m.label));
      wrap.appendChild(lbl);
    }
    filtersEl.appendChild(wrap);
  }
  if (!sub.metric) sub.metric = entry.default_metric;
}

function currentFilterKey() {
  const fv = RENDER_OVERRIDE ? RENDER_OVERRIDE.filter_value : state.filter_value;
  return fv === null ? "__no_filter__" : String(fv);
}

function availableGroups() {
  const entry = activeEntry();
  if (!entry.group_field) return [];
  return entry.data_by_filter[currentFilterKey()].groups;
}

function defaultSelectedGroups() {
  const entry = activeEntry();
  if (!entry.group_field) return [];
  let dg = entry.default_groups;
  // dg can be: an array (filter-independent) OR a dict keyed by filter value.
  if (dg && !Array.isArray(dg)) {
    dg = dg[currentFilterKey()] || [];
  }
  if (!dg) dg = [];
  // Intersect with available groups (in case manifest names a group that's
  // not in the current filter slice).
  const avail = new Set(availableGroups());
  return dg.filter(g => avail.has(g));
}

function renderGroupSelect() {
  const entry = activeEntry();
  const sub = entryState(entry.id);
  const sel = document.getElementById("group-select");
  if (!sel || !entry.group_field) return;
  sel.innerHTML = "";
  for (const g of availableGroups()) {
    const opt = document.createElement("option");
    opt.value = g;
    opt.textContent = g;
    sel.appendChild(opt);
  }
  if (!sub.selected) {
    sub.selected = defaultSelectedGroups();
  }
  for (const opt of sel.options) {
    opt.selected = sub.selected.includes(opt.value);
  }
  sel.onchange = () => {
    sub.selected = Array.from(sel.selectedOptions).map(o => o.value);
    recompute();
  };
}

function applyPreset(preset) {
  const entry = activeEntry();
  const sub = entryState(entry.id);
  const avail = availableGroups();
  let next;
  if (preset.all) {
    next = avail.slice();
  } else if (preset.groups) {
    const av = new Set(avail);
    next = preset.groups.filter(g => av.has(g));
  } else if (preset.exclude_groups) {
    const ex = new Set(preset.exclude_groups);
    next = avail.filter(g => !ex.has(g));
  } else if (preset.strategy === "top_n_by_metric") {
    next = topNByMetric(preset.metric, preset.n);
  } else {
    next = avail.slice();
  }
  sub.selected = next;
  // Reflect in the select element.
  const sel = document.getElementById("group-select");
  if (sel) {
    for (const opt of sel.options) opt.selected = next.includes(opt.value);
  }
  recompute();
}

function topNByMetric(metricCol, n) {
  const entry = activeEntry();
  const groups = availableGroups();
  const data = entry.data_by_filter[currentFilterKey()].metrics_data[metricCol] || {};
  const ranked = groups
    .map(g => [g, (data[g] || []).reduce((s, v) => s + (v || 0), 0)])
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(p => p[0]);
  return ranked;
}

// ----------------------- caveat / meta / footer -----------------------
function renderCaveat() {
  const entry = activeEntry();
  const cav = document.getElementById("caveat");
  cav.className = "caveat " + entry.category;
  const TAG_LABELS = {
    "regulator_finding": "Regulator finding",
    "regulator_complaint_index": "Regulator complaint index",
    "plaintiff_allegation": "Allegation",
    "federal_lawsuit": "Federal lawsuit",
  };
  const tag = TAG_LABELS[entry.category] || entry.category;
  cav.innerHTML = `<span class="caveat-tag">${tag}</span>${escapeHtml(entry.caveat_short)}`;
  document.getElementById("meta").innerHTML =
    `<strong>${escapeHtml(entry.name)}</strong> — ${entry.jurisdiction.join(", ")} · `
    + `years ${entry.years[0]}–${entry.years[entry.years.length - 1]}`
    + (entry.partial_year !== null && entry.partial_year !== undefined
        ? ` (${entry.partial_year} partial)` : "");
  const footer = document.getElementById("footer-source");
  footer.innerHTML =
    `Source manifest: <code>${escapeHtml(entry.source_manifest)}</code>`
    + ` · Provenance: <a href="../${escapeHtml(entry.provenance_url)}">${escapeHtml(entry.provenance_url)}</a>`
    + (entry.notes ? ` · ${escapeHtml(entry.notes)}` : "");
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/[&<>"']/g, c => (
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]
  ));
}

// ----------------------- chart -----------------------
function buildTraces() {
  const entry = activeEntry();
  const sub = entryState(entry.id);
  const filterKey = currentFilterKey();
  const slice = entry.data_by_filter[filterKey];
  const yearsAll = entry.years;
  const showAvg = readOverlay("ovl-avg");
  const showMA3 = readOverlay("ovl-ma3");
  const showMA5 = readOverlay("ovl-ma5");
  const showMean = readOverlay("ovl-mean");
  const showSum = readOverlay("ovl-sum");
  const showMedian = readOverlay("ovl-median");

  const metricCol = entry.metrics.find(m => m.id === sub.metric).column;
  const data = slice.metrics_data[metricCol] || {};

  let selected;
  if (entry.group_field) {
    selected = sub.selected || [];
  } else {
    selected = ["__series__"];
  }

  const traces = [];

  // National-rollup overlay: when checkbox is on, append a single trace
  // summing across ALL jurisdictions (regardless of multi-select). Drawn as
  // a thicker dark line so it reads distinctly against the colored per-state
  // traces. Trace is appended AFTER per-state, so it sits on top in the
  // legend and on the plot.
  const appendNational = entry.national_rollup && sub.show_national;

  for (const g of selected) {
    const color = entry.group_field ? colorFor(entry, g) : "#1f4e79";
    const counts = data[g] || [];
    const [yrs, vals] = maybeExcludePartial(yearsAll, counts);
    const label = entry.group_field ? g : entry.metrics.find(m => m.id === sub.metric).label;

    traces.push({
      x: yrs, y: vals,
      type: "scatter", mode: "lines+markers",
      name: label,
      legendgroup: g,
      line: { color, width: 2 },
      marker: { color, size: 5 },
      hovertemplate: `<b>${escapeHtml(label)}</b> %{x}<br>%{y}<extra></extra>`,
    });

    if (showAvg) {
      const m = seriesMean(vals);
      if (m !== null) {
        traces.push({
          x: [yrs[0], yrs[yrs.length - 1]],
          y: [m, m],
          type: "scatter", mode: "lines",
          legendgroup: g,
          showlegend: false,
          line: { color, width: 1, dash: "dash" },
          opacity: 0.35,
          hoverinfo: "skip",
        });
      }
    }
    if (showMA3) {
      traces.push({
        x: yrs, y: trailingMA(vals, 3),
        type: "scatter", mode: "lines",
        legendgroup: g,
        showlegend: false,
        line: { color, width: 1.5, dash: "dot" },
        opacity: 0.6,
        hovertemplate: `<b>${escapeHtml(label)} 3yr MA</b> %{x}<br>%{y:.2f}<extra></extra>`,
      });
    }
    if (showMA5) {
      traces.push({
        x: yrs, y: trailingMA(vals, 5),
        type: "scatter", mode: "lines",
        legendgroup: g,
        showlegend: false,
        line: { color, width: 1.5, dash: "dashdot" },
        opacity: 0.6,
        hovertemplate: `<b>${escapeHtml(label)} 5yr MA</b> %{x}<br>%{y:.2f}<extra></extra>`,
      });
    }
  }

  // National-rollup overlay (single trace, sum across ALL groups).
  if (appendNational) {
    const allGroups = slice.groups;
    const sumAll = new Array(yearsAll.length).fill(null);
    for (let i = 0; i < yearsAll.length; i++) {
      let s = 0, anyVal = false;
      for (const g of allGroups) {
        const v = (data[g] || [])[i];
        if (v !== null && v !== undefined) { s += v; anyVal = true; }
      }
      sumAll[i] = anyVal ? s : null;
    }
    const [yrs, vals] = maybeExcludePartial(yearsAll, sumAll);
    const shortName = entry.national_rollup_short_label || "US total";
    traces.push({
      x: yrs, y: vals,
      type: "scatter", mode: "lines+markers",
      name: shortName,
      line: { color: "#111", width: 3 },
      marker: { color: "#111", size: 6 },
      hovertemplate: `<b>${escapeHtml(shortName)}</b> (n=${allGroups.length}) %{x}<br>%{y}<extra></extra>`,
    });
  }

  // Cross-series overlays.
  if (selected.length > 1 && (showMean || showSum || showMedian)) {
    const fullArrays = selected.map(g => data[g] || []);
    const [yrs, ...arrays] = maybeExcludePartial(yearsAll, ...fullArrays);
    const meanVals = [], sumVals = [], medVals = [];
    for (let i = 0; i < yrs.length; i++) {
      const col = arrays.map(a => a[i]).filter(v => v !== null && v !== undefined);
      if (!col.length) {
        meanVals.push(null); sumVals.push(null); medVals.push(null);
      } else {
        const s = col.reduce((a, b) => a + b, 0);
        sumVals.push(s);
        meanVals.push(s / col.length);
        medVals.push(median(col));
      }
    }
    if (showMean) traces.push({
      x: yrs, y: meanVals, type: "scatter", mode: "lines",
      name: `Mean of selected (n=${selected.length})`,
      line: { color: "#444", width: 2.5, dash: "dash" },
      hovertemplate: `<b>Mean of selected</b> %{x}<br>%{y:.2f}<extra></extra>`,
    });
    if (showSum) traces.push({
      x: yrs, y: sumVals, type: "scatter", mode: "lines",
      name: `Sum of selected (n=${selected.length})`,
      line: { color: "#444", width: 2.5, dash: "dot" },
      hovertemplate: `<b>Sum of selected</b> %{x}<br>%{y}<extra></extra>`,
    });
    if (showMedian) traces.push({
      x: yrs, y: medVals, type: "scatter", mode: "lines",
      name: `Median of selected (n=${selected.length})`,
      line: { color: "#444", width: 2.5, dash: "dashdot" },
      hovertemplate: `<b>Median of selected</b> %{x}<br>%{y:.2f}<extra></extra>`,
    });
  }

  return traces;
}

function buildLayout() {
  const entry = activeEntry();
  const sub = entryState(entry.id);
  const yScale = document.querySelector("input[name='yaxis']:checked").value;
  const metricLabel = entry.metrics.find(m => m.id === sub.metric).label;
  return {
    margin: { l: 70, r: 20, t: 10, b: 50 },
    xaxis: { title: entry.year_field_label, tickformat: "d" },
    yaxis: {
      title: metricLabel,
      type: yScale,
      rangemode: yScale === "log" ? "normal" : "tozero",
    },
    legend: { orientation: "v", x: 1.01, y: 1, xanchor: "left", font: { size: 11 } },
    hovermode: "closest",
    plot_bgcolor: "#fff",
    paper_bgcolor: "#fff",
    showlegend: true,
  };
}

// ----------------------- outcome bucket rendering -----------------------
// Colors for the 4-bucket outcome taxonomy. Mirrors MD MIA's chart palette:
// red (against insurer), gold (mixed / partial), blue (for insurer), gray
// (no merits decision). Used by stacked-bar and two-panel chart modes.
const BUCKET_COLORS = {
  against_insurer: "#C44536",
  mixed:           "#D4A55E",
  for_insurer:     "#5B7BA0",
  no_decision:     "#B8B8C8",
};
const BUCKET_DEFAULT_LABELS = {
  against_insurer: "Against insurer (regulator finding)",
  mixed:           "Mixed / partial",
  for_insurer:     "For insurer",
  no_decision:     "No merits decision",
};
// Stack order: bottom → top. no_decision at the bottom (largest, neutral),
// for_insurer next, mixed, against_insurer on top so the red sits prominent.
const BUCKET_STACK_ORDER = ["no_decision", "for_insurer", "mixed", "against_insurer"];

function activeChartMode() {
  const entry = activeEntry();
  // Rendering is driven purely by plot_type now. Outcome entries always
  // render as two-panel; every other entry renders as a line chart. No user
  // toggle.
  if (entry.plot_type === "complaints_with_outcomes" && entry.outcome_data_by_filter) {
    return "two_panel";
  }
  return "line";
}

function activeOutcomeSlice() {
  const entry = activeEntry();
  if (!entry.outcome_data_by_filter) return null;
  const key = currentFilterKey();
  return entry.outcome_data_by_filter[key]
      || entry.outcome_data_by_filter["__no_filter__"]
      || null;
}

function maybeExcludePartialOutcome(slice) {
  // Drop the single partial-year row (anywhere — handles MD's leading 2008
  // and TX's trailing 2026 alike).
  const exclude = readOverlay("opt-exclude-partial");
  const entry = activeEntry();
  if (!exclude || entry.partial_year === null || entry.partial_year === undefined) {
    return slice;
  }
  const idx = slice.years.indexOf(entry.partial_year);
  if (idx === -1) return slice;
  const drop = (a) => a.slice(0, idx).concat(a.slice(idx + 1));
  const out = { years: drop(slice.years), buckets: {} };
  for (const [bid, vals] of Object.entries(slice.buckets)) {
    out.buckets[bid] = drop(vals);
  }
  return out;
}

function bucketHasAnyValue(vals) {
  for (const v of vals) {
    if (v !== null && v !== undefined && v !== 0) return true;
  }
  return false;
}

function buildBarTraces(opts) {
  // opts: { xaxis, yaxis, showLegend }
  const entry = activeEntry();
  const slice = maybeExcludePartialOutcome(activeOutcomeSlice());
  if (!slice) return [];
  const meta = entry.outcome_buckets_meta || {};
  const xaxis = (opts && opts.xaxis) || "x";
  const yaxis = (opts && opts.yaxis) || "y";
  const showLegend = !opts || opts.showLegend !== false;

  const traces = [];
  for (const bid of BUCKET_STACK_ORDER) {
    const vals = slice.buckets[bid];
    if (!vals) continue;
    if (!bucketHasAnyValue(vals)) continue;
    const label = meta[bid] || BUCKET_DEFAULT_LABELS[bid];
    traces.push({
      x: slice.years,
      y: vals.map(v => v === null ? 0 : v),
      type: "bar",
      name: label,
      legendgroup: "outcome_" + bid,
      marker: { color: BUCKET_COLORS[bid], line: { color: "white", width: 0.5 } },
      hovertemplate: `<b>${escapeHtml(label)}</b><br>${escapeHtml(entry.year_field_label)} %{x}<br>%{y}<extra></extra>`,
      xaxis, yaxis,
      showlegend: showLegend,
    });
  }

  // Bar-top total labels — separate scatter trace, transparent points, text only.
  const totals = slice.years.map((_, i) => {
    let s = 0, any = false;
    for (const bid of BUCKET_STACK_ORDER) {
      const v = (slice.buckets[bid] || [])[i];
      if (v !== null && v !== undefined) { s += v; any = true; }
    }
    return any ? s : null;
  });
  traces.push({
    x: slice.years,
    y: totals,
    mode: "text",
    text: totals.map(t => t === null ? "" : String(t)),
    textposition: "top center",
    textfont: { size: 10, color: "#222" },
    type: "scatter",
    hoverinfo: "skip",
    showlegend: false,
    xaxis, yaxis,
  });

  return traces;
}

function computeOnMerits(buckets, i) {
  // on_merits = against + mixed + for (excludes no_decision).
  let s = 0, any = false;
  for (const bid of ["against_insurer", "mixed", "for_insurer"]) {
    const v = (buckets[bid] || [])[i];
    if (v !== null && v !== undefined) { s += v; any = true; }
  }
  return any ? s : null;
}

function buildRateTraces(opts) {
  // opts: { xaxis, yaxis }
  const entry = activeEntry();
  const slice = maybeExcludePartialOutcome(activeOutcomeSlice());
  if (!slice) return [];
  const xaxis = (opts && opts.xaxis) || "x";
  const yaxis = (opts && opts.yaxis) || "y";

  const years = slice.years;
  const rates = [], againstCounts = [], onMeritsArr = [];
  for (let i = 0; i < years.length; i++) {
    const a = (slice.buckets.against_insurer || [])[i];
    const om = computeOnMerits(slice.buckets, i);
    againstCounts.push(a);
    onMeritsArr.push(om);
    if (a === null || a === undefined || om === null || om === 0) {
      rates.push(null);
    } else {
      rates.push(a / om);
    }
  }

  // Lifetime aggregate (computed from the full slice, not the partial-year-filtered one).
  const fullSlice = activeOutcomeSlice();
  let totA = 0, totOM = 0;
  for (let i = 0; i < fullSlice.years.length; i++) {
    const a = (fullSlice.buckets.against_insurer || [])[i];
    const om = computeOnMerits(fullSlice.buckets, i);
    if (a !== null && a !== undefined) totA += a;
    if (om !== null && om !== undefined) totOM += om;
  }
  const lifetimeRate = totOM > 0 ? totA / totOM : null;

  const traces = [];

  // Lifetime aggregate dashed line, drawn as a trace (so it shows up in legend
  // and toggles cleanly).
  if (lifetimeRate !== null && years.length > 0) {
    traces.push({
      x: [years[0], years[years.length - 1]],
      y: [lifetimeRate, lifetimeRate],
      type: "scatter", mode: "lines",
      name: `Lifetime: ${(lifetimeRate*100).toFixed(2)}% (${totA}/${totOM})`,
      line: { color: "#444", width: 1.4, dash: "dash" },
      hoverinfo: "skip",
      legendgroup: "outcome_rate",
      xaxis, yaxis,
    });
  }

  // Rate line + markers. Open marker for years where against_count == 0;
  // filled red marker otherwise.
  const markerColors = againstCounts.map(c => (c === 0 ? "white" : BUCKET_COLORS.against_insurer));
  const markerLineColors = againstCounts.map(_ => BUCKET_COLORS.against_insurer);
  traces.push({
    x: years,
    y: rates,
    type: "scatter",
    mode: "lines+markers",
    name: "Against / on-merits",
    line: { color: "#222", width: 1.6 },
    marker: {
      color: markerColors,
      size: 9,
      line: { color: markerLineColors, width: 1.5 },
    },
    hovertemplate: years.map((y, i) =>
      `<b>${y}</b><br>${againstCounts[i] || 0}/${onMeritsArr[i] || 0} = ${rates[i] === null ? '—' : (rates[i]*100).toFixed(2)+'%'}<extra></extra>`
    ),
    legendgroup: "outcome_rate",
    xaxis, yaxis,
  });

  return traces;
}

function rateAnnotations(yref) {
  // Per-year `7.5% (3/40)` label just above each marker. Toggleable via
  // #opt-point-labels (entry mode); state-page render forces it on.
  if (!readOverlay("opt-point-labels")) return [];
  const slice = maybeExcludePartialOutcome(activeOutcomeSlice());
  if (!slice) return [];
  const out = [];
  for (let i = 0; i < slice.years.length; i++) {
    const a = (slice.buckets.against_insurer || [])[i];
    const om = computeOnMerits(slice.buckets, i);
    if (a === null || a === undefined || om === null || om === 0) continue;
    const r = a / om;
    out.push({
      x: slice.years[i],
      y: r,
      text: `${(r*100).toFixed(1)}%<br>(${a}/${om})`,
      showarrow: false,
      yshift: 18,
      font: { size: 9, color: "#333" },
      xref: "x",
      yref: yref || "y",
      align: "center",
    });
  }
  return out;
}

function buildBarLayout() {
  const entry = activeEntry();
  return {
    margin: { l: 70, r: 20, t: 30, b: 50 },
    barmode: "stack",
    xaxis: { title: entry.year_field_label, tickformat: "d" },
    yaxis: { title: "Number of complaints" },
    legend: { orientation: "v", x: 1.01, y: 1, xanchor: "left", font: { size: 11 } },
    hovermode: "closest",
    plot_bgcolor: "#fff",
    paper_bgcolor: "#fff",
    showlegend: true,
  };
}

function buildTwoPanelLayout() {
  const entry = activeEntry();
  return {
    margin: { l: 70, r: 20, t: 30, b: 50 },
    barmode: "stack",
    grid: { rows: 2, columns: 1, pattern: "independent", roworder: "top to bottom" },
    xaxis:  { domain: [0, 1], title: "", tickformat: "d", anchor: "y" },
    yaxis:  { domain: [0.50, 1.00], title: "Number of complaints", anchor: "x" },
    xaxis2: { domain: [0, 1], title: entry.year_field_label, tickformat: "d", anchor: "y2", matches: "x" },
    yaxis2: { domain: [0, 0.40], title: "Against / on-merits", anchor: "x2", tickformat: ".0%", rangemode: "tozero" },
    annotations: rateAnnotations("y2"),
    legend: { orientation: "v", x: 1.01, y: 1, xanchor: "left", font: { size: 11 } },
    hovermode: "closest",
    plot_bgcolor: "#fff",
    paper_bgcolor: "#fff",
    showlegend: true,
  };
}

// ----------------------- chart mode dispatch -----------------------
function recompute() {
  const mode = activeChartMode();  // "two_panel" or "line"
  let traces, layout;
  const config = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] };

  if (mode === "two_panel") {
    traces = buildBarTraces({ xaxis: "x", yaxis: "y", showLegend: true })
       .concat(buildRateTraces({ xaxis: "x2", yaxis: "y2" }));
    layout = buildTwoPanelLayout();
  } else {
    traces = buildTraces();
    layout = buildLayout();
  }
  Plotly.react("plot", traces, layout, config);
}

// ----------------------- per-entry control visibility -----------------------
function syncChartModeToggle() {
  // Function name is historical — there's no longer a chart-mode toggle.
  // It now just hides/shows controls in the sidebar based on plot_type and
  // entry features.
  const entry = activeEntry();
  const mode = activeChartMode();  // "two_panel" or "line"
  // Per-year rate labels only apply to two-panel rate plots.
  const ptLbl = document.getElementById("lbl-point-labels");
  if (ptLbl) ptLbl.style.display = (mode === "two_panel") ? "" : "none";
  // Per-series / cross-series / metric / y-axis controls only apply to
  // line-chart entries.
  const inLineMode = (mode === "line");
  const ps = document.getElementById("row-per-series");
  const cs = document.getElementById("row-cross-series");
  // Per-series overlays are usable on any line chart (single or multi series).
  if (ps) ps.style.display = inLineMode ? "" : "none";
  // Cross-series stats only mean something with multiple series; hide for
  // entries that don't have a group_field at all.
  if (cs) cs.style.display = (inLineMode && !!entry.group_field) ? "" : "none";
  // Y-axis Linear/Log toggle only renders cleanly for line charts.
  const ya = document.getElementById("row-yaxis");
  if (ya) ya.style.display = inLineMode ? "" : "none";
  // Metric radio is read by buildTraces (line mode) only; bar/two_panel modes
  // pull values directly from outcome_buckets and ignore the metric. Hide it
  // there to avoid the no-op-toggle confusion (e.g., MD MIA in two-panel).
  const mr = document.getElementById("row-metric");
  if (mr) mr.style.display = inLineMode ? "" : "none";
  // Exclude-partial-year only does anything when the entry has a partial_year.
  const ep = document.getElementById("lbl-exclude-partial");
  if (ep) ep.style.display =
    (entry.partial_year !== null && entry.partial_year !== undefined) ? "" : "none";
}

// ----------------------- rate-only layout (state-page split) -----------------------
function buildRateOnlyLayout() {
  const entry = activeEntry();
  return {
    margin: { l: 70, r: 20, t: 30, b: 50 },
    xaxis: { title: entry.year_field_label, tickformat: "d" },
    yaxis: { title: "Against / on-merits", tickformat: ".0%", rangemode: "tozero" },
    annotations: rateAnnotations("y"),
    legend: { orientation: "v", x: 1.01, y: 1, xanchor: "left", font: { size: 11 } },
    hovermode: "closest",
    plot_bgcolor: "#fff",
    paper_bgcolor: "#fff",
    showlegend: true,
  };
}

// ----------------------- state-page rendering -----------------------
function ephemeralSubFor(entry, sliceGroup, isNationwide) {
  // Build a fresh sub-state for one chart on a state page. Doesn't leak into
  // state.per_entry — the user's interactive entry-mode state is preserved.
  const sub = {
    metric: entry.default_metric,
    selected: null,
    filter_value: entry.filter_default || null,
    chart_mode: entry.default_chart_mode || "line",
    show_national: false,
  };

  // Resolve default groups so we have something to render even before user
  // touches anything.
  if (entry.group_field) {
    let dg = entry.default_groups;
    if (dg && !Array.isArray(dg)) {
      const k = sub.filter_value === null ? "__no_filter__" : String(sub.filter_value);
      dg = dg[k] || [];
    }
    sub.selected = (dg || []).slice();
  } else {
    sub.selected = [];
  }

  if (sliceGroup) {
    // Multi-state entry sliced to one state code: show that state's series only.
    sub.selected = [sliceGroup];
    sub.show_national = false;
  } else if (isNationwide) {
    if (entry.id === "naic_idrr") {
      // National total line only — no per-state clutter.
      sub.selected = [];
      sub.show_national = true;
    } else if (entry.id === "fjc_idb") {
      // Show all 50+DC, no overlays. Busy but unambiguous.
      const allGroups = (entry.data_by_filter["__no_filter__"] || {}).groups || [];
      const TERRITORIES = new Set(["PR", "VI", "GU", "MP"]);
      sub.selected = allGroups.filter(g => !TERRITORIES.has(g));
    }
  }
  return sub;
}

function renderWithOverride(entry, sub, overlays, fn) {
  const filterValue = sub.filter_value === undefined ? null : sub.filter_value;
  RENDER_OVERRIDE = { entry, sub, filter_value: filterValue, overlays };
  try { return fn(); } finally { RENDER_OVERRIDE = null; }
}

// Default overlay flags for state-page renders: keep things uncluttered.
// Partial-year exclusion ON; per-series and cross-series overlays OFF;
// per-year rate labels ON for readability.
const STATE_PAGE_DEFAULT_OVERLAYS = {
  "opt-exclude-partial": true,
  "opt-point-labels":    true,
  "ovl-avg":   false,
  "ovl-ma3":   false,
  "ovl-ma5":   false,
  "ovl-mean":  false,
  "ovl-sum":   false,
  "ovl-median": false,
};

function statePageOverlays(entryId, isNationwide) {
  const o = Object.assign({}, STATE_PAGE_DEFAULT_OVERLAYS);
  if (isNationwide && entryId === "fjc_idb") {
    // Show a sum line over all 50+DC for the federal nationwide view.
    o["ovl-sum"] = true;
  }
  return o;
}

function renderLineChartInto(containerId, entry, sub, overlays) {
  renderWithOverride(entry, sub, overlays, () => {
    const traces = buildTraces();
    const layout = buildLayout();
    Plotly.newPlot(containerId, traces, layout,
      { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
  });
}

function renderOutcomeStackedInto(containerId, entry, sub, overlays) {
  renderWithOverride(entry, sub, overlays, () => {
    const traces = buildBarTraces();
    const layout = buildBarLayout();
    Plotly.newPlot(containerId, traces, layout,
      { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
  });
}

function renderOutcomeRateInto(containerId, entry, sub, overlays) {
  renderWithOverride(entry, sub, overlays, () => {
    const traces = buildRateTraces();
    const layout = buildRateOnlyLayout();
    Plotly.newPlot(containerId, traces, layout,
      { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
  });
}

const CAVEAT_TAG_LABELS = {
  "regulator_finding": "Regulator finding",
  "regulator_complaint_index": "Regulator complaint index",
  "plaintiff_allegation": "Allegation",
  "federal_lawsuit": "Federal lawsuit",
};

function renderStatePage(stateCode) {
  const root = document.getElementById("state-page");
  root.innerHTML = "";
  const specs = stateCode === "Nationwide"
    ? PAYLOAD.nationwide_index
    : (PAYLOAD.state_index[stateCode] || []);

  // Page title.
  const title = document.createElement("h2");
  title.className = "section-heading";
  title.style.fontSize = "16px";
  title.style.borderBottomWidth = "2px";
  title.textContent = stateCode === "Nationwide"
    ? "Nationwide — federal lawsuits & NAIC totals"
    : `${stateCode} — all available plots`;
  root.appendChild(title);

  if (!specs.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = `No data available for ${stateCode}.`;
    root.appendChild(empty);
    return;
  }

  const sections = [
    {key: "complaints_with_outcomes", label: "Complaints with outcomes"},
    {key: "complaint_volume",         label: "Complaint volume"},
    {key: "lawsuit_volume",           label: "Lawsuit volume"},
  ];

  let chartIdx = 0;
  const isNationwide = (stateCode === "Nationwide");
  for (const sect of sections) {
    const sectSpecs = specs.filter(s => s.plot_type === sect.key);
    if (!sectSpecs.length) continue;

    const h = document.createElement("h3");
    h.className = "section-heading";
    h.textContent = sect.label;
    root.appendChild(h);

    for (const spec of sectSpecs) {
      const entry = PAYLOAD.entries.find(e => e.id === spec.entry_id);
      if (!entry) continue;
      const sub = ephemeralSubFor(entry, spec.slice_group, isNationwide);

      // Per-chart heading.
      const hdr = document.createElement("div");
      hdr.className = "chart-heading";
      const sliceSuffix = spec.slice_group ? ` — ${spec.slice_group}` : "";
      hdr.textContent = entry.name + sliceSuffix;
      root.appendChild(hdr);

      // Per-chart caveat banner.
      const cav = document.createElement("div");
      cav.className = "caveat " + entry.category;
      const tag = CAVEAT_TAG_LABELS[entry.category] || entry.category;
      cav.innerHTML = `<span class="caveat-tag">${escapeHtml(tag)}</span>${escapeHtml(entry.caveat_short)}`;
      root.appendChild(cav);

      const overlays = statePageOverlays(entry.id, isNationwide);

      const isOutcome = !!entry.outcome_data_by_filter
                     && spec.plot_type === "complaints_with_outcomes";
      if (isOutcome) {
        // 1) stacked outcome counts
        const id1 = `sp-chart-${chartIdx++}`;
        const d1 = document.createElement("div");
        d1.className = "state-plot";
        d1.id = id1;
        root.appendChild(d1);
        renderOutcomeStackedInto(id1, entry, sub, overlays);

        // 2) against / on-merits rate line — own subtitle + own plot
        const sub2 = document.createElement("div");
        sub2.className = "subchart-label";
        sub2.textContent = "Against-insurer rate (against / on-merits)";
        root.appendChild(sub2);
        const id2 = `sp-chart-${chartIdx++}`;
        const d2 = document.createElement("div");
        d2.className = "state-plot short";
        d2.id = id2;
        root.appendChild(d2);
        renderOutcomeRateInto(id2, entry, sub, overlays);
      } else {
        const id = `sp-chart-${chartIdx++}`;
        const d = document.createElement("div");
        d.className = "state-plot";
        d.id = id;
        root.appendChild(d);
        renderLineChartInto(id, entry, sub, overlays);
      }
    }
  }
}

// ----------------------- view dispatch -----------------------
function applyEntryModeUI() {
  document.getElementById("plot").classList.remove("hidden");
  document.getElementById("state-page").classList.add("hidden");
  document.getElementById("state-page").innerHTML = "";
  document.getElementById("caveat").style.display = "";
  document.getElementById("meta").style.display = "";
  // Sidebar control panels visible in entry mode.
  for (const id of ["filters-heading", "filters", "display-heading", "display-controls"]) {
    const el = document.getElementById(id);
    if (el) el.style.display = "";
  }
}

function applyStateModeUI() {
  document.getElementById("plot").classList.add("hidden");
  document.getElementById("state-page").classList.remove("hidden");
  document.getElementById("caveat").style.display = "none";
  document.getElementById("meta").style.display = "none";
  // Hide entry-mode-only sidebar panels in state mode (state pages render
  // with sensible defaults; per-chart filters would be confusing).
  for (const id of ["filters-heading", "filters", "display-heading", "display-controls"]) {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  }
  Plotly.purge("plot");
}

function activateView() {
  syncPickerActive();
  if (state.view_mode === "state") {
    applyStateModeUI();
    renderStatePage(state.active_state_code);
  } else {
    applyEntryModeUI();
    renderCaveat();
    renderFilters();
    syncChartModeToggle();
    Plotly.purge("plot");
    recompute();
  }
}

// Back-compat alias for any straggler caller.
function activateEntry() { state.view_mode = "entry"; activateView(); }

// ----------------------- init -----------------------
function onGlobalToggle() {
  // Re-render either the entry-mode chart or the entire state page in
  // response to a sidebar control toggle.
  if (state.view_mode === "state") {
    renderStatePage(state.active_state_code);
  } else {
    recompute();
  }
}

function init() {
  document.getElementById("hdr-build").textContent = PAYLOAD.build_info.built_at;
  renderPicker();
  for (const id of [
    "opt-exclude-partial", "ovl-avg", "ovl-ma3", "ovl-ma5",
    "ovl-mean", "ovl-sum", "ovl-median", "opt-point-labels",
  ]) {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", onGlobalToggle);
  }
  for (const r of document.querySelectorAll("input[name='yaxis']")) {
    r.addEventListener("change", onGlobalToggle);
  }
  activateView();
}

document.addEventListener("DOMContentLoaded", init);
</script>
</body>
</html>
"""


def main() -> int:
    print("Discovering manifests…")
    payload = build_payload()
    payload_json = json.dumps(payload, separators=(",", ":"), default=str)
    html = HTML_TEMPLATE.replace("__PAYLOAD_JSON__", payload_json)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html)
    size_kb = OUT_HTML.stat().st_size / 1024
    print(f"\nWrote {OUT_HTML}  ({size_kb:.1f} KB)")
    print(f"  {payload['build_info']['n_entries']} entries:")
    for e in payload["entries"]:
        nfilters = len(e["filter_values"])
        ngroups_total = sum(
            len(d["groups"]) for d in e["data_by_filter"].values()
        )
        print(
            f"    {e['id']:24}  plot_type={e['plot_type']:24}  "
            f"category={e['category']:22}  "
            f"years={e['years'][0]}-{e['years'][-1]}  "
            f"groups={ngroups_total}  filters={nfilters or '-'}"
        )
    print(f"\n  State index: {payload['build_info']['n_states']} states")
    for st in sorted(payload["state_index"].keys()):
        specs = payload["state_index"][st]
        ids = ", ".join(
            (s["entry_id"] + ("(sliced)" if s["slice_group"] else ""))
            for s in specs
        )
        print(f"    {st}: {ids}")
    print(f"  Nationwide: {[s['entry_id'] for s in payload['nationwide_index']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

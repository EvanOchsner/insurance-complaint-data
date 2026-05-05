# Methodology — Oregon DFR Complaint Statistics

## DFR's complaint metrics

Each year's per-line PDF reports four columns per company:

1. **Premium** — Direct written premium in Oregon for that line, that year.
2. **Total Complaints** — Total complaints filed against the company that year.
3. **Confirmed Complaints** — Complaints where DFR's investigation found that the insurer violated insurance code, contract terms, or industry standards. This is the **regulator's merits decision** — approximately equivalent to TX's `Confirmed`, MD's "in favor of insured", and CT's "against insurer" outcome buckets.
4. **Complaint Index** — A normalized ratio similar to NAIC's share-of-share, but weighted by the **confirmed** count rather than total. A company with index 1.0 has confirmed complaints in proportion to its premium share. > 1.0 indicates more confirmed complaints than expected; 0 means no confirmed complaints (regardless of how many were filed).

## Why "Confirmed" matters

This is the key dimension that's missing from MI, OH, LA, IN, KS, ID, IL, WI, CO, MO's `mo_dci` (which has a soft outcome rate but not counts), and the rest of the per-company-index peer set. With OR's data you can:

- Compute confirmation rate = confirmed / total per (company, line, year).
- Distinguish carriers that get many filings but few sustained findings (high-volume, low-confirmation) from carriers with smaller filing counts but higher findings rates (low-volume, high-confirmation).
- Map directly to the canonical cross-state outcome taxonomy without estimation.

OR's complaint index is itself outcome-weighted, but the raw `total_complaints` and `confirmed_complaints` columns are preserved separately so downstream code can compute alternative metrics (e.g., Texas-style confirmation rate, MO-style consumer-relief proxy, or pure workload counts).

## Lines of business

Six lines, consistent across all 7 years:

1. **Auto** (`auto`)
2. **Annuities** (`annuities`)
3. **Health** (`health`)
4. **Homeowners** (`homeowners`)
5. **Life** (`life`)
6. **Long Term Care** (`long_term_care`)

These are all personal lines. DFR does regulate commercial lines and workers' comp (the latter via the WC Division), but they're not in this annual report series.

## Comparison with peer states

| State | Lines | Years | Per-company? | Outcome dim? |
|---|---|---|---|---|
| **OR (this)** | **6** | **7 (2019-2025)** | ✓ | **✓ Confirmed Complaints** |
| LA | 4 (personal only) | 10 (2015-2024) | ✓ | ✗ |
| MI | 5 | 3 (2022-2024) | ✓ | ✗ |
| OH (PRR) | 6 | 4 (2021-2024) | ✓ (top 50 only) | ✗ |
| MO | 7 | 3 reports × 5 yrs (2017-2023) | ✓ (3-yr pooled) | ✓ (% relief) |
| IN | 5 | 16 (2009-2024) | ✓ | ✗ |
| KS | many | 5 (2020-2024) | ✓ (top 20 only) | ✗ |
| ID | 4 | 3 (2018-2020) | ✓ | ✗ |
| IL | 5 | 5 (2018-2024 minus 21/22) | ✓ | ✗ |
| WI | 11 sub-lines | 6 (2019-2024) | ✗ (line aggregates only) | ✗ |
| CO | 4 | 4 (FY 22-25) | ✗ | ✓ ($ recovered) |

**Among Phase 5 states recon'd so far, OR is the strongest.** It has the outcome dimension (which LA does not), and its history covers 7 years (vs LA's 10 but without confirmed data, MI's 3, OH's 4).

## Comparison with NAIC IDRR

OR's IDRR mean (~3,879 complaints/year) is the all-source workload count. Summing OR's per-line published totals for 2024 gives:
- auto 1,456 + annuities 30 + health 574 + homeowners 797 + life 140 + LTC 39 = **3,036 total complaints in published lines**.

The gap to IDRR (~3,879) is informal contacts and complaints in lines not exposed in the public per-line reports (e.g., commercial lines, workers' comp, large-group health, title, etc.).

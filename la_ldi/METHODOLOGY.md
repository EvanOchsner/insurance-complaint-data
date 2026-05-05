# Methodology — Louisiana LDI Complaint Index

## LDI's complaint index, defined

The Louisiana Department of Insurance (LDI) computes a per-company per-line **complaint index** as:

```
                  (Company complaints / Sum of all complaints, that line, that year)
Complaint Index = ────────────────────────────────────────────────────────────────────
                  (Company premium / Sum of all premiums, that line, that year)
```

This is the standard NAIC share-of-share index, expressed as a ratio (not multiplied by 100). LDI's posted definition: *"A company with a complaint index of 1 has an average number of complaints. A company with a complaint index higher than 1 has more complaints than average."*

**Important interpretation difference from MO/IN/KS:** LDI reports the index as a raw ratio centered at 1.0, while MO/IN/KS scale by 100 (industry average = 100). To convert LDI to the MO scale, multiply by 100.

## Lines of business

The form's coverage-type dropdown exposes 4 lines:

| Slug | LDI label | Coverage code |
|---|---|---|
| `auto` | Auto - Individual Private Passenger | 1 |
| `homeowners` | Homeowners | 47 |
| `life` | Life & Annuity - Individual Life | 70 |
| `accident_health` | Accident & Health - Individual | 119 |

The page's prose mentions "Life Company Sort" as a 5th option, but it does not appear in the actual `<select>` element. Either deprecated or accessible via a different route. Flagged in [`PLAN.md`](PLAN.md).

## Years available

10 years (2015–2024) at the time of the initial build (2026-05-05). LDI publishes a new year approximately mid-year (after collecting prior-year premium data from insurers).

## Inclusion rule

Per LDI's posted policy: *"Only companies that wrote premium in a given year are included."* The reports include companies regardless of premium magnitude — there is no `>$1M` floor like MI uses. Companies with $0 or negative reported premium (accounting reversals) appear at the bottom of the table with index 0 or extreme positive/negative values. Filter on `premium_written > 0` for stable index comparisons.

No index cap is applied — extreme values up to 5-digit indices appear when complaints are filed against a carrier with negligible premium volume.

## Reporting period

LDI describes the reports as "Period Ending: <YYYY>" — the index is computed over a single calendar year. Unlike MO (which pools 3 years for company indices), LDI's per-company index is genuinely per-year.

## What's NOT in the data

1. **No outcome / disposition** — LDI publishes filed-complaint counts, not merits-decision categorization. Outcome data would require a public-records request to LDI.
2. **No reason / nature-of-complaint breakdown** — the LDI tool does not expose a "complaint reason" axis. Other states (MO, MI, OH) do publish this.
3. **No NAIC code** — companies are listed by name only. Group rollup requires fuzzy matching.
4. **No commercial lines** — Commercial Auto, General Liability, Workers' Comp, Commercial Multi-Peril, etc. are absent. The 4 published lines are all personal lines.

## Comparison with peer states

| State | Lines | Years | Index methodology | Index scale | Outcome? |
|---|---|---|---|---|---|
| **LA (this)** | 4 (Auto, HO, Life, A&H) | 10 (2015-2024) | NAIC share-of-share | 1.0 = avg | No |
| MO | 7 | 3 reports × 5 years aggregate, 2017-2023 | NAIC share-of-share, **3-yr pooled per-company** | 100 = avg | Yes (% relief) |
| IN | 5 | 16 (2009-2024) | NAIC share-of-share | 100 = avg | No |
| KS | many | 5 (2020-2024) | NAIC share-of-share, top-20 only | 100 = avg | No |
| ID | 4 | 3 (2018-2020) | NAIC share-of-share | 100 = avg | No |
| IL | 5 | 5 (2018-2024 minus 21/22) | mixed (NAIC pre-2019; per-$1M EP / per-10k policies post) | varies | No |
| MI | 5 | 3 (2022-2024) | per-$1M premium | raw rate | No |
| OH (PRR pending) | 6 | 4 (2021-2024) | NAIC share-of-share | 1.0 = avg | No (workload only) |

**LA's strengths in this peer set:**
- Tied with IN for **deepest history** (10 vs 16 years) — but IN starts in 2009, LA's 10 years are continuous and span the post-Katrina recovery + Ida.
- Per-year (not pooled) per-company index — easier to use for trend analysis than MO's pooled view.
- Documented post-Ida (2021) homeowners surge with cleanly-identified failed-carrier signal.

**LA's weaknesses:**
- Only 4 lines, all personal — narrower than MO's 7 lines or KS's industry-spanning coverage.
- No outcome data, no reason breakdown.
- No NAIC code on the company name — manual mapping needed for cross-state rollup.

## Comparison with NAIC IDRR

LDI's per-line per-year aggregates can be summed to compare with IDRR's state-total-complaints. For 2022, IDRR shows LA = ~5,400 total received. LDI per-line totals for 2022: auto 859 + homeowners 2,508 + life 245 + A&H 286 = **3,898**. The gap (~1,500 complaints) is consistent with IDRR including informal contacts and complaints in lines not exposed in LDI's public dashboard (e.g., Health large-group, Commercial lines, Workers' Comp, Title, etc. that LDI does cover but doesn't publish through this online services tool).

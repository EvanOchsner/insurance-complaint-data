# Maryland Insurance Administration §27-1001 bad-faith data, FY 2008–FY 2025

This packet compiles 18 years of data from the Maryland Insurance Administration's
annual reports to the General Assembly under Md. Insurance Article §27-1001(h),
which requires the MIA to report on the disposition of first-party bad-faith
complaints against property/casualty insurers. The packet contains the original
MIA reports as PDFs, the extracted year-by-year figures as a CSV, a chart, and
the Python scripts used to build the dataset.

## What's in this packet

```
mia-bad-faith-data/
├── README.md          (this file)
├── chart.png          (rendered chart, 18 years of data with commissioner timeline)
├── chart.pdf          (vector version of the chart)
├── data.csv           (extracted year-by-year figures)
├── source-reports/    (18 original MIA reports as PDFs, one per fiscal year)
└── scripts/           (Python used to build the dataset and render the chart)
    ├── build.py
    └── plot.py
```

## The data, briefly

§27-1001 is Maryland's first-party bad-faith statute, enacted in 2007 and
effective October 1 of that year. It allows policyholders who believe their
insurer denied or underpaid a property/casualty claim in bad faith to file a
complaint with the MIA, which conducts an on-the-record administrative review.
A finding of "absence of good faith" entitles the insured to actual damages,
expenses including attorney's fees up to one-third of the actual damages, and
interest. The MIA's decisions are reviewable de novo in circuit court.

Section 27-1001(h) requires the Commissioner to file an annual report with the
General Assembly summarizing complaint volume, dispositions, and any regulatory
enforcement actions. Those annual reports are the primary source for everything
in this packet.

Across the full FY 2008–FY 2025 period:

- 711 complaints were filed under §27-1001
- 493 were reviewed and decided on the merits (the rest were withdrawn,
  settled prior to a merits decision, or dismissed for lack of jurisdiction)
- 28 found an absence of good faith — i.e., the insurer was found to have
  acted in bad faith
- The aggregate finding-for-insured rate is 28/493 = 5.68%

The bulk of those 28 findings (13 of them, 46%) occurred during a single
commissioner's tenure: Therese M. Goldsmith, June 2011 – January 2015. Excluding
her four fiscal years (FY 2012–2015) drops the rate from 5.68% to 15/431 = 3.48%.
The chart in this packet shows the full year-by-year breakdown along with the
commissioner timeline.

## Primary sources

Every figure in this packet derives from the MIA's own annual §27-1001(h) reports.
All 18 PDFs are in `source-reports/`. The MIA hosts them at the following URLs;
journalists can fetch them independently to verify nothing in this packet has
been altered:

| FY  | URL                                                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 2008| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2008goodfaithreport-271001cases-12-29-08.pdf                 |
| 2009| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2009goodfaithreport-271001cases-12-23-09.pdf                 |
| 2010| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2010-good-faith-report.pdf                                   |
| 2011| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/27-1001report2011.pdf                                        |
| 2012| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/271001report2012.pdf                                         |
| 2013| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/annual27-1001reportfy13.pdf                                  |
| 2014| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/27-1001annualreport2014.pdf                                  |
| 2015| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2015-Absence-of-Good-Faith-Cases-Report.pdf                  |
| 2016| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2016-Absence-Of-Good-Faith-Cases-Report-6587.pdf             |
| 2017| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/FY-2017-Report-on-Absence-of-Good-Faith-Cases-MSAR-6587.pdf  |
| 2018| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2018-Absence-of-Good-Faith-Cases-Filed-Under-27-1001-MSAR6587.pdf |
| 2019| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/MSAR6587-27-1001-2019-Annual-Report.pdf                      |
| 2020| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2020-Report-on-the-Absence-of-Good-Faith-Cases-MSAR-6587.pdf |
| 2021| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2021-Report-on-the-Absence-of-Good-Faith-Cases-MSAR-6587.pdf |
| 2022| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2022-Report-on-Absence-of-Good-Faith-Cases.pdf               |
| 2023| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2023-Report-on-Absence-of-Good-Faith-Cases-Filed-under-27-1001.pdf |
| 2024| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/2024-Report-on-Absence-of-Good-Faith-Cases.pdf               |
| 2025| https://insurance.maryland.gov/Consumer/Appeals%20and%20Grievances%20Reports/Absence-of-Good-Faith-Cases-Filed-2025-Report.pdf            |

The MIA's index of these reports lives at:
https://insurance.maryland.gov/Consumer/Pages/Property-and-Casualty-Reports.aspx

## Methodology and judgment calls

A few things worth disclosing up front, because a careful reader may spot
them and wonder whether something was massaged.

**Source selection across years.** Each fiscal year's figures are taken from
the most recent annual report that includes that year. The MIA generally
publishes a "Table 1" or "Table 2" with the prior 5–6 years' data alongside
the current year, and these retrospective tables sometimes update prior years'
figures as cases close on appeal or get reclassified. For example:

- FY 2011's original report (Dec 2011) showed 8 settled / 2 violations / 16
  no-violation. By the FY 2013 report it was retabulated as 7 / 1 / 18. The
  retrospective figure is used here, since it reflects post-appeals reality.
- FY 2008's original report shows 25 cases as "good faith or still pending" at
  the time of publication (Dec 2008). Later reports do not retrospectively
  re-tabulate FY 2008, so those 25 are recorded as "no violation" here. FY
  2008 also covers only 9 months (Oct 1, 2007 – Jun 30, 2008) since the
  statute had just taken effect.

**FY 2025 internal arithmetic.** The FY 2025 report's Table 1 lists 27
"Settled, Withdrawn, Rejected, or Dismissed" complaints and 30 "Total Reviewed"
on the merits — but a headline "Total" of 52, despite 27 + 30 summing to 57.
The same 5-case discrepancy appears in the prose breakdown (4 rejected for
incompleteness + 7 jurisdictional + 16 settled + 28 no-breach + 2 breach =
57). The on-merits decomposition (30 = 28 no-breach + 2 breach-and-bad-faith +
0 breach-pay-only) is internally consistent, so it is preserved verbatim. The
"settled" bucket is recorded here as 22, the figure that reconciles to the
report's headline total of 52. This is noted in the `source` column of `data.csv`.
The discrepancy does not affect the chart's lower panel (which depends only on
on-merits and bad-faith counts) and shifts the upper panel's settled segment
by 5 units in FY 2025.

**The "breach-of-obligation-to-pay-only" category.** Beginning with the FY 2022
report, the MIA's tables broke out a finding category for cases where the
insurer was found to have breached its duty to pay (the insured was right on
damages) but did NOT act in absence of good faith — so no fee-shifting under
§27-1001 applies. This category appeared in earlier reports' footnotes (e.g.,
FY 2012 fn. 3, FY 2013 fn. 2) but was not broken out as a separate row. There
is one such finding across all 18 years, in FY 2022. The chart's upper panel
includes it as a distinct segment. The lower panel's percentage is computed
strictly on bad-faith findings (§27-1001 violations), not on breach-pay-only,
since fee-shifting attaches only to the former.

**Goldsmith era boundaries.** The dashed aggregate lines in the chart's lower
panel partition the data into two windows: Goldsmith (FY 2012–2015) and
everything else (FY 2008–2011 plus FY 2016–2025). Goldsmith took office June
13, 2011 and resigned January 21, 2015 — neither boundary aligns with Maryland's
July 1 – June 30 fiscal year. The packet attributes a fiscal year to whichever
commissioner was in office at its midpoint (Jan 1 of the FY-end calendar year):
- FY 2011 midpoint (Jan 1, 2011): Sammis (acting); Goldsmith hadn't started yet
- FY 2012, 2013, 2014, 2015 midpoints: Goldsmith
- FY 2016 midpoint: Redmer

This is the simplest defensible cut at annual granularity. Using FY-end
attribution instead would put FY 2015 under Redmer, which would shift one
year's worth of cases (3 bad-faith findings of 15 on-merits) from the Goldsmith
aggregate to the "all others" aggregate, changing the rates to 10/47 = 21.28%
and 18/446 = 4.04% respectively. Either cut still shows Goldsmith as the
clear outlier.

**Commissioner attribution generally.** Tenures were verified against MIA
letterhead on each report's first page. Cross-referenced against Ballotpedia
and contemporaneous press coverage (Insurance Journal, Baltimore Sun, Daily
Record). The full timeline:

| Commissioner               | Tenure                       | Appointed by                |
| -------------------------- | ---------------------------- | --------------------------- |
| Ralph S. Tyler             | Apr 2007 – Jan 8, 2010       | O'Malley                    |
| Beth Sammis (acting)       | Jan 8, 2010 – Jun 13, 2011   | O'Malley                    |
| Therese M. Goldsmith       | Jun 13, 2011 – Jan 21, 2015  | O'Malley                    |
| Al Redmer, Jr.             | Jan 21, 2015 – May 18, 2020  | Hogan                       |
| Kathleen A. Birrane        | May 18, 2020 – Jun 30, 2024  | Hogan (continued under Moore) |
| Joy Hatchette (interim)    | Jul 1, 2024 – Sep 30, 2024   | Moore                       |
| Marie Grant                | Oct 1, 2024 – present        | Moore (Senate confirmed Apr 2, 2025) |

The Hatchette interim covered only 3 months of FY 2025 and is not separately
broken out in the chart since the underlying case data isn't split between her
and Grant.

## Reproducing the data

The CSV in `data.csv` was produced by `scripts/build.py` from the data points
extracted manually from each MIA report's table. The chart was rendered by
`scripts/plot.py` from that CSV. To reproduce:

```bash
pip install polars matplotlib
cd scripts
python3 build.py    # writes ../data.csv (run from packet root, or adjust paths)
python3 plot.py     # writes chart.png and chart.pdf
```

The scripts are short (under 250 lines combined) and contain comments noting
the source of each row.

## Using this packet

The CSV and chart are licensed under CC0 / public domain. The MIA's reports
themselves are public records of the State of Maryland. Republish, excerpt,
and verify freely. The contact who compiled this packet is happy to walk
through the methodology or any specific figure.

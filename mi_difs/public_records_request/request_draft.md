# MI DIFS Freedom of Information Act Request — DRAFT

> Copy-paste-ready. Review before submitting; verify the email address against
> <https://www.michigan.gov/difs/legal/foia> at submission time.
> See [`submission_guide.md`](submission_guide.md) for channel options and fee policy.

---

**To:** FOIA Coordinator, Michigan Department of Insurance and Financial Services
**Statute cited:** Michigan Freedom of Information Act, MCL 15.231 et seq.
**Subject:** Request for Insurance Complaint Disposition Data, Calendar Years 2010–Present

Dear FOIA Coordinator,

Pursuant to the Michigan Freedom of Information Act (MCL 15.231 et seq.), I am requesting copies of records from the Department of Insurance and Financial Services (DIFS) describing the **disposition** of consumer complaints filed against insurance companies. DIFS already publishes per-company complaint *counts* and ratios on its public website at <https://difs.state.mi.us/complaintstats>; this request seeks the disposition / closing-classification fields that are not on that public surface.

## Records requested

For each of the calendar years 2010 through the most recent year for which DIFS has finalized data, please provide:

1. **Per-company per-line per-disposition complaint counts.** A tabular dataset with one row per `(company, line of coverage, disposition category, year)` including:
   - Company name as filed and the DIFS internal company identifier (e.g., `0000631`);
   - NAIC company code, where DIFS records contain it;
   - Line of coverage using the same line-of-business taxonomy DIFS uses for its public per-line tables (Automobile, Homeowners, Life, Accident & Health, Annuity, plus any additional lines DIFS distinguishes internally — e.g., Fire/Allied/CMP, Liability — that are not broken out per-company on the public site);
   - Disposition / closing-classification category;
   - Count of complaints in that bucket.

2. **The disposition / closing-classification taxonomy** that DIFS uses internally — i.e., the list of distinct values your records system uses to classify how a complaint case closed (for example: "upheld," "not upheld," "withdrawn," "referred to another agency," "no jurisdiction," etc.), with brief descriptions of what each category means.

3. **A DIFS-internal-company-id ↔ NAIC code mapping table** for all companies that appear in the per-company complaint statistics for any year in the requested range. This is a single small table, separate from item 1.

I have no preference between calendar-year-of-receipt and calendar-year-of-closure, but please use whichever is the convention DIFS already follows in its public reports, and indicate which one was used.

## Format

I prefer machine-readable tabular formats — CSV, Excel `.xlsx`, or plain-text TSV — sent as e-mail attachments. If multiple files are needed, a ZIP archive is fine. Please do **not** convert the data to PDF.

## Public-interest fee waiver request

I am requesting these records for non-commercial public-interest research. The processed dataset will be published openly at <https://github.com/anthropics/...> (TODO: insert published URL once the repo is public) so that consumers, regulators, and other state insurance departments can study how complaint dispositions vary across insurers and lines of business. I respectfully request a fee waiver under DIFS's public-interest provisions. If a fee waiver is not granted, please provide a written cost estimate before processing the request — I am willing to pay reasonable copying / staff-time costs not to exceed **fifty U.S. dollars ($50.00)** without further written approval.

## Scope reductions

If any portion of this request is overly broad or burdensome, please contact me and I will narrow it. Specifically:

- If the full 2010–present range is impractical, I would accept the most recent five years (2020–present) as a first delivery.
- If per-disposition × per-company × per-line is too granular, I would accept per-disposition × per-line aggregates (no company breakout) as a first delivery, with a follow-up request for the per-company breakout.
- If the disposition taxonomy itself is exempt, the per-company per-line **counts** alone (matching the public site's columns but covering all companies regardless of premium volume, and including pre-2022 history) would still be valuable.

I am happy to discuss any of these reductions by email or phone.

## Contact information

- Name: Evan Ochsner
- E-mail: evan.ochsner@gmail.com
- Phone: (TODO — fill in if you want to provide one; not required by FOIA)
- Mailing address: (TODO — fill in only if requesting paper records)

I am not requesting any non-public, exempt, or confidential information; if any portion of the requested records is exempt under MCL 15.243, please redact and produce the non-exempt portions along with a written explanation of the basis for any redaction.

Thank you for your time.

Sincerely,
Evan Ochsner

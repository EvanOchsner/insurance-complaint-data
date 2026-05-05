# OH ODI Public Records Request — DRAFT

> Copy-paste-ready. Review before submitting; verify the submission channel
> against <https://insurance.ohio.gov/about-us/public-records-request> at submission time.
> See [`submission_guide.md`](submission_guide.md) for channel options.

---

**To:** Records Custodian, Ohio Department of Insurance
**Statute cited:** Ohio Public Records Act, Ohio Revised Code §149.43
**Subject:** Request for Per-Company Insurance Complaint and Disposition Data, Calendar Years 2010–Present

Dear Records Custodian,

Pursuant to Ohio's Public Records Act (Ohio Revised Code §149.43), I am requesting copies of records held by the Ohio Department of Insurance describing consumer complaints filed against insurance companies. ODI publishes a top-50-company complaint dashboard at <https://insurance.ohio.gov/about-us/complaint-center/complaint-ratios> via Power BI; this request seeks the underlying tabular data for **all** authorized companies (not only the top 50), broader historical coverage, and the **disposition / closing-classification** field that does not appear on the public dashboard.

## Records requested

For each of the calendar years 2010 through the most recent year for which ODI has finalized data, please provide:

1. **Per-company per-line complaint and premium data — full company list.** A tabular dataset with one row per `(company, line of business, year)` including:
   - Company name as filed and the NAIC company code (NAIC ID / cocode);
   - Line of business using the same taxonomy ODI's public dashboard uses (Homeowners, Individual Accident & Health, Individual Annuities, Life Individual, Long Term Care, Private Passenger Auto), plus any additional lines ODI separates internally;
   - Complaint count;
   - Direct written premium in Ohio for that line, that year;
   - Complaint ratio as ODI computes it for the public dashboard;
   - Market share for that line, that year.
   - **Important:** Please include all authorized companies for each line, not only the top 50 by market share that the public dashboard displays.

2. **Per-company per-line per-disposition complaint counts.** A second tabular dataset with one row per `(company, line, disposition category, year)` containing the count of complaints in each closing-classification bucket. This is the field that does not appear on the public dashboard.

3. **The disposition / closing-classification taxonomy** that ODI uses internally — i.e., the list of distinct values your records system uses to categorize how a complaint case closed (for example: "complaint upheld," "no violation found," "withdrawn," "referred," "no jurisdiction," etc.), with brief descriptions of what each category means.

4. **Complaint reasons.** ODI's public dashboard displays "Top Complaint Reasons" as a bar chart per line. Please include a per-company per-line per-reason cross-tab if ODI maintains one in machine-readable form, for the same year range. (Optional — only include if maintained natively; do not generate from scratch on my behalf.)

I have no preference between calendar-year-of-receipt and calendar-year-of-closure, but please use whichever convention ODI already follows in the dashboard, and indicate which one was used.

## Format

I prefer machine-readable tabular formats — CSV, Excel `.xlsx`, or plain-text TSV — sent as e-mail attachments. If multiple files are needed, a ZIP archive is fine. Please do **not** convert the data to PDF.

## Public-interest fee waiver request

I am requesting these records for non-commercial public-interest research. The processed dataset will be published openly so that consumers, regulators, and other state insurance departments can study how complaint outcomes vary across insurers and lines of business. Per ODI's posted records policy, the department does not charge for documents provided by e-mail and does not charge for a single request of 20 pages or fewer; this request is for tabular data delivered electronically, so I do not anticipate any per-page fees. If a fee will nonetheless be assessed, please provide a written cost estimate before processing — I am willing to pay reasonable costs not to exceed **fifty U.S. dollars ($50.00)** without further written approval.

## Scope reductions

If any portion of this request is overly broad or burdensome, please contact me and I will narrow it. Specifically:

- If the full 2010–present range is impractical, I would accept the most recent five years (2020–present) as a first delivery, with a follow-up for older history.
- If per-disposition × per-company × per-line is too granular, I would accept per-disposition × per-line aggregates (no company breakout) as a first delivery.
- The "complaint reasons" cross-tab (item 4) is the lowest priority — drop it first if it would slow the rest.

I am happy to discuss any of these reductions by email or phone.

## Contact information

- Name: Evan Ochsner
- E-mail: evan.ochsner@gmail.com
- Phone: (TODO — fill in if you want to provide one; ORC 149.43 does not require it)

Per ORC 149.43(B)(4), I understand I am not required to provide my identity, the intended use of these records, or to put this request in writing; I am providing all three voluntarily for clarity. If any portion of the requested records is exempt under ORC §149.43(A)(1) or otherwise, please redact and produce the non-exempt portions along with a written explanation of the basis for any redaction.

Thank you for your time.

Sincerely,
Evan Ochsner

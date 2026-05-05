# OH ODI — submission guide

Snapshot of ODI's public-records submission rules, taken from
<https://insurance.ohio.gov/about-us/public-records-request> on 2026-05-05. Verify before submitting.

## Statute

Ohio Public Records Act, **Ohio Revised Code §149.43**.

## Notable ORC features

- **No written request required.** A requester may make a verbal request and is not obligated to provide identity or stated use of the records. (We're providing all three voluntarily for clarity and to help the records officer process the request faster.)
- **No fixed response deadline.** The statute uses "promptly" for inspection and "reasonable time" for copies, where "reasonable" depends on volume, location, legal review, and redaction work.
- **No public-interest fee waiver clause** in the same form Michigan FOIA has, but ODI's posted policy waives copy fees for any single request of 20 pages or fewer and for documents provided by e-mail. Tabular data delivered as a CSV attachment should be free.

## Submission channels

ODI's records page directs requesters to a **"Launch Public Records Request Form"** electronic web form. There is no published direct e-mail for the records custodian, but the Communications office handles records inquiries. Three viable channels:

| Channel | Detail |
|---|---|
| **Web form (preferred)** | Click "Launch Public Records Request Form" on <https://insurance.ohio.gov/about-us/public-records-request>. Paste the body of `request_draft.md`. |
| **Phone** | 614-728-1384 (general / records inquiries). Useful for follow-up; less ideal for a multi-paragraph request. |
| **U.S. Mail** | Ohio Department of Insurance, 50 W. Town St. 3rd Floor, Suite 300, Columbus OH 43215, ATTN: Public Records Custodian / Communications Office. (Verify the suite number on ODI's contact page before mailing.) |

## Costs

- $0.10 per page for paper copies (waived for ≤ 20 pages).
- $2.00 per CD if delivered on disc.
- $2.00 per certification.
- $0 for documents delivered by e-mail.
- Postage at cost if delivered by mail.

The current request asks for electronic delivery of tabular data; should be free.

## Trade-secret considerations

Insurer-specific premium and complaint data could be claimed as trade secret by the carriers under ORC §1333.61(D), but the ODI dashboard already publishes per-company complaint counts, premiums, and ratios for the top 50 — establishing that this category of data is not a protectable trade secret. We expect any trade-secret challenges from carriers to be limited and procedurally handled by ODI per the policy posted on the records page.

## What to attach

Just the body of [`request_draft.md`](request_draft.md). No supporting documents needed.

If using the web form: paste the full body into the form's main text/comments field. The form likely has separate name/email fields — fill those from the contact-info section of the request body.

## After submitting

Append a row to [`sent_log.md`](sent_log.md) with the date, channel, and any tracking number / acknowledgment reference ODI provides.

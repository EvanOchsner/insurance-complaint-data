# Public records request template — FDFS CRN bulk export

The FDFS Civil Remedy database has no API and no bulk download button. To get a per-filing dataset (rather than just yearly counts) the practical path is a public records request under Florida's Chapter 119.

## How to send

Email or web form: <https://www.myfloridacfo.com/division/Records/> (the FDFS Public Records office). Include a clear, narrowly scoped request — they will send you a fee estimate first if it's large.

Florida public records law is consumer-friendly: government agencies cannot generally refuse public-records requests, and most non-PII fields in the CRN database are unambiguously public. FDFS has historically fulfilled CRN export requests.

## Suggested wording

> Subject: Public records request — Civil Remedy Notices (CRN) bulk export
>
> To FDFS Public Records Officer:
>
> Pursuant to Chapter 119 of the Florida Statutes, I respectfully request a bulk export of every Civil Remedy Notice (CRN) filed with the Department of Financial Services since the system became digital, in CSV or Excel format. I am happy to receive the data in whatever format your systems most easily produce.
>
> Specifically, I am requesting one row per CRN with at minimum these fields:
>
> - DFS file number
> - Submission date
> - Complainant type (Insured / Third Party / Other)
> - Insured name (or business name)
> - Insurer name
> - Type of insurance
> - Reason(s) for notice
> - Statute(s) cited
> - Insurer response date and disposition (if recorded)
>
> I do not need personally identifying information about individual complainants (names, addresses, emails, phone numbers, policy numbers, claim numbers). If your office's standard export format includes those fields, please redact them or substitute opaque hashes — whichever is easier for your staff. Business names are public and may remain.
>
> The intended use is statistical/longitudinal analysis of insurance bad-faith litigation pressure across U.S. states, as part of an unaffiliated independent research project. There is no commercial use planned.
>
> Please let me know if a fee estimate or further specification is required before fulfillment.
>
> Thank you,
> [name]
> [contact]

## Why this is worth doing even though we have a counts-only dataset

The yearly counts we collect via search-result headers tell us *how many* CRNs were filed per (year × line). They tell us nothing about:

- **Insurer-level distribution.** Who's named most? How does that change year-to-year?
- **Statute mix.** Are filings concentrated under § 624.155(1)(b)(1) (good-faith claim handling) or § 626.9541 (unfair trade practices)?
- **Reason mix.** Claim Denial vs Claim Delay vs Unsatisfactory Settlement Offer.
- **Disposition / cure.** What fraction of CRNs are "cured" by the insurer within 60 days?
- **Attorney concentration.** Does a small set of plaintiffs' firms file most of the volume?

A bulk PRR delivery unlocks all of these.

## Status

| Date | Action | Notes |
|---|---|---|
| _(none yet — waiting on user/operator to send)_ | | |

When a request is sent, append a row above with the date and any reference number FDFS issues.

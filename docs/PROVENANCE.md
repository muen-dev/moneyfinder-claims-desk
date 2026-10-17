# Provenance — factual claims on the landing page

Last checked: 2026-10-17. This file is the audit trail for numbers shown on the
marketing/landing surfaces. It is not tax advice.

## Claim table

| Claim on site | Current copy | Source | Status |
|---|---|---|---|
| Federal small-business health-care tax credit potential | **$15B+** potential credits, tax year 2011 | [Families USA & Small Business Majority (2012), via California Healthline](https://californiahealthline.org/morning-breakout/study-millions-of-small-businesses-not-claiming-reform-law-tax-credits/) | **Supported with wording caveat.** The source says the credit “could provide credits of more than $15 billion”; it is not an “unclaimed” total. |
| 89% missed / 11% claimed | **89%** estimated missed (derived); **11%** claimed (360k of 3.2M) | Same source: 3.2M eligible; 360,000 claimed per White House estimate | **Derived, not directly stated.** 360,000 / 3.2M = 11.25%; 88.75% did not claim. Labeled “estimated (derived)” on the page. |
| Long Island unclaimed funds | **$1.6B** on Long Island | [News 12: “more than 5 million people in Nassau and Suffolk counties are owed a combined $1.6 billion”](https://newyork.news12.com/you-could-have-unclaimed-cash-sitting-with-ny-state-heres-how-to-find-it) | **Supported.** These are personal unclaimed funds, not business credits; the page says so. |
| Ohio unclaimed funds | **~$5B** in Ohio | [Ohio House / Local 12 (2025): “The state currently holds nearly $5 billion in unclaimed funds”](https://ohiohouse.gov/members/dontavius-l-jarrells/in-the-news/ohio-allocates-17-billion-from-unclaimed-residents-funds-for-stadium-projects-5846) | **Supported as approximate.** Previous copy said “$4.8B”; changed to “~$5B” to match the source. |
| New Yorkers urged to check | **New Yorkers** urged to check | [News 12: State Comptroller’s Office encourages New Yorkers to check for unclaimed funds](https://newyork.news12.com/state-comptrollers-office-encourages-new-yorkers-to-check-for-unclaimed-funds) | **Supported.** Headline framing; personal funds, not business credits. |
| Demo application values | **$45,737 identified** (IT-636 $13,471; IT-212 $7,460; IT-643 $15,075; 8846 $9,731) | Synthetic fixture: `fixtures/applications.json`, `fixtures/onboarding.json` | **Synthetic, not a factual claim.** Labeled “synthetic demo” on the page. |
| Real government forms | “official IT-636 / IT-212 / IT-643 / 8846 AcroForms” | [NYS IT-636](https://www.tax.ny.gov/pdf/current_forms/it/it636_fill_in.pdf), [NYS IT-212](https://www.tax.ny.gov/pdf/current_forms/it/it212_fill_in.pdf), [NYS IT-643](https://www.tax.ny.gov/pdf/current_forms/it/it643_fill_in.pdf), [IRS 8846](https://www.irs.gov/pub/irs-pdf/f8846.pdf) | **Verified.** Blank PDFs are cached in `fixtures/forms/` and filled with pypdf. |
| IT-636 formula | **$0.14/gal** first 500,000 gallons | [NYS Tax: Alcoholic beverage production credit](https://www.tax.ny.gov/pit/credits/beer_prod_credit.htm) | **Supported.** 14 cents/gal for beer/cider first 500k; 4.5 cents/gal above; Article 18 distributor eligibility. |
| FICA tip credit rate | **7.65%** employer Social Security + Medicare on certain tips | [IRS Form 8846](https://www.irs.gov/forms-pubs/about-form-8846); employer FICA rate 6.2% + 1.45% | **Supported as standard rate.** Form 8846 claims the employer’s social security and Medicare taxes on certain tips. |
| Agent instrumentation | “1 agent span + 12 tool spans + 1 LLM span” | PRISM project `6e1051f7-8dce-498f-9846-d6acaa087737` | **Internal, verifiable** via PRISM traces; not a public statistic. |

## Wording rules

1. Don’t say “$15B was unclaimed.” Say “more than $15B in credits could have been claimed / was available.”
2. Don’t present 89% as a direct source figure. Say “estimated/derived” and show 360k of 3.2M.
3. Personal unclaimed-funds headlines must be labeled as personal, not business credits.
4. Mark synthetic demo amounts as synthetic everywhere.
5. Link the source next to the number, not only in this file.
6. The Ohio figure is approximate: “~$5B” / “nearly $5 billion,” not “$4.8B.”

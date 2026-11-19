# Fact check log

Every number, rate, deadline and law name in the reference files is checked here, with the source.
The skills still look up the current rule live before answering; this log is the starting point.
Re-check every January and after each federal or provincial budget.

## 2026-10-14

| Fact in the plugin | Result | Source |
|---|---|---|
| Sales tax rates for all 13 provinces and territories (incl. Nova Scotia HST 14% since Apr 1, 2025) | Correct | [Raymond Chabot Grant Thornton, sales tax rates 2026](https://www.rcgt.com/globalassets/1.-member-firms/raymond-chabot/media/202445/10/sales_tax_rates_2026.pdf), [TaxTips 2026 rates](https://www.taxtips.ca/salestaxes/sales-tax-rates-2026.htm) |
| Instalments: over $3,000 net tax owing ($1,800 Quebec) this year and either of the past two years | Correct. Added the due dates | [CRA: who has to pay instalments](https://www.canada.ca/en/revenue-agency/services/payments/payments-cra/individual-payments/income-tax-instalments/who-pays-instalments.html) |
| Self-employed: file by June 15, pay by April 30 | Correct | [CRA important dates](https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/important-dates-individuals.html) |
| T4A slips for contractors paid over $500 for services | Correct. Sources differ on exactly $500, so treat $500 as reportable | [Xero T4A guide](https://www.xero.com/ca/guides/t4a-slip/), [CRA trucking payments](https://canada.ca/trucking-payments) |
| Equipment write-offs (CCA) | **Updated.** Added the proposed Productivity Mega Deduction (announced Sept 15, 2026, not law yet) | [Osler](https://www.osler.com/en/insights/updates/canadian-prime-minister-announces-productivity-mega-deduction/), [PwC](https://www.pwc.com/ca/en/services/tax/publications/tax-insights/federal-tax-measures-boost-investments-canada-2026.html) |
| Ontario Consumer Protection Act, 2023 | **Updated.** Passed but not proclaimed in force; the 2002 Act still applies | [Gowling WLG](https://gowlingwlg.com/en-gb/insights-resources/articles/2023/ontario-s-new-consumer-protection-act), [Norton Rose Fulbright](https://www.nortonrosefulbright.com/en/knowledge/publications/cc6345e7/ontarios-new-consumer-protection-act-one-step-closer-to-becoming-law) |
| Alberta private-sector privacy law (PIPA) | **Updated.** Still in force; under review in 2026 | [Alberta PIPA engagement](https://www.alberta.ca/index%2Ephp/personal-information-protection-act-engagement), [Gowling WLG](https://gowlingwlg.com/en/insights-resources/articles/2025/alberta-overhauls-public-sector-information-law) |

Not re-checked this round (stable rules, but confirm in January): GST $30,000 small-supplier threshold,
meals at 50%, home-office rules, 6-year record keeping, limitation periods, employment-standards law names.

## 2026-11-16: the rates file

All numbers the calculator uses now live in `shared/rates/2026.json`, built by `dev/build_rates.py`.
Each section names its sources (CRA T4127 payroll formulas, 122nd edition; TaxTips.ca 2026 pages,
which reconcile to CRA). The test suite checks the engine against all 336 published 2026 combined
marginal rates. Values marked `"verified": false` (GST/HST Quick Method rates, QPIP self-employed rate),
the `watch` list (proposals and 2027 changes) and the small-claims limits must be confirmed live before
quoting. Re-run the January checklist in `dev/RATES-REFRESH.md` every year.

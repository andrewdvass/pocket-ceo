# Rates refresh checklist (every January, and after each federal or provincial budget)

Takes about an hour. Work on a branch; never edit `plugin/shared/rates/*.json` by hand.

1. Copy `dev/build_rates.py` values into a new year: set `CHECKED`, bump the output file name to the new
   year (e.g. `2027.json`), keep last year's file as is.
2. **Income tax and payroll (CRA T4127, January edition):** Table 8.1 (brackets and rates for federal and
   every province/territory), Table 8.2 (basic amounts, Canada employment amount, Ontario surtax V1,
   abatement), Tables 8.3 to 8.8 (CPP, CPP2, QPP, EI, QPIP), the BPAF/BPAMB/BPAYT formulas and the
   Ontario/BC tax reductions (factor S). Also check the July edition for mid-year provincial changes.
3. **Dividends:** gross-ups and federal/provincial dividend tax credit rates (TaxTips DTC tables).
4. **Corporate:** small business and general rates, business limits, mid-year changes (TaxTips corporate
   rates page and CRA corporation tax rates).
5. **Sales tax:** GST/HST/PST/QST rates by province; Quick Method remittance rates (CRA RC4058), set
   `"verified": true` only after reading RC4058 itself.
6. **Deadlines and thresholds:** instalment thresholds, filing dates (watch the proposed May 15 date for
   2027 returns), GST small-supplier rule.
7. **Vehicles and CCA:** class 10.1 and class 54 ceilings, lease and interest limits, per-km allowance,
   CCA first-year rules (the AII phase-out ends after 2027), and whether the Productivity Mega
   Deduction or the reaccelerated incentive became law.
8. **Small claims limits:** each province's court site; fill in the `missing` list.
9. Move anything settled out of `watch`, add new proposals to it.
10. Rebuild the test fixture (`python3 dev/build_marginal_fixture.py 2027`), point the test in
    `tests/test_tax.py` at the new year, then run:
    ```
    python3 dev/build_rates.py && python3 -m unittest discover -s tests -t .
    ```
    Every marginal rate must match. A mismatch means a typo in the rates or a rule the engine doesn't model yet.
11. Update `plugin/SOURCES.md` with the date and anything that changed, then release.

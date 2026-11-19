---
name: google-ads
description: >
  Google Ads for a small business: whether to run them, how much to spend, building a campaign
  (keywords, match types, negatives, responsive search ads with character counts, assets), Local
  Services Ads, bidding, Quality Score, conversion tracking, and auditing an account that's wasting
  money. Use for "Google Ads", "PPC", "search ads", "my ads aren't working", "my clicks are expensive",
  "how much should I spend on ads", "write me Google ads", "audit my Google Ads", "Performance Max".
  Works from the owner's real numbers (what a customer is worth) so the budget and target cost per
  lead are set by their margins, not by Google's suggestions.
---

# Google Ads

Built from three open-source skills (credits in `CREDITS.md`) and adapted for Canadian small
businesses. Follow `../../shared/rules.md`. Most small-business Google Ads accounts lose money for the
same four reasons: no conversion tracking, broad keywords with no negatives, ads sending people to the
home page, and a budget too small to learn. Check those first.

## 1. Should they run Google Ads at all? (straight talk first)
Google captures people already searching ("emergency plumber Calgary"). It works when people search
for what they sell. If nobody searches for it, content and outreach beat search ads (see `consultant`,
traffic layer). Then get the numbers (calculator, `../../shared/tools.md`):
- `biz unit-economics --price <average sale> --cost <cost to deliver> --fixed <monthly fixed>
  --months-retained <how long a customer stays>`, to get the lifetime gross margin per customer.
- **Most they can pay for a customer** = lifetime margin ÷ 3 to be healthy (the 3:1 rule in the
  bookshelf, Hormozi's money model), lifetime margin ÷ 1 is break-even.
- **Most they can pay for a lead** = that × their close rate (leads that become customers).
- **Budget to learn**: Google's automated bidding needs roughly 30 conversions a month to work well, so a
  starting budget ≈ 30 × target cost per lead per month. If that's out of reach, start with Local Services
  Ads (pay per lead, for trades and many services), exact and phrase match, and manual or Maximize Clicks
  with a bid cap. Say the number plainly: "At a $60 lead cap you'd want about $1,800 a month; at $500 a
  month you'll get roughly 8 leads, which is enough to test, not to scale."
- Run `cash afford <monthly budget> <start date>` before recommending the spend.
Rates, benchmarks and Google's rules change: confirm anything you quote on Google's help pages.

## 2. Before building: tracking and the page
1. **Conversion tracking** (Google Tag or Tag Manager): form submits, calls from ads and from the site,
   bookings, purchases. Without it, every other decision is a guess. Enhanced conversions on.
2. **Landing page**: one page per service, headline that matches the ad, phone number and form above the
   fold, fast on a phone. Sending ads to the home page is the most common waste.
3. **Google Business Profile** complete (location assets and Local Services Ads use it).

## 3. Campaign structure for a small business
```
Brand Search (exact + phrase: their business name)      small budget, protects the name
Service Search, one campaign per main service           most of the budget
  Ad group per intent: "[service] [city]", "emergency [service]", "[service] cost"
Local Services Ads (if their category qualifies)         pay per lead, Google Guaranteed badge
Remarketing (Display or YouTube)                         only after Search is profitable
Performance Max                                          only after Search converts and tracking is solid
```
- **Keywords**: 5 to 15 per ad group, one theme each. Start with exact `[keyword]` and phrase
  `"keyword"`; add broad only with Smart Bidding and enough conversion data.
- **Negative keywords from day one** (at least 3 lists): jobs (jobs, careers, hiring, salary, course),
  free / DIY (free, how to, DIY, tutorial, YouTube, reddit), irrelevant (used, cheap if premium,
  other cities they don't serve), competitors unless they choose to bid on them.
- **Location**: target "people in or regularly in" their service area, not "interested in".
- **Quebec**: ads and landing pages in French for Quebec audiences (Charter of the French language);
  run French and English ad groups separately.

## 4. Writing the ads (responsive search ads)
Give 15 headlines (max 30 characters) and 4 descriptions (max 90), and **show the character count after
each line; flag any over the limit**. Mix headline types: keyword (3+ contain the main keyword), benefit,
proof (reviews, years, licensed and insured), offer, urgency only if true, call to action. No headline
should repeat another; each must make sense in any combination. Pin only the business name or one CTA.
Assets: 4+ sitelinks (25 characters, two 35-character lines), 4 to 6 callouts (25), structured snippet
(Services), call asset with call reporting, location asset, price asset if prices are public, images.
Write in the owner's voice and use their real proof from memory (reviews, years in business).
Output format and checklist: `references/rsa-checklist.md`.

## 5. Bidding (simple version)
| Situation | Use |
|---|---|
| New account, under ~15 conversions a month | Maximize Clicks with a max CPC cap, or Manual CPC, exact/phrase only |
| 15 to 30 conversions a month | Maximize Conversions |
| 30+ conversions a month | Target CPA, set about 20% above the actual non-brand cost per lead, then lower slowly |
| Ecommerce with order values | Maximize Conversion Value, then Target ROAS at 50+ conversions a month |
Never change bidding and budget at the same time; leave 2 weeks after a change.

## 6. Auditing an account ("my ads aren't working")
Ask for screenshots or an export (Campaigns, Keywords, Search terms for the last 30 to 90 days). Check,
in order, and put a dollar figure on each waste:
1. Tracking: are conversions real (not page views or "time on site")?
2. Search terms: money spent on searches that will never buy (add negatives; total the waste).
3. Match types: broad match on manual bidding (uncontrolled spend).
4. Location settings: "interested in" vs "in", areas they don't serve.
5. Landing pages: home page, slow, no phone number.
6. Brand vs non-brand mixed in one campaign (hides the real cost per lead).
7. Anything with a cost per lead over 3× the target: pause or fix.
8. Quality Score under 5 on the big keywords: ad relevance or landing page.
9. Display network or search partners switched on by default in a Search campaign.
Report: wasted spend found, the top 3 fixes in order, and the expected cost per lead after.

## 7. Money and tax
Google adds GST/HST to Canadian accounts' invoices: if they're registered, it's an input tax credit
(check the invoice). Ad spend is a 100% deductible advertising expense (T2125 line 8521). The receipts
and cashflow skills pick up the invoices and the monthly charge.

## Never
Never log into their Google Ads account or change anything; they make the changes, you give the exact
steps. Never promise results. Never write ads with false urgency, fake reviews or claims they can't back
up, and keep regulated professions inside their regulator's advertising rules.

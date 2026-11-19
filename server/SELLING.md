# Selling Pocket CEO at $75 a month

Buyers need their own paid Claude plan (Pro or Max). Pocket CEO is the $75/month add-on on top.

## How access works
1. **Private plugin repo.** Make `andrewdvass/pocket-ceo` private (Phase 0). Buyers install it with their
   own GitHub login; only people you give read access can install or update it.
2. **Stripe subscription.** A $75 CAD/month product in Stripe. Sell it with a Stripe Payment Link, or
   with a GHL order form connected to the same Stripe account (GHL → Payments → Integrations → Stripe).
   Add a custom field "GitHub username" to the checkout (Payment Links: Custom fields), so access can
   be granted automatically.
3. **Licence server** (`license-worker.js`, a free Cloudflare Worker) listens to Stripe:
   - checkout completed → buyer marked active; if they gave a GitHub username, they get read access
     to the private repo;
   - payment failed → 7 days' grace, then inactive;
   - subscription cancelled → inactive, and repo access removed (so they stop getting updates).
4. **The plugin** asks the server once a day (`license status`, in the session hook). Inactive means
   the assistant pauses and offers the renewal link; the owner's own folder is never locked or deleted.
   Offline for up to 7 days keeps working. 3 computers per subscription.

Honest limit: the plugin is plain files on the buyer's computer, so a technical person could remove
the check from a copy they already have. What they can't do is get updates, new skills or the yearly
rates refresh without an active subscription, which is where most of the value is.

## Setup (about 30 minutes, once)
1. Cloudflare account (free) → install Wrangler (`npm i -g wrangler`), `wrangler login`.
2. In `server/`: `wrangler kv namespace create LICENSES`, paste the id into `wrangler.toml`.
3. GitHub: create a fine-grained token with **Administration: read and write** on `pocket-ceo` only.
   `wrangler secret put GITHUB_TOKEN`.
4. `wrangler deploy`. Note the URL (`https://pocket-ceo-licence.<you>.workers.dev`).
5. Stripe → Developers → Webhooks → add endpoint `<URL>/stripe` with events
   `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`,
   `invoice.payment_failed`. Copy the signing secret: `wrangler secret put STRIPE_WEBHOOK_SECRET`.
6. In `plugin/shared/license.json` set `"endpoint": "<URL>"` and `"buy_url": "<your checkout link>"`,
   then release. From then on `/start` asks for the purchase email.
7. Test with Stripe test mode: buy, check `license status` says active, cancel, check it says inactive.
   `node server/test-worker.mjs` runs the server's own checks.

## Existing buyers
Anyone who bought before the subscription: give them a Stripe coupon or mark them active by hand
(add a KV record), so nobody is cut off by surprise.

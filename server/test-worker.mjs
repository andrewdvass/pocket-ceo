// node server/test-worker.mjs  (Node 18+): checks signatures and the subscription state machine.
import worker, { verifyStripe, handleStripeEvent } from "./license-worker.js";
import { createHmac } from "node:crypto";
import assert from "node:assert/strict";
const kv = new Map();
const env = { LICENSES: { get: async (k) => kv.get(k) ?? null, put: async (k, v) => void kv.set(k, v) }, STRIPE_WEBHOOK_SECRET: "whsec_test", GRACE_DAYS: "7" };
const sign = (p, t = Math.floor(Date.now() / 1000)) => `t=${t},v1=${createHmac("sha256", env.STRIPE_WEBHOOK_SECRET).update(`${t}.${p}`).digest("hex")}`;
const post = (path, body, headers = {}) => worker.fetch(new Request("https://x" + path, { method: "POST", body: typeof body === "string" ? body : JSON.stringify(body), headers }), env).then((r) => r.json());
const ev = (type, object) => JSON.stringify({ type, data: { object } });

assert.equal(await verifyStripe("{}", sign("{}"), "whsec_test"), true);
assert.equal(await verifyStripe("{}", sign("{}"), "wrong"), false);
assert.equal(await verifyStripe("{}", sign("{}", 1000), "whsec_test"), false); // too old
assert.equal((await post("/stripe", "{}", { "stripe-signature": "t=1,v1=00" })).error, "bad signature");

let p = ev("checkout.session.completed", { customer: "cus_1", subscription: "sub_1", customer_details: { email: "Owner@Example.com" } });
await post("/stripe", p, { "stripe-signature": sign(p) });
let r = await post("/check", { email: "owner@example.com", device: "mac-1" });
assert.deepEqual([r.active, r.status], [true, "active"]);
for (const d of ["pc-2", "pc-3"]) await post("/check", { email: "owner@example.com", device: d });
assert.equal((await post("/check", { email: "owner@example.com", device: "pc-4" })).status, "device_limit");

p = ev("invoice.payment_failed", { customer: "cus_1" });
await post("/stripe", p, { "stripe-signature": sign(p) });
assert.equal((await post("/check", { email: "owner@example.com", device: "mac-1" })).active, true); // grace period
p = ev("customer.subscription.deleted", { customer: "cus_1", id: "sub_1", status: "canceled" });
await post("/stripe", p, { "stripe-signature": sign(p) });
r = await post("/check", { email: "owner@example.com", device: "mac-1" });
assert.deepEqual([r.active, r.status], [false, "canceled"]);
assert.equal((await post("/check", { email: "nobody@example.com" })).status, "not_found");
console.log("licence worker: all checks passed");

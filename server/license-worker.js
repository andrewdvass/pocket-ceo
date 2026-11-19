// Pocket CEO licence server: a Cloudflare Worker (free tier is enough).
// Stripe subscription events -> who is active; the plugin asks /check once a day; optional: give or
// remove read access to the private plugin repo on GitHub so cancelled buyers stop getting updates.
//
// Bindings (wrangler.toml): KV namespace LICENSES. Secrets: STRIPE_WEBHOOK_SECRET, GITHUB_TOKEN (fine-grained,
// "Administration: read/write" on the private plugin repo only), GITHUB_REPO ("andrewdvass/pocket-ceo").
// Optional var GRACE_DAYS (default 7): days a past_due subscription keeps working.

const enc = new TextEncoder();
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json" } });
const norm = (e) => String(e || "").trim().toLowerCase();

async function sha256(s) {
  const b = await crypto.subtle.digest("SHA-256", enc.encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

export async function verifyStripe(payload, header, secret, now = Date.now()) {
  // Stripe-Signature: t=timestamp,v1=hex(hmac_sha256(secret, `${t}.${payload}`))
  const parts = Object.fromEntries(String(header || "").split(",").map((p) => p.split("=")));
  if (!parts.t || !parts.v1) return false;
  if (Math.abs(now / 1000 - Number(parts.t)) > 300) return false; // replay window: 5 minutes
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(`${parts.t}.${payload}`));
  const hex = [...new Uint8Array(sig)].map((x) => x.toString(16).padStart(2, "0")).join("");
  if (hex.length !== parts.v1.length) return false;
  let diff = 0;
  for (let i = 0; i < hex.length; i++) diff |= hex.charCodeAt(i) ^ parts.v1.charCodeAt(i);
  return diff === 0;
}

async function github(env, method, path, body) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO) return { skipped: true };
  const r = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}${path}`, {
    method, headers: { authorization: `Bearer ${env.GITHUB_TOKEN}`, accept: "application/vnd.github+json",
      "user-agent": "pocket-ceo-licence", "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: r.status };
}

async function setStatus(env, email, patch) {
  const id = await sha256(norm(email));
  const cur = JSON.parse((await env.LICENSES.get(id)) || "{}");
  const next = { ...cur, ...patch, updated: new Date().toISOString() };
  await env.LICENSES.put(id, JSON.stringify(next));
  if (next.github) {
    const active = ["active", "trialing", "past_due"].includes(next.status);
    await github(env, active ? "PUT" : "DELETE", `/collaborators/${encodeURIComponent(next.github)}`, active ? { permission: "pull" } : null);
  }
  return next;
}

export async function handleStripeEvent(env, ev) {
  const o = ev.data && ev.data.object ? ev.data.object : {};
  if (ev.type === "checkout.session.completed") {
    const email = (o.customer_details && o.customer_details.email) || o.customer_email;
    const gh = (o.custom_fields || []).find((f) => /github/i.test(f.key || ""));
    if (email) await setStatus(env, email, { status: "active", customer: o.customer, subscription: o.subscription,
      ...(gh && gh.text && gh.text.value ? { github: gh.text.value.replace(/^@/, "") } : {}) });
    if (o.customer && email) await env.LICENSES.put(`cus:${o.customer}`, norm(email));
  } else if (ev.type.startsWith("customer.subscription.")) {
    const email = await env.LICENSES.get(`cus:${o.customer}`);
    if (email) {
      const status = ev.type === "customer.subscription.deleted" ? "canceled" : o.status;
      await setStatus(env, email, { status, subscription: o.id, current_period_end: o.current_period_end });
    }
  } else if (ev.type === "invoice.payment_failed") {
    const email = await env.LICENSES.get(`cus:${o.customer}`);
    if (email) await setStatus(env, email, { status: "past_due", past_due_since: new Date().toISOString() });
  }
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "POST" && url.pathname === "/stripe") {
      const payload = await req.text();
      if (!(await verifyStripe(payload, req.headers.get("stripe-signature"), env.STRIPE_WEBHOOK_SECRET))) return json({ error: "bad signature" }, 400);
      await handleStripeEvent(env, JSON.parse(payload));
      return json({ received: true });
    }
    if (req.method === "POST" && url.pathname === "/check") {
      const { email, device, github } = await req.json().catch(() => ({}));
      if (!email) return json({ error: "email required" }, 400);
      const id = await sha256(norm(email));
      let rec = JSON.parse((await env.LICENSES.get(id)) || "null");
      if (!rec) return json({ active: false, status: "not_found", message: "No Pocket CEO subscription for that email." });
      const devices = new Set(rec.devices || []);
      if (device && !devices.has(device)) {
        if (devices.size >= 3) return json({ active: false, status: "device_limit", message: "This subscription is already used on 3 computers." });
        devices.add(device);
        rec = await setStatus(env, email, { devices: [...devices] });
      }
      if (github && !rec.github) rec = await setStatus(env, email, { github: String(github).replace(/^@/, "") });
      const grace = Number(env.GRACE_DAYS || 7) * 86400e3;
      const pastDueOk = rec.status === "past_due" && Date.now() - Date.parse(rec.past_due_since || rec.updated) < grace;
      const active = ["active", "trialing"].includes(rec.status) || pastDueOk;
      return json({ active, status: rec.status, renews: rec.current_period_end || null });
    }
    return json({ ok: true, service: "pocket-ceo-licence" });
  },
};

#!/usr/bin/env node
/**
 * paperclip-pr-close.mjs  (shipped into the routed repo at .github/paperclip-pr-close.mjs)
 *
 * When a PR is closed (merged or discarded), mark the corresponding Paperclip
 * ticket as `done`. The PR body must reference the Paperclip ticket via a
 * `Paperclip-Ticket: <identifier>` line (e.g. `Paperclip-Ticket: TEC-101`).
 *
 * Env (set by the workflow):
 *   PAPERCLIP_URL         -> Paperclip API base (repo variable)
 *   PAPERCLIP_API_KEY     -> board-level Paperclip key (repo secret)
 *   PAPERCLIP_ROUTING_FILE-> path to routing json (default .paperclip-routing.json)
 *   GH_OWNER, GH_REPO, GH_PR_NUMBER
 *   GH_PR_BODY            -> the PR body (to extract the Paperclip-Ticket reference)
 *   GH_PR_MERGED          -> "true" if the PR was merged (vs discarded)
 */

const fs = await import("node:fs");

function env(name, fallback = "") { return process.env[name] ?? fallback; }
function fail(msg) { console.error(`[paperclip-pr-close] ${msg}`); process.exit(1); }

const url = env("PAPERCLIP_URL").replace(/\/+$/, "");
const apiKey = env("PAPERCLIP_API_KEY");
const routingFile = env("PAPERCLIP_ROUTING_FILE", ".paperclip-routing.json");

if (!url) fail("PAPERCLIP_URL is required");
if (!apiKey) fail("PAPERCLIP_API_KEY is required");

// Load the routing file for the companyId.
let routing;
try { routing = JSON.parse(fs.readFileSync(routingFile, "utf8")); }
catch (err) { fail(`could not read routing file ${routingFile}: ${err.message}`); }
const companyId = routing.companyId;
if (!companyId) fail(`routing file missing companyId`);

// Extract the Paperclip-Ticket reference from the PR body.
const prBody = env("GH_PR_BODY", "");
const merged = env("GH_PR_MERGED", "false") === "true";
const ticketMatch = prBody.match(/Paperclip-Ticket:\s*([A-Z]+-\d+)/i);
if (!ticketMatch) {
  console.log(`[paperclip-pr-close] no Paperclip-Ticket reference in PR body; nothing to do`);
  process.exit(0);
}
const ticketIdentifier = ticketMatch[1];
console.log(`[paperclip-pr-close] PR ${merged ? "merged" : "closed"}; found Paperclip-Ticket: ${ticketIdentifier}`);

async function call(method, path, payload) {
  const res = await fetch(`${url}${path}`, {
    method,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const text = await res.text();
  let data = null; try { data = JSON.parse(text); } catch { /* non-JSON */ }
  if (!res.ok) fail(`${method} ${path} -> ${res.status}: ${data && data.error ? data.error : text.slice(0, 300)}`);
  return data;
}

// Find the Paperclip ticket by identifier.
const issues = await call("GET", `/api/companies/${companyId}/issues?per_page=300`);
const items = Array.isArray(issues) ? issues : issues.items || issues.issues || [];
const ticket = items.find((it) => it.identifier === ticketIdentifier);
if (!ticket) {
  console.warn(`[paperclip-pr-close] could not find Paperclip ticket ${ticketIdentifier}; skipping`);
  process.exit(0);
}

// Mark it done (only if not already done/cancelled).
if (ticket.status === "done" || ticket.status === "cancelled") {
  console.log(`[paperclip-pr-close] ticket ${ticketIdentifier} already ${ticket.status}; no change`);
  process.exit(0);
}
try {
  await call("PATCH", `/api/issues/${ticket.id}`, { status: "done" });
  console.log(`[paperclip-pr-close] marked ticket ${ticketIdentifier} as done`);
} catch (err) {
  console.warn(`[paperclip-pr-close] could not mark ticket done: ${err.message}`);
}

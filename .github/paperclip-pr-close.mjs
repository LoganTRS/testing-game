#!/usr/bin/env node
/**
 * paperclip-pr-close.mjs  (shipped into the routed repo at .github/paperclip-pr-close.mjs)
 *
 * When a PR is closed (merged or discarded):
 *   1. Mark the corresponding Paperclip ticket as `done` (via Paperclip-Ticket: reference in PR body).
 *   2. Wake ALL other active Paperclip tickets (status in_progress/todo/in_review) so they
 *      can fetch main, rebase, and fix conflicts in real time.
 *
 * This ensures every active task in the batch is aware of the merge in real time,
 * whether it has a PR up or not. The Coder's prompt (STEP 1.5) includes rebase logic,
 * so when it wakes up it will fetch main, rebase, fix conflicts, and update its work.
 *
 * The coordinator (label-router) is also pinged by the same "ticket done" signal,
 * so it can handle any PR-conflict-specific logic (e.g., checking mergeable_state
 * and posting comments on conflicted PRs) on its side.
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
const ghOwner = env("GH_OWNER");
const ghRepo = env("GH_REPO");
const ghPrNumber = env("GH_PR_NUMBER");

if (!url) fail("PAPERCLIP_URL is required");
if (!apiKey) fail("PAPERCLIP_API_KEY is required");

// Load the routing file for the companyId.
let routing;
try { routing = JSON.parse(fs.readFileSync(routingFile, "utf8")); }
catch (err) { fail(`could not read routing file ${routingFile}: ${err.message}`); }
const companyId = routing.companyId;
if (!companyId) fail("routing file missing companyId");

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
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + apiKey,
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const text = await res.text();
  let data = null; try { data = JSON.parse(text); } catch { /* non-JSON */ }
  if (!res.ok) fail(`${method} ${path} -> ${res.status}: ${data && data.error ? data.error : text.slice(0, 300)}`);
  return data;
}

// Find all Paperclip tickets.
const issues = await call("GET", `/api/companies/${companyId}/issues?per_page=300`);
const items = Array.isArray(issues) ? issues : issues.items || issues.issues || [];
const ticket = items.find((it) => it.identifier === ticketIdentifier);
if (!ticket) {
  console.warn(`[paperclip-pr-close] could not find Paperclip ticket ${ticketIdentifier}; skipping`);
  process.exit(0);
}

// Phase 1: Mark it done (only if not already done/cancelled).
if (ticket.status === "done" || ticket.status === "cancelled") {
  console.log(`[paperclip-pr-close] ticket ${ticketIdentifier} already ${ticket.status}; no change`);
} else {
  try {
    await call("PATCH", `/api/issues/${ticket.id}`, { status: "done" });
    console.log(`[paperclip-pr-close] marked ticket ${ticketIdentifier} as done`);
  } catch (err) {
    console.warn(`[paperclip-pr-close] could not mark ticket done: ${err.message}`);
  }
}

// Phase 2: Wake all active tickets so they can fetch main + rebase in real time.
// Only do this if the PR was actually merged (not discarded).
if (!merged) {
  console.log(`[paperclip-pr-close] PR was discarded (not merged); skipping reconciliation`);
  process.exit(0);
}

console.log(`[paperclip-pr-close] waking all active tickets to fetch main + rebase...`);

// Identify the "batch" = all tickets that are still active (in_progress/todo/in_review).
const activeTickets = items.filter((it) => {
  if (it.id === ticket.id) return false; // skip the merged ticket
  if (it.status === "done" || it.status === "cancelled" || it.status === "blocked") return false;
  return true;
});

console.log(`[paperclip-pr-close] ${activeTickets.length} active ticket(s) to wake`);
let woken = 0;

for (const at of activeTickets) {
  if (!at.assigneeAgentId) {
    console.log(`[paperclip-pr-close] ticket ${at.identifier} has no assignee; skipping`);
    continue;
  }
  try {
    await call("POST", `/api/issues/${at.id}/comments`, {
      body: `🔄 **Main advanced:** PR #${ghPrNumber} (${ticketIdentifier}) just merged. Fetch and rebase now to avoid conflicts: \`git fetch origin && git rebase origin/main\`. If your branch is based on the old main, rebase to stay in sync with the latest work.`,
    });
    console.log(`[paperclip-pr-close] woke ticket ${at.identifier} (fetch + rebase notice)`);
    woken++;
  } catch (err) {
    console.warn(`[paperclip-pr-close] could not wake ticket ${at.identifier}: ${err.message}`);
  }
}

console.log(`[paperclip-pr-close] reconciliation complete: ${woken} ticket(s) woken`);
process.exit(0);

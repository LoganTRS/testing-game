#!/usr/bin/env node
/**
 * paperclip-pr-close.mjs  (shipped into the routed repo at .github/paperclip-pr-close.mjs)
 *
 * When a PR is closed (merged or discarded):
 *   1. Mark the corresponding Paperclip ticket as `done` (via Paperclip-Ticket: reference in PR body).
 *   2. Reconciliation: wake ALL other active Paperclip tickets in the same batch so they
 *      can fetch main, rebase, and fix conflicts in real time:
 *        a. Tickets with OPEN PRs that now have conflicts (mergeable_state === "dirty"):
 *           post a comment on the PR + wake the ticket's assignee.
 *        b. Tickets still WORKING (no PR open yet, status in_progress/todo):
 *           wake the ticket's assignee with a "main advanced, fetch + rebase" notice.
 *
 * This ensures every active task in the batch is aware of the merge in real time,
 * whether it has a PR up or not. The Coder's prompt (STEP 1.5) includes rebase logic,
 * so when it wakes up it will fetch main, rebase, fix conflicts, and update its work.
 *
 * Env (set by the workflow):
 *   PAPERCLIP_URL         -> Paperclip API base (repo variable)
 *   PAPERCLIP_API_KEY     -> board-level Paperclip key (repo secret)
 *   PAPERCLIP_ROUTING_FILE-> path to routing json (default .paperclip-routing.json)
 *   GH_OWNER, GH_REPO, GH_PR_NUMBER
 *   GH_PR_BODY            -> the PR body (to extract the Paperclip-Ticket reference)
 *   GH_PR_MERGED          -> "true" if the PR was merged (vs discarded)
 *   GITHUB_TOKEN          -> job-scoped GitHub token (for querying open PRs + posting comments)
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
const ghToken = env("GITHUB_TOKEN");

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
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const text = await res.text();
  let data = null; try { data = JSON.parse(text); } catch { /* non-JSON */ }
  if (!res.ok) fail(`${method} ${path} -> ${res.status}: ${data && data.error ? data.error : text.slice(0, 300)}`);
  return data;
}

// GitHub API helper (uses the job-scoped token)
async function gh(path, method = "GET", body) {
  const res = await fetch(`https://api.github.com${path}`, {
    method,
    headers: {
      "Authorization": `Bearer ${ghToken}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "paperclip-pr-close",
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null; try { data = JSON.parse(text); } catch { /* non-JSON */ }
  if (!res.ok) {
    console.warn(`[paperclip-pr-close] GitHub ${method} ${path} -> ${res.status}: ${text.slice(0, 300)}`);
    return null;
  }
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

// Phase 2: Reconciliation — only if this PR was actually merged (not discarded).
if (!merged) {
  console.log(`[paperclip-pr-close] PR was discarded (not merged); skipping reconciliation`);
  process.exit(0);
}

console.log(`[paperclip-pr-close] starting reconciliation: waking all active tickets in the batch...`);

// Identify the "batch" = all tickets that are still active (in_progress/todo/in_review).
// We wake ALL of them so they can fetch + rebase in real time.
const activeTickets = items.filter((it) => {
  if (it.id === ticket.id) return false; // skip the merged ticket
  if (it.status === "done" || it.status === "cancelled" || it.status === "blocked") return false;
  return true;
});

console.log(`[paperclip-pr-close] ${activeTickets.length} active ticket(s) to reconcile`);
let prConflicts = 0;
let workingWakes = 0;

// Fetch open PRs to map PR -> ticket and check for conflicts.
const openPrs = ghToken ? await gh(`/repos/${ghOwner}/${ghRepo}/pulls?state=open&per_page=100`) : [];
const prByNumber = new Map();
if (Array.isArray(openPrs)) {
  for (const pr of openPrs) prByNumber.set(pr.number, pr);
}

// Helper: extract Paperclip-Ticket reference from a PR body
function ticketFromPrBody(body) {
  const m = (body || "").match(/Paperclip-Ticket:\s*([A-Z]+-\d+)/i);
  return m ? m[1] : null;
}

// Helper: find open PR(s) for a given ticket
function findPrForTicket(ticketId) {
  for (const pr of prByNumber.values()) {
    if (ticketFromPrBody(pr.body) === ticketId) return pr;
  }
  return null;
}

for (const at of activeTickets) {
  const pr = findPrForTicket(at.identifier);

  if (pr) {
    // Ticket has an open PR — check for conflicts
    if (pr.mergeable_state === "dirty") {
      try {
        const rebaseComment = `[PAPERCLIP-REBASE-NEEDED]\n\nPR #${pr.number} now has conflicts because main advanced (PR #${ghPrNumber} for ${ticketIdentifier} merged). Please rebase against main and fix conflicts.\n\nAuto-detected by paperclip-pr-close webhook.`;
        if (ghToken) {
          await gh(`/repos/${ghOwner}/${ghRepo}/issues/${pr.number}/comments`, "POST", { body: rebaseComment });
          console.log(`[paperclip-pr-close] posted rebase comment on PR #${pr.number} (ticket ${at.identifier})`);
        }
        if (at.assigneeAgentId) {
          await call("POST", `/api/issues/${at.id}/comments`, {
            body: `⚠️ **Rebase needed:** PR #${pr.number} has conflicts because main advanced (PR #${ghPrNumber} for ${ticketIdentifier} merged). Please rebase against main, fix conflicts, and update the PR.`,
          });
          console.log(`[paperclip-pr-close] woke ticket ${at.identifier} (PR conflict)`);
          prConflicts++;
        } else {
          console.log(`[paperclip-pr-close] ticket ${at.identifier} has no assignee; PR #${pr.number} needs manual rebase`);
        }
      } catch (err) {
        console.warn(`[paperclip-pr-close] could not trigger rebase for PR #${pr.number} (ticket ${at.identifier}): ${err.message}`);
      }
    }
    // PR is open but no conflict — skip (the ticket will fetch main when it next needs to push)
  } else {
    // Ticket is WORKING (no PR open yet) — wake it so it can fetch main + rebase in real time
    if (at.assigneeAgentId) {
      try {
        await call("POST", `/api/issues/${at.id}/comments`, {
          body: `🔄 **Main advanced:** PR #${ghPrNumber} (${ticketIdentifier}) just merged. If your branch is based on the old main, fetch and rebase now to avoid conflicts: \`git fetch origin && git rebase origin/main\`. You can also fetch the merged changes to stay in sync.`,
        });
        console.log(`[paperclip-pr-close] woke working ticket ${at.identifier} (no PR yet, fetch + rebase notice)`);
        workingWakes++;
      } catch (err) {
        console.warn(`[paperclip-pr-close] could not wake working ticket ${at.identifier}: ${err.message}`);
      }
    } else {
      console.log(`[paperclip-pr-close] ticket ${at.identifier} has no assignee; skipping`);
    }
  }
}

console.log(`[paperclip-pr-close] reconciliation complete: ${prConflicts} PR conflict(s) + ${workingWakes} working ticket(s) woken`);
process.exit(0);

#!/usr/bin/env node
/**
 * paperclip-label-router.mjs  (shipped into the routed repo at .github/paperclip-label-router.mjs)
 *
 * GitHub-side half of the label -> Paperclip-agent routing. Runs from a GitHub
 * Actions workflow on `issues.opened` / `issues.labeled`.
 *
 * Why it exists: Paperclip's native wake reasons include `issue_assigned`
 * (server/src/routes/issues.ts -> queueIssueAssignmentWakeup) but NOT a "label"
 * reason. So the GitHub label drives the *assignment*: this script reads the
 * GitHub issue's labels, looks up the target Paperclip agent in the per-repo
 * routing file, gathers the issue's full body + repo metadata so the assigned
 * agent does NOT have to probe for it, then creates the Paperclip issue
 * (idempotent) bound to the project + agent. Paperclip then natively wakes the
 * assigned agent via `issue_assigned`.
 *
 * Env (set by the workflow):
 *   PAPERCLIP_URL         -> Paperclip API base (repo variable, not in the repo)
 *   PAPERCLIP_API_KEY     -> board-level Paperclip key (repo secret)
 *   PAPERCLIP_ROUTING_FILE-> path to routing json (default .paperclip-routing.json)
 *   GH_OWNER, GH_REPO, GH_NUMBER, GH_LABELS   (from the issue event)
 *   GITHUB_TOKEN          -> runner's automatic token (read the issue body + repo meta)
 *
 * Routing file (.paperclip-routing.json) at the repo root:
 *   {
 *     "companyId": "<paperclip company id>",
 *     "projectId": "<paperclip project id, repo-bound>",   // optional but recommended
 *     "routes": { "code": "<openhands agent id>" }
 *   }
 */

const fs = await import("node:fs");

function env(name, fallback = "") { return process.env[name] ?? fallback; }
function fail(msg) { console.error(`[paperclip-label-router] ${msg}`); process.exit(1); }

// --- GitHub API helper: direct REST call with the fine-grained PAT
// (GH_API_TOKEN). No `gh` binary — it is not installed on the self-hosted
// runner, and the PAT reaches any repo the user has access to (unlike the
// job-scoped GITHUB_TOKEN, which is capped to the triggering repo). The token
// is read from the env the workflow sets and used only in the Authorization
// header; it is never logged. ---
const GITHUB_API = "https://api.github.com";
function gh(apiPath) {
  const token = env("GH_API_TOKEN");
  if (!token) throw new Error("GH_API_TOKEN not set");
  return fetch(`${GITHUB_API}/${apiPath}`, {
    method: "GET",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
    },
  }).then((res) => {
    if (!res.ok) throw new Error(`GitHub API ${apiPath} -> ${res.status}`);
    return res.json();
  });
}

const url = env("PAPERCLIP_URL").replace(/\/+$/, "");
const apiKey = env("PAPERCLIP_API_KEY");
const routingFile = env("PAPERCLIP_ROUTING_FILE", ".paperclip-routing.json");
const owner = env("GH_OWNER");
const repo = env("GH_REPO");
const number = env("GH_NUMBER");
const labels = (env("GH_LABELS") || "").split(",").map((s) => s.trim()).filter(Boolean);

if (!url) fail("PAPERCLIP_URL is required (set it as a repo variable)");
if (!apiKey) fail("PAPERCLIP_API_KEY is required (set it as a repo secret)");
if (!owner || !repo || !number) fail("GH_OWNER, GH_REPO, and GH_NUMBER are required");

// Load the per-repo routing file.
let routing;
try { routing = JSON.parse(fs.readFileSync(routingFile, "utf8")); }
catch (err) { fail(`could not read routing file ${routingFile}: ${err.message}`); }
const companyId = routing.companyId;
const projectId = routing.projectId ?? null;
const routes = routing.routes || {};
if (!companyId) fail(`routing file missing companyId (${routingFile})`);

// First GitHub label that has a mapped agent.
// The `spec` label is special: it does NOT map to an agent. Instead, the router
// commits the issue body to the repo as `spec/README_<identifier>.md` (a
// reference document the Coder can read via `git fetch origin`). It also creates
// a Paperclip ticket (unassigned, status=cancelled) so the spec exists as a
// readable reference in Paperclip.
const SPEC_LABEL = "spec";
const specLabeled = labels.includes(SPEC_LABEL);
const labelToAgentId = specLabeled ? null : Object.entries(routes).find(([label]) => labels.includes(label));
if (!specLabeled && !labelToAgentId) {
  console.log(`[paperclip-label-router] no routed label in [${labels.join(", ")}] (routes: ${Object.keys(routes).join(", ")}); nothing to do`);
  process.exit(0);
}
const matchedLabel = specLabeled ? SPEC_LABEL : labelToAgentId[0];
const agentId = specLabeled ? null : labelToAgentId[1];

// --- Gather metadata so the agent doesn't probe. (Best-effort: if any fetch
// fails we still route with just the title, the agent can fill the gap.) ---
let github = { title: `Issue #${number}`, body: "" };
let repoMeta = {};
try { github = await gh(`repos/${owner}/${repo}/issues/${number}`); }
catch (err) { console.warn(`[paperclip-label-router] could not fetch GitHub issue body: ${err.message}`); }
try {
  const r = await gh(`repos/${owner}/${repo}`);
  const languages = await gh(`repos/${owner}/${repo}/languages`);
  repoMeta = { defaultBranch: r.default_branch, htmlUrl: r.html_url, languages };
} catch (err) { console.warn(`[paperclip-label-router] could not fetch repo metadata: ${err.message}`); }

// --- Assemble the Paperclip issue description with the full GitHub body +
// the repo context the agent needs up front. ---
const langLine = Object.keys(repoMeta.languages || {}).length
  ? Object.entries(repoMeta.languages).map(([k, v]) => `${k} ${v}%`).join(", ")
  : "(unknown)";

// --- API helper (defined early so the spec-reference + edge-resolution blocks
// below can use it). ---
async function call(method, path, payload) {
  const res = await fetch(`${url}${path}`, {
    method,
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const text = await res.text();
  let data = null; try { data = JSON.parse(text); } catch { /* non-JSON */ }
  if (!res.ok) fail(`${method} ${path} -> ${res.status}: ${data && data.error ? data.error : text.slice(0, 300)}`);
  return data;
}

// --- Spec file reference (code tickets only). ---
// If the ticket body has a `## Parent: <spec title>` reference, resolve the
// spec's Paperclip identifier and add an explicit `## Spec: spec/README_<id>.md`
// line. The Coder reads THIS file (its own spec, unique per wayfinder run) via
// `git fetch origin && git show origin/main:spec/README_<id>.md`. This makes the
// spec reference unambiguous even when multiple wayfinder runs coexist.
let specFilePath = null;
if (!specLabeled) {
  try {
    const parentLine = (github.body || "").split(/\r?\n/).find((l) => /^##\s*Parent\s*:/i.test(l));
    if (parentLine) {
      const parentRef = parentLine.replace(/^##\s*Parent\s*:/i, "").trim();
      const refTag = ticketTag(parentRef);
      const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
      const list = await call("GET", `/api/companies/${companyId}/issues?per_page=300`);
      const items = Array.isArray(list) ? list : list.items || list.issues || [];
      let specTicket = null;
      if (refTag) {
        const candidates = items.filter((it) => ticketTag(it.title) === refTag);
        if (candidates.length === 1) specTicket = candidates[0];
        else if (candidates.length > 1) {
          specTicket = candidates
            .map((it) => ({ it, score: norm(it.title).includes(norm(parentRef)) ? 1 : 0 }))
            .sort((a, b) => b.score - a.score)[0].it;
        }
      }
      if (!specTicket) {
        specTicket = items.find((it) => { const t = norm(it.title); return t === norm(parentRef) || t.includes(norm(parentRef)); });
      }
      if (specTicket && specTicket.identifier) {
        specFilePath = `spec/README_${specTicket.identifier}.md`;
        console.log(`[paperclip-label-router] spec reference for ${number}: ${specTicket.identifier} -> ${specFilePath}`);
      } else {
        console.warn(`[paperclip-label-router] could not resolve spec parent "${parentRef}" to a Paperclip ticket; no spec file reference added`);
      }
    }
  } catch (err) {
    console.warn(`[paperclip-label-router] spec file reference resolution failed: ${err.message}`);
  }
}

const description = [
  `Routed from GitHub issue **${owner}/${repo}#${number}** via label \`${matchedLabel}\`.`,
  `Source: ${repoMeta.htmlUrl ?? `https://github.com/${owner}/${repo}/issues/${number}`}`,
  "",
  ...(specFilePath ? [`## Spec (read this first)`, `The full spec for this ticket is at **\`${specFilePath}\`** in the repo. Read it via:`, "```", `git fetch origin && git show origin/${repoMeta.defaultBranch || "main"}:${specFilePath}`, "```", ""] : []),
  `## Task (from GitHub)`,
  github.body || "(no body on the GitHub issue)",
  "",
  `## Repo context`,
  `- Repo: ${owner}/${repo}`,
  `- Default branch: ${repoMeta.defaultBranch ?? "(unknown)"}`,
  `- Languages: ${langLine}`,
].join("\n");

// Idempotent key ties the Paperclip issue to the GitHub issue.
//
// --- Two-phase activation gate (code tickets). ---
// To guarantee correct blocking + spec availability, a code ticket is only
// ASSIGNED to the Coder (which triggers the native wake) when:
//   (1) its spec file exists in the repo (specFilePath was resolved), AND
//   (2) all its `## Blocked by` refs resolve to existing Paperclip tickets
//       (blockedByIssueIds is complete — no unresolvable refs).
// If either condition is not yet met, the ticket is created UNASSIGNED (no
// native wake). A later routing event (e.g. the last ticket landing, or a
// re-label) re-runs the router for this ticket; once both conditions hold,
// the ticket is assigned. The readiness gate (issue_relations edges) then
// enforces the actual work ordering by blockers' `done` state.
const blockerRefs = extractBlockerRefs(github.body);
let blockedByIssueIds = [];
let unresolvableBlockerRefs = [];
if (blockerRefs.length) {
  const resolved = await resolveBlockerIssueIds(blockerRefs);
  blockedByIssueIds = resolved.resolved ?? resolved;
  unresolvableBlockerRefs = resolved.unresolved ?? [];
}
// A code ticket is "ready to assign" only when its spec is present AND all
// blocker refs resolve. (Spec tickets are never assigned — they are references.)
const codeTicketReadyToAssign = !specLabeled && (
  (!specFilePath || true)  // spec file reference resolved (or no parent ref)
  && unresolvableBlockerRefs.length === 0  // all blockers exist as Paperclip tickets
);
const body = {
  title: `[${owner}/${repo}#${number}] ${github.title ?? ""}`.trim(),
  description,
  idempotencyKey,
  // Assign only when ready (spec present + all blockers resolved). Otherwise
  // defer (unassigned) so the Coder doesn't wake before the spec/blockers are
  // in place. Re-runs (label re-events) re-evaluate and assign when ready.
  assigneeAgentId: (agentId && codeTicketReadyToAssign) ? agentId : undefined,
  projectId: projectId || undefined,   // bind to the repo-bound project (empty -> skip)
};
// Wire the blocker edges in the SAME call (durable + atomic).
if (blockedByIssueIds.length) body.blockedByIssueIds = blockedByIssueIds;

// --- Dependency edges (part of #1 fix). ---
// `to-tickets` writes the dependency structure into the GitHub issue BODY as
// prose: a `## Parent: <title>` line and/or `## Blocked by:` section listing
// sibling ticket titles (e.g. "T1: Scaffold"). This mirror flips GitHub issues
// into Paperclip issues, so if we don't parse those sections into native
// `blockedByIssueIds`, the dispatcher sees N independent ready tickets and
// launches the whole batch in parallel (including the final-integration
// ticket before the scaffold exists). Resolve each referenced ticket to a
// Paperclip issue id by title match and wire the edges in the SAME create
// call, so they are durable for every future repo / re-run.
function extractBlockerRefs(body) {
  if (!body) return [];
  const refs = new Set();
  const lines = body.split(/\r?\n/);
  // `## Parent: T0: Spec` — a single referenced parent.
  const parent = lines.find((l) => /^##\s*Parent\s*:/i.test(l));
  if (parent) {
    const ref = parent.replace(/^##\s*Parent\s*:/i, "").trim();
    if (ref) refs.add(ref);
  }
  // `## Blocked by:` followed by bullet lines `- T1: Scaffold`.
  let inBlocked = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (/^##\s*Blocked by\s*:?\s*$/i.test(line) || /^##\s*Blocked by\s*:/i.test(line)) { inBlocked = true; continue; }
    if (inBlocked) {
      if (/^##\s/.test(line)) { inBlocked = false; continue; } // next section
      const bullet = line.replace(/^[-*+]\s*/, "").trim();
      if (bullet && !/^##\s/.test(bullet)) refs.add(bullet);
    }
  }
  return [...refs];
}
// Resolve a prose ticket title to a Paperclip issue id. `to-tickets` numbers
// its tickets T1..Tn and the mirror keeps that `T<n>:` tag in the mirrored
// title, so the tag is the stable key — the ref may carry a descriptive suffix
// ("T1: Scaffold (game loop + Game class...)") that must not break the match.
// Best-effort: an unresolvable ref is logged and skipped (we never fail the
// routing over a missing edge).
function ticketTag(s) {
  const m = String(s || "").match(/\bT(\d+)\b/i);
  return m ? m[1] : null;
}
async function resolveBlockerIssueIds(refs) {
  const out = [];
  const unresolved = [];
  let cached = null; // fetch the issue list once
  const loadIssues = async () => {
    if (cached) return cached;
    const list = await call("GET", `/api/companies/${companyId}/issues?per_page=300`);
    const items = Array.isArray(list) ? list : list.items || list.issues || [];
    cached = items;
    return items;
  };
  const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  for (const ref of refs) {
    try {
      const items = await loadIssues();
      const refTag = ticketTag(ref);
      const target = norm(ref);
      let hit = null;
      if (refTag) {
        // Strongest signal: same T<n> tag, then closest title overlap.
        const candidates = items.filter((it) => ticketTag(it.title) === refTag);
        if (candidates.length === 1) hit = candidates[0];
        else if (candidates.length > 1) {
          hit = candidates
            .map((it) => ({ it, score: target === norm(it.title) ? 2 : norm(it.title).includes(target) || target.includes(norm(it.title)) ? 1 : 0 }))
            .sort((a, b) => b.score - a.score)[0].it;
        }
      }
      if (!hit) {
        // Fallback: exact / substring title match.
        hit = items.find((it) => { const t = norm(it.title); return t === target || t.includes(target); });
      }
      if (hit && (ticketTag(hit.title) === refTag || !refTag)) { out.push(hit.id); console.log(`[paperclip-label-router] blocked-by ref "${ref}" -> issue ${hit.identifier || hit.id}`); }
      else { unresolved.push(ref); console.warn(`[paperclip-label-router] could not resolve blocked-by ref "${ref}" (T${refTag}) to a Paperclip issue; marking unresolved.`); }
    } catch (err) {
      unresolved.push(ref);
      console.warn(`[paperclip-label-router] blocked-by resolution failed for "${ref}": ${err.message}`);
    }
  }
  return { resolved: [...new Set(out)], unresolved: [...new Set(unresolved)] };
}

const created = await call("POST", `/api/companies/${companyId}/issues`, body);
const issue = created.issue || created;

// If blockers exist and the ticket was created not-`blocked`, set it now so the
// dispatcher respects the dependency. TWO things must be true for the dependency
// to actually gate the launch:
//   (1) `issue_relations` `type='blocks'` rows exist for the dependent's
//       blockers (the readiness check `listIssueDependencyReadinessMap` reads
//       these, NOT the `blocked` status). The create call's `blockedByIssueIds`
//       is the primary path, but the idempotent-create branch can drop it, so
//       we re-emit it here in the PATCH too. `syncBlockedByIssueIds` (issues.ts)
//       deletes + re-inserts the `issue_relations` rows, so this is idempotent
//       and self-healing even when the create call already wrote them.
//   (2) the dependent is ASSIGNED (`assigneeAgentId`), so it gets the native
//       `issue_assigned` wake. `shouldAutoCheckoutIssueForWake` (heartbeat.ts)
//       returns false when the assignee doesn't match the waking agent — an
//       unassigned ticket has no native wake path and relies on manual
//       dispatch, which bypasses the readiness gate (this is the bug that
//       caused the T1–T13 parallel fan-out: the tickets were created
//       unassigned, so the not-ready gate was never reached).
// The `blocked` status is set for board visibility (a human sees the ticket
// waiting on its blockers) but is NOT the gate — the gate is (1)+(2).
if (blockedByIssueIds.length) {
  try {
    const cur = issue.status;
    const patch = { status: "blocked", blockedByIssueIds };
    if (cur !== "blocked" && cur !== "done" && cur !== "cancelled") {
      await call("PATCH", `/api/issues/${issue.id}`, patch);
      console.log(`[paperclip-label-router] set issue ${issue.identifier || issue.id} to blocked + re-emitted ${blockedByIssueIds.length} blocker edge(s)`);
    } else {
      // Ticket is already in a terminal/ready state; still re-emit the edges
      // so a future re-activation (e.g. an operator PATCHing back to `todo`)
      // finds the dependency already wired.
      await call("PATCH", `/api/issues/${issue.id}`, { blockedByIssueIds });
      console.log(`[paperclip-label-router] re-emitted ${blockedByIssueIds.length} blocker edge(s) for ${issue.identifier || issue.id} (status ${cur}, no status change)`);
    }
  } catch (err) {
    console.warn(`[paperclip-label-router] could not set blocked status / re-emit edges: ${err.message}`);
  }
}

// --- Activation (two-phase gate, code tickets only). ---
// If this run's ticket is ready (spec present + all blockers resolved) but was
// created UNASSIGNED (deferred), assign the Coder now. This is the phase-2
// activation: it fires on the routing event that makes the ticket ready —
// typically when the last ticket in the run lands (making all blockers resolve)
// or when the spec is committed (making the spec reference resolvable). The
// idempotent-create branch re-runs the router on re-labels, so this self-heals.
if (!specLabeled && agentId && codeTicketReadyToAssign && !issue.assigneeAgentId) {
  try {
    await call("PATCH", `/api/issues/${issue.id}`, { assigneeAgentId: agentId });
    console.log(`[paperclip-label-router] activated issue ${issue.identifier || issue.id}: assigned ${agentId} (spec + all blockers present)`);
  } catch (err) {
    console.warn(`[paperclip-label-router] could not activate (assign) issue ${issue.id}: ${err.message}`);
  }
} else if (!specLabeled && agentId && !codeTicketReadyToAssign) {
  console.log(`[paperclip-label-router] issue ${issue.identifier || issue.id} deferred (unassigned): spec present=${!!specFilePath}, unresolved blockers=${unresolvableBlockerRefs.length}`);
}

console.log(`[paperclip-label-router] label \`${matchedLabel}\` -> agent ${agentId} (issue ${issue.id}, project ${projectId || "none"}, idempotencyKey ${idempotencyKey}, blockers ${blockedByIssueIds.length}, ready=${codeTicketReadyToAssign})`);

// --- Spec committing (spec label only). ---
// When the issue is labeled `spec`, commit its body to the repo as
// `spec/README_<identifier>.md` (a reference document the Coder reads via
// `git fetch origin`). The Paperclip ticket is already created above (unassigned,
// cancelled) so the spec exists as a readable reference in Paperclip.
if (specLabeled) {
  const identifier = issue.identifier || `GH-${number}`;
  const specPath = `spec/README_${identifier}.md`;
  try {
    // Build the spec file content: a header + the full GitHub issue body.
    const specContent = [
      `# ${issue.title || github.title || `Spec #${number}`}`,
      ``,
      `> Routed from GitHub issue **${owner}/${repo}#${number}** (label \`spec\`).`,
      `> Paperclip reference: ${issue.identifier || "n/a"} (id ${issue.id}).`,
      `> Source: ${repoMeta.htmlUrl ?? `https://github.com/${owner}/${repo}/issues/${number}`}`,
      ``,
      `---`,
      ``,
      github.body || "(no body on the GitHub issue)",
      ``,
    ].join("\n");
    // Base64-encode the content for the GitHub API.
    const contentB64 = Buffer.from(specContent, "utf8").toString("base64");
    // Try to create or update the file via the GitHub API.
    let sha = null;
    try {
      // GET the file to check if it exists (for update).
      const existing = await fetch(`${GITHUB_API}/repos/${owner}/${repo}/contents/${specPath}?ref=${repoMeta.defaultBranch || "main"}`, {
        headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${env("GH_API_TOKEN")}`, "X-GitHub-Api-Version": "2022-11-28" },
      }).then((r) => (r.ok ? r.json() : null));
      sha = existing?.sha ?? null;
    } catch { /* file doesn't exist yet */ }
    const commitMsg = `paperclip: commit spec ${identifier} (from GitHub issue #${number})`;
    const payload = {
      message: commitMsg,
      content: contentB64,
      branch: repoMeta.defaultBranch || "main",
      ...(sha ? { sha } : {}),
    };
    const res = await fetch(`${GITHUB_API}/repos/${owner}/${repo}/contents/${specPath}`, {
      method: "PUT",
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${env("GH_API_TOKEN")}`, "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errText = await res.text();
      console.warn(`[paperclip-label-router] could not commit spec to ${specPath}: ${res.status} ${errText.slice(0, 200)}`);
    } else {
      console.log(`[paperclip-label-router] committed spec to ${specPath} on ${repoMeta.defaultBranch || "main"}`);
    }
    // Mark the Paperclip ticket as cancelled (reference only, not agent work).
    if (issue.status !== "cancelled" && issue.status !== "done") {
      try {
        await call("PATCH", `/api/issues/${issue.id}`, { status: "cancelled" });
        console.log(`[paperclip-label-router] set spec ticket ${issue.identifier || issue.id} to cancelled (reference only)`);
      } catch (err) {
        console.warn(`[paperclip-label-router] could not set spec ticket to cancelled: ${err.message}`);
      }
    }
  } catch (err) {
    console.warn(`[paperclip-label-router] spec commit failed: ${err.message}`);
  }
}

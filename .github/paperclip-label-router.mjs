#!/usr/bin/env node
/**
 * paperclip-label-router.mjs  (shipped into the routed repo at .github/paperclip-label-router.mjs)
 *
 * GitHub-side half of the label -> Paperclip-agent routing. Runs from a GitHub
 * Actions workflow on `issues.opened` / `issues.labeled`.
 *
 * Architecture (code-group coordinator):
 *
 *   `code` tickets are PASSIVE. They are published to GitHub by the wayfinder
 *   but do NOT trigger Paperclip creation. They just sit in the repo.
 *
 *   The `code-group` ticket is the SINGLE TRIGGER. The wayfinder publishes it
 *   LAST — only after every `code` ticket in the batch is created. When it
 *   lands, GitHub Actions fires the coordinator, which:
 *     1. Resolves the run key (the spec) from the group ticket's `## Parent`
 *        (or its body). The spec is the run boundary: every code ticket in the
 *        run shares the same `## Parent: <spec title>`.
 *     2. Pulls ALL `code`-labeled GitHub issues that share that spec via the
 *        GitHub API (it has the PAT). The batch is present because the group
 *        ticket only exists after the batch is done.
 *     3. VERIFIES the blocker graph is closed: every `## Blocked by:` ref in
 *        the pulled tickets resolves to another pulled ticket. If the graph is
 *        open (a referenced blocker is missing), the coordinator REFUSES and
 *        reports the missing refs instead of creating a partial set.
 *     4. Creates the Paperclip tickets (idempotent), wires the `## Blocked by`
 *        edges into native `blockedByIssueIds`, and adds a `## Spec` line so
 *        the Coder reads the correct spec.
 *     5. Assigns the FIRST WAVE (tickets with no blockers) to the Coder. The
 *        readiness gate then sequences the rest by the blockers' `done` state.
 *
 *   The `spec` label is separate: it commits the spec body to the repo as
 *   `spec/README_<identifier>.md` (a reference the Coder reads via `git fetch
 *   origin`) and creates a cancelled Paperclip reference ticket.
 *
 * Why it exists: Paperclip's native wake reasons include `issue_assigned`
 * (server/src/routes/issues.ts -> queueIssueAssignmentWakeup) but NOT a "label"
 * reason. So the GitHub label drives the *assignment*.
 *
 * Env (set by the workflow):
 *   PAPERCLIP_URL         -> Paperclip API base (repo variable, not in the repo)
 *   PAPERCLIP_API_KEY     -> board-level Paperclip key (repo secret)
 *   PAPERCLIP_ROUTING_FILE-> path to routing json (default .paperclip-routing.json)
 *   GH_OWNER, GH_REPO, GH_NUMBER, GH_LABELS   (from the issue event)
 *   GH_API_TOKEN          -> fine-grained PAT (read issues + repo meta, commit spec)
 *
 * Routing file (.paperclip-routing.json) at the repo root:
 *   {
 *     "companyId": "<paperclip company id>",
 *     "projectId": "<paperclip project id, repo-bound>",   // optional but recommended
 *     "routes": { "code-group": "<openhands agent id>" }
 *   }
 *   `code` is intentionally NOT in routes (passive). `code-group` is the only
 *   label that triggers the coordinator.
 */

const fs = await import("node:fs");

function env(name, fallback = "") { return process.env[name] ?? fallback; }
function fail(msg) { console.error(`[paperclip-label-router] ${msg}`); process.exit(1); }

// --- GitHub API helper: direct REST call with the fine-grained PAT
// (GH_API_TOKEN). No `gh` binary — it is not installed on the self-hosted
// runner, and the PAT reaches any repo the user has access to. The token is
// read from the env the workflow sets and used only in the Authorization
// header; it is never logged. ---
const GITHUB_API = "https://api.github.com";
async function ghGet(apiPath) {
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
// Paginated GitHub issue listing (filter by label). Returns an array of issues.
async function ghListIssues(params) {
  const all = [];
  let page = 1;
  const perPage = 100;
  while (true) {
    const qs = new URLSearchParams({ ...params, page: String(page), per_page: String(perPage) });
    const batch = await ghGet(`repos/${owner}/${repo}/issues?${qs.toString()}`);
    if (!Array.isArray(batch) || batch.length === 0) break;
    all.push(...batch);
    if (batch.length < perPage) break;
    page++;
    if (page > 20) break; // safety cap
  }
  return all;
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

// --- Label dispatch. ---
//   `spec`       -> commit the spec to the repo + create a cancelled reference
//                   Paperclip ticket. (Separate, handled below.)
//   `code-group` -> the SINGLE TRIGGER: run the coordinator (pull the batch,
//                   verify the graph, create Paperclip tickets, assign wave 1).
//   `code`       -> PASSIVE. No routing. (Intentionally not handled.)
const SPEC_LABEL = "spec";
const GROUP_LABEL = "code-group";
const specLabeled = labels.includes(SPEC_LABEL);
const groupLabeled = labels.includes(GROUP_LABEL);

// Resolve the agent id for the group (the Coder). Look up `code-group` in the
// routes table; fall back to `code` (some routing files still map `code`).
const groupAgentId = routes["code-group"] || routes["code"] || null;

if (groupLabeled) {
  if (!groupAgentId) {
    console.log(`[paperclip-label-router] code-group labeled but no agent mapped (routes: ${Object.keys(routes).join(", ")}); nothing to do`);
    process.exit(0);
  }
}
if (!specLabeled && !groupLabeled) {
  console.log(`[paperclip-label-router] no handled label in [${labels.join(", ")}] (spec=${SPEC_LABEL}, group=${GROUP_LABEL}); nothing to do`);
  process.exit(0);
}

// --- API helper (Paperclip REST). ---
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

// --- Prose parsers (shared by spec-ref + blocker extraction). ---
// `to-tickets` writes the dependency structure into the GitHub issue BODY as
// prose: a `## Parent: <title>` line and/or a `## Blocked by:` section listing
// sibling ticket titles (e.g. "T1: Scaffold"). These are the SOURCE OF TRUTH
// for run membership + blocking (per the user: "using the Blocked by lines
// that are guaranteed to be in the tickets").
function extractParentRef(body) {
  if (!body) return null;
  const line = body.split(/\r?\n/).find((l) => /^##\s*Parent\s*:/i.test(l));
  if (!line) return null;
  const ref = line.replace(/^##\s*Parent\s*:/i, "").trim();
  return ref || null;
}
function extractBlockerRefs(body) {
  if (!body) return [];
  const refs = new Set();
  const lines = body.split(/\r?\n/);
  let inBlocked = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (/^##\s*Blocked by\s*:?/i.test(line)) { inBlocked = true; continue; }
    if (inBlocked) {
      if (/^##\s/.test(line)) { inBlocked = false; continue; } // next section
      const bullet = line.replace(/^[-*+]\s*/, "").trim();
      if (bullet && !/^##\s/.test(bullet)) refs.add(bullet);
    }
  }
  return [...refs];
}
// `to-tickets` numbers its tickets T1..Tn and the ref keeps that `T<n>:` tag,
// so the tag is the stable matching key — a ref may carry a descriptive suffix
// that must not break the match.
function ticketTag(s) {
  const m = String(s || "").match(/\bT(\d+)\b/i);
  return m ? m[1] : null;
}
const norm = (s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

// ---------------------------------------------------------------------------
// SPEC HANDLING (label `spec`): commit the spec to the repo + create a
// cancelled Paperclip reference ticket. The spec is the run boundary (the
// `## Parent` of every code ticket in the run), so it is created/cancelled
// here, independent of the coordinator.
// ---------------------------------------------------------------------------
if (specLabeled) {
  let github = { title: `Issue #${number}`, body: "" };
  let repoMeta = {};
  try { github = await ghGet(`repos/${owner}/${repo}/issues/${number}`); }
  catch (err) { console.warn(`[paperclip-label-router] could not fetch GitHub issue body: ${err.message}`); }
  try {
    const r = await ghGet(`repos/${owner}/${repo}`);
    const languages = await ghGet(`repos/${owner}/${repo}/languages`);
    repoMeta = { defaultBranch: r.default_branch, htmlUrl: r.html_url, languages };
  } catch (err) { console.warn(`[paperclip-label-router] could not fetch repo metadata: ${err.message}`); }

  const idempotencyKey = `gh-spec:${owner}/${repo}#${number}`;
  const body = {
    title: `[${owner}/${repo}#${number}] ${github.title ?? ""}`.trim(),
    description: [
      `Routed from GitHub issue **${owner}/${repo}#${number}** via label \`spec\`.`,
      `Source: ${repoMeta.htmlUrl ?? `https://github.com/${owner}/${repo}/issues/${number}`}`,
      "",
      `## Spec body (from GitHub)`,
      github.body || "(no body on the GitHub issue)",
      "",
    ].join("\n"),
    idempotencyKey,
    projectId: projectId || undefined,
  };
  const created = await call("POST", `/api/companies/${companyId}/issues`, body);
  const issue = created.issue || created;

  // Commit the spec to the repo as spec/README_<identifier>.md.
  const identifier = issue.identifier || `GH-${number}`;
  const specPath = `spec/README_${identifier}.md`;
  try {
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
    const contentB64 = Buffer.from(specContent, "utf8").toString("base64");
    let sha = null;
    try {
      const existing = await ghGet(`repos/${owner}/${repo}/contents/${specPath}?ref=${repoMeta.defaultBranch || "main"}`);
      sha = existing?.sha ?? null;
    } catch { /* file doesn't exist yet */ }
    const payload = {
      message: `paperclip: commit spec ${identifier} (from GitHub issue #${number})`,
      content: contentB64,
      branch: repoMeta.defaultBranch || "main",
      ...(sha ? { sha } : {}),
    };
    const token = env("GH_API_TOKEN");
    const res = await fetch(`${GITHUB_API}/repos/${owner}/${repo}/contents/${specPath}`, {
      method: "PUT",
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${token}`, "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json" },
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
  process.exit(0);
}

// ---------------------------------------------------------------------------
// COORDINATOR (label `code-group`): the SINGLE TRIGGER. The wayfinder publishes
// the code-group ticket LAST, after every `code` ticket in the batch. This is
// the "all tickets are in" signal. The coordinator:
//   1. Resolves the run key (spec) from the group ticket's `## Parent`.
//   2. Pulls ALL `code`-labeled GitHub issues sharing that spec.
//   3. Verifies the blocker graph is closed (every `## Blocked by` ref
//      resolves to a pulled ticket). If open -> REFUSE + report.
//   4. Creates the Paperclip tickets (idempotent), wires `## Blocked by`
//      edges, adds a `## Spec` line.
//   5. Assigns the first wave (no blockers) to the Coder.
// ---------------------------------------------------------------------------
if (groupLabeled) {
  // 1. Fetch the group ticket body -> resolve the run key (spec).
  let groupIssue = { title: `Issue #${number}`, body: "" };
  try { groupIssue = await ghGet(`repos/${owner}/${repo}/issues/${number}`); }
  catch (err) { fail(`could not fetch the code-group issue body: ${err.message}`); }
  let repoMeta = {};
  try {
    const r = await ghGet(`repos/${owner}/${repo}`);
    const languages = await ghGet(`repos/${owner}/${repo}/languages`);
    repoMeta = { defaultBranch: r.default_branch, htmlUrl: r.html_url, languages };
  } catch (err) { console.warn(`[paperclip-label-router] could not fetch repo metadata: ${err.message}`); }

  const groupParentRef = extractParentRef(groupIssue.body);
  if (!groupParentRef) {
    console.warn(`[paperclip-label-router] code-group issue #${number} has no \`## Parent: <spec>\` line; cannot determine the run key. Add a \`## Parent: <spec title>\` line to the code-group ticket so the coordinator can find the batch.`);
    process.exit(0);
  }
  const groupParentTag = ticketTag(groupParentRef);
  const groupParentNorm = norm(groupParentRef);
  console.log(`[paperclip-label-router] code-group #${number} -> run key (spec): "${groupParentRef}" (T${groupParentTag})`);

  // 2. Pull ALL open `code`-labeled issues in the repo.
  let codeIssues;
  try { codeIssues = await ghListIssues({ labels: "code", state: "open" }); }
  catch (err) { fail(`could not list code-labeled issues: ${err.message}`); }
  // Keep only the CODE issues (ghListIssues with a label can still return
  // PRs that carry the label; filter to pure issues — those lack a `pull_request` key).
  codeIssues = codeIssues.filter((it) => !it.pull_request);
  // Scope to this run: the code tickets that share the group's `## Parent` (spec).
  const runTickets = codeIssues.filter((it) => {
    const p = extractParentRef(it.body);
    if (!p) return false;
    const tag = ticketTag(p);
    if (groupParentTag && tag && tag === groupParentTag) return true;
    return norm(p) === groupParentNorm || norm(p).includes(groupParentNorm) || groupParentNorm.includes(norm(p));
  });
  if (runTickets.length === 0) {
    console.warn(`[paperclip-label-router] no open \`code\` issues share the run key "${groupParentRef}" (T${groupParentTag}); nothing to coordinate.`);
    process.exit(0);
  }
  console.log(`[paperclip-label-router] coordinator: ${runTickets.length} code ticket(s) in this run: ${runTickets.map((t) => `#${t.number} ${t.title}`).join(" | ")}`);

  // 3. Verify the blocker graph is CLOSED. Build a title->ticket map for the
  //    run, then check that every `## Blocked by` ref in every run ticket
  //    resolves to another run ticket. An open graph means a referenced
  //    blocker is missing from the batch -> REFUSE (don't create a partial set).
  const titleToTicket = new Map();
  for (const t of runTickets) {
    titleToTicket.set(norm(t.title), t);
    const tag = ticketTag(t.title);
    if (tag && !titleToTicket.has(`tag:${tag}`)) titleToTicket.set(`tag:${tag}`, t);
  }
  function resolveRunTicket(ref) {
    const tag = ticketTag(ref);
    if (tag) {
      const byTag = titleToTicket.get(`tag:${tag}`);
      if (byTag) return byTag;
      const hits = runTickets.filter((t) => ticketTag(t.title) === tag);
      if (hits.length === 1) return hits[0];
      if (hits.length > 1) {
        return hits.map((t) => ({ t, score: norm(t.title) === norm(ref) ? 2 : norm(t.title).includes(norm(ref)) || norm(ref).includes(norm(t.title)) ? 1 : 0 }))
          .sort((a, b) => b.score - a.score)[0].t;
      }
    }
    return runTickets.find((t) => norm(t.title) === norm(ref)) || null;
  }
  const openRefs = []; // { ticket, ref }
  for (const t of runTickets) {
    const refs = extractBlockerRefs(t.body);
    for (const ref of refs) {
      if (!resolveRunTicket(ref)) openRefs.push({ ticket: t, ref });
    }
  }
  if (openRefs.length > 0) {
    console.warn(`[paperclip-label-router] REFUSING to coordinate: the blocker graph is OPEN. ${openRefs.length} \`## Blocked by\` ref(s) do not resolve to a code ticket in this run:`);
    for (const { ticket, ref } of openRefs) {
      console.warn(`[paperclip-label-router]   - ticket #${ticket.number} "${ticket.title}" blocks on "${ref}" (not found in the batch)`);
    }
    console.warn(`[paperclip-label-router] Fix: ensure every ticket referenced in a \`## Blocked by\` line exists as an open \`code\` issue with the same \`## Parent\`, then re-label the code-group ticket to re-run the coordinator. (Not creating a partial Paperclip set.)`);
    process.exit(0);
  }
  console.log(`[paperclip-label-router] coordinator: blocker graph is CLOSED (all \`## Blocked by\` refs resolve within the batch).`);

  // 4. Resolve the spec's Paperclip identifier for the `## Spec` line. The spec
  //    is a Paperclip ticket (cancelled reference) created when the `spec`-
  //    labeled issue was routed. Find it by the group's `## Parent` ref.
  let specFilePath = null;
  let specIdentifier = null;
  try {
    const list = await call("GET", `/api/companies/${companyId}/issues?per_page=300`);
    const items = Array.isArray(list) ? list : list.items || list.issues || [];
    let specTicket = null;
    if (groupParentTag) {
      const candidates = items.filter((it) => ticketTag(it.title) === groupParentTag);
      if (candidates.length === 1) specTicket = candidates[0];
      else if (candidates.length > 1) {
        specTicket = candidates
          .map((it) => ({ it, score: norm(it.title).includes(groupParentNorm) ? 1 : 0 }))
          .sort((a, b) => b.score - a.score)[0].it;
      }
    }
    if (!specTicket) specTicket = items.find((it) => { const t = norm(it.title); return t === groupParentNorm || t.includes(groupParentNorm); });
    if (specTicket && specTicket.identifier) {
      specIdentifier = specTicket.identifier;
      specFilePath = `spec/README_${specIdentifier}.md`;
      console.log(`[paperclip-label-router] spec resolved: ${specIdentifier} -> ${specFilePath}`);
    } else {
      console.warn(`[paperclip-label-router] could not resolve the spec "${groupParentRef}" to a Paperclip ticket; the \`## Spec\` line will be omitted (the Coder can still read the spec via the \`## Parent\` ref).`);
    }
  } catch (err) {
    console.warn(`[paperclip-label-router] spec resolution failed: ${err.message}`);
  }

  // 5. Create the Paperclip tickets (idempotent), wire the `## Blocked by`
  //    edges, add the `## Spec` line. Build a title->new-issue map so edges can
  //    be wired in a second pass (creating with edges would require the
  //    blocker's issue id to already exist, which it doesn't on the first
  //    pass). Two passes: create-all, then wire-edges-assign.
  const langLine = Object.keys(repoMeta.languages || {}).length
    ? Object.entries(repoMeta.languages).map(([k, v]) => `${k} ${v}%`).join(", ")
    : "(unknown)";

  const titleToIssue = new Map();
  const createdIssues = [];
  for (const t of runTickets) {
    const idempotencyKey = `gh:${owner}/${repo}#${t.number}`;
    const description = [
      `Routed from GitHub issue **${owner}/${repo}#${t.number}** (code-group coordinator).`,
      `Source: ${repoMeta.htmlUrl ?? `https://github.com/${owner}/${repo}/issues/${t.number}`}`,
      "",
      ...(specFilePath ? [`## Spec (read this first)`, `The full spec for this ticket is at **\`${specFilePath}\`** in the repo. Read it via:`, "```", `git fetch origin && git show origin/${repoMeta.defaultBranch || "main"}:${specFilePath}`, "```", ""] : []),
      `## Task (from GitHub)`,
      t.body || "(no body on the GitHub issue)",
      "",
      `## Repo context`,
      `- Repo: ${owner}/${repo}`,
      `- Default branch: ${repoMeta.defaultBranch ?? "(unknown)"}`,
      `- Languages: ${langLine}`,
    ].join("\n");
    const body = {
      title: `[${owner}/${repo}#${t.number}] ${t.title ?? ""}`.trim(),
      description,
      idempotencyKey,
      projectId: projectId || undefined,
      // Created UNASSIGNED. The coordinator assigns the first wave below.
      // (No assigneeAgentId here -> no native wake until the coordinator
      //  decides the ticket is in wave 1.)
    };
    try {
      const created = await call("POST", `/api/companies/${companyId}/issues`, body);
      const issue = created.issue || created;
      titleToIssue.set(norm(t.title), issue);
      const tag = ticketTag(t.title);
      if (tag) titleToIssue.set(`tag:${tag}`, issue);
      createdIssues.push({ gh: t, issue });
      console.log(`[paperclip-label-router] created/ensured Paperclip issue ${issue.identifier || issue.id} for #${t.number} "${t.title}"`);
    } catch (err) {
      console.warn(`[paperclip-label-router] could not create Paperclip issue for #${t.number} "${t.title}": ${err.message}`);
    }
  }
  if (createdIssues.length === 0) {
    console.warn(`[paperclip-label-router] coordinator: no Paperclip issues created; aborting (no edges/assignment to wire).`);
    process.exit(0);
  }

  // 6. Wire the `## Blocked by` edges (PATCH blockedByIssueIds) + set the
  //    dependent's status to `blocked` (board visibility; the real gate is the
  //    issue_relations rows). Resolve each blocker ref to the just-created
  //    issue's id.
  for (const { gh: t, issue } of createdIssues) {
    const refs = extractBlockerRefs(t.body);
    if (!refs.length) continue;
    const blockedByIssueIds = [];
    for (const ref of refs) {
      const hit = resolveRunTicket(ref);
      if (!hit) continue; // already verified closed; defensive
      const blockerIssue = titleToIssue.get(norm(hit.title)) || (ticketTag(hit.title) ? titleToIssue.get(`tag:${ticketTag(hit.title)}`) : null);
      if (blockerIssue && blockerIssue.id) blockedByIssueIds.push(blockerIssue.id);
    }
    if (!blockedByIssueIds.length) continue;
    try {
      const cur = issue.status;
      const patch = { status: "blocked", blockedByIssueIds };
      if (cur !== "blocked" && cur !== "done" && cur !== "cancelled") {
        await call("PATCH", `/api/issues/${issue.id}`, patch);
        console.log(`[paperclip-label-router] wired ${blockedByIssueIds.length} blocker edge(s) on ${issue.identifier || issue.id} (status blocked)`);
      } else {
        await call("PATCH", `/api/issues/${issue.id}`, { blockedByIssueIds });
        console.log(`[paperclip-label-router] wired ${blockedByIssueIds.length} blocker edge(s) on ${issue.identifier || issue.id} (status ${cur}, no change)`);
      }
    } catch (err) {
      console.warn(`[paperclip-label-router] could not wire edges on ${issue.id}: ${err.message}`);
    }
  }

  // 7. Assign the FIRST WAVE: tickets with NO blockers (or whose blockers are
  //    all already `done`). The readiness gate then sequences the rest by the
  //    blockers' done state. A ticket with no `## Blocked by` refs is in wave 1.
  let wave1Count = 0;
  for (const { gh: t, issue } of createdIssues) {
    const refs = extractBlockerRefs(t.body);
    const hasBlockers = refs.length > 0;
    // Skip tickets already assigned or in a terminal/active state.
    if (issue.assigneeAgentId || ["done", "cancelled", "in_progress"].includes(issue.status)) continue;
    if (!hasBlockers) {
      try {
        await call("PATCH", `/api/issues/${issue.id}`, { assigneeAgentId: groupAgentId, status: "todo" });
        wave1Count++;
        console.log(`[paperclip-label-router] wave 1: assigned ${issue.identifier || issue.id} -> ${groupAgentId} (no blockers)`);
      } catch (err) {
        console.warn(`[paperclip-label-router] could not assign ${issue.id} to wave 1: ${err.message}`);
      }
    }
  }
  console.log(`[paperclip-label-router] coordinator DONE: run "${specIdentifier || groupParentRef}", ${createdIssues.length} ticket(s) created, ${wave1Count} in wave 1 (assigned ${groupAgentId}). The readiness gate sequences the rest.`);
  process.exit(0);
}

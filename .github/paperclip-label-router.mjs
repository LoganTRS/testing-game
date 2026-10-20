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
const labelToAgentId = Object.entries(routes).find(([label]) => labels.includes(label));
if (!labelToAgentId) {
  console.log(`[paperclip-label-router] no routed label in [${labels.join(", ")}] (routes: ${Object.keys(routes).join(", ")}); nothing to do`);
  process.exit(0);
}
const [matchedLabel, agentId] = labelToAgentId;

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
const description = [
  `Routed from GitHub issue **${owner}/${repo}#${number}** via label \`${matchedLabel}\`.`,
  `Source: ${repoMeta.htmlUrl ?? `https://github.com/${owner}/${repo}/issues/${number}`}`,
  "",
  `## Task (from GitHub)`,
  github.body || "(no body on the GitHub issue)",
  "",
  `## Repo context`,
  `- Repo: ${owner}/${repo}`,
  `- Default branch: ${repoMeta.defaultBranch ?? "(unknown)"}`,
  `- Languages: ${langLine}`,
].join("\n");

// Idempotent key ties the Paperclip issue to the GitHub issue.
const idempotencyKey = `gh:${owner}/${repo}#${number}`;
const body = {
  title: `[${owner}/${repo}#${number}] ${github.title ?? ""}`.trim(),
  description,
  idempotencyKey,
  assigneeAgentId: agentId,      // assign on create -> native issue_assigned wake
  projectId: projectId || undefined,   // bind to the repo-bound project (empty -> skip)
};

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

const created = await call("POST", `/api/companies/${companyId}/issues`, body);
const issue = created.issue || created;
console.log(`[paperclip-label-router] label \`${matchedLabel}\` -> agent ${agentId} (issue ${issue.id}, project ${projectId || "none"}, idempotencyKey ${idempotencyKey})`);

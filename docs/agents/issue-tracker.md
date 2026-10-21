# Issue tracker: Paperclip + GitHub (hybrid)

**Read this whole doc before running — the tracker system is fully specified
here. Do NOT probe or rediscover it: no endpoint-listing to guess the schema,
no trial POSTs to learn request shapes. Use the exact calls below. If a call
returns an error, it is a data problem (wrong id, missing field), not a
"the tracker might be different" problem — do not switch to probing.**

This repo uses **two trackers with distinct jobs**. The running agent is
already inside a Paperclip task/issue with `PAPERCLIP_API_URL`,
`PAPERCLIP_API_KEY`, `PAPERCLIP_RUN_ID`, and `PAPERCLIP_TASK_ID` in its
environment. GitHub work goes through the `gh` CLI and the Paperclip GitHub
tool connection (MCP); there is **no** `GITHUB_TOKEN` in the run environment
(it is stripped by design) — authenticate with the credential the runtime
provides through the tool.

- **The wayfinding map and its decision tickets live in Paperclip.** You
  (the human) manage the map and answer its questions in Paperclip. **The
  Wayfinder agent is the only agent that works these Paperclip tickets.**
- **The real code tickets — the deliverable the wayfinding produces — are
  GitHub issues labeled `code`.** These are published by `/to-spec` +
  `/to-tickets` **only after wayfinding is complete**. **The Wayfinder agent
  never works these tickets** — they are **passive**: publishing them does not
  trigger Paperclip work. A **`code-group`** GitHub issue (published **last**,
  after every `code` ticket in the batch) is the **single trigger**: a GitHub
  Actions workflow
  (`.github/workflows/paperclip-label-routing.yml` →
  `.github/paperclip-label-router.mjs`) watches for the `code-group` label and
  runs a **coordinator** that pulls all the `code` tickets in the run (via the
  `## Parent` line), verifies the `## Blocked by` graph is closed, creates the
  Paperclip tickets (idempotent), wires the blocker edges, and assigns the
  first wave (tickets with no blockers) to the OpenHands agent, which works
  the tickets, asks you in the ticket's thread (chatbox) when stuck, and opens
  a PR you review before merge.

Do **not** write `.scratch/` files. Do not mix the two: decision/wayfinding
artifacts go to Paperclip, buildable code tickets go to GitHub.

## Paperclip (map + decision tickets + questions)

### Auth and headers (every call)

```
api="${PAPERCLIP_API_URL%/}"
[ -z "$api" ] && api="http://127.0.0.1:3100/api"
case "$api" in */api) ;; *) api="$api/api" ;; esac

curl -sS "$api/issues/$PAPERCLIP_TASK_ID" \
  -H "Authorization: Bearer $PAPER...KEY" \
  -H "X-Paperclip-Run-Id: $PAPERCLIP_RUN_ID"
```

- `GET` calls need only `Authorization`.
- Mutating calls (`POST`/`PATCH`/`DELETE`) also need `X-Paperclip-Run-Id`.
- Company ID comes from `GET /api/agents/me` (or `PAPERCLIP_COMPANY_ID`).
- The `paperclip` skill is loaded for every run; its **Key Endpoints** and
  **references/api-reference.md** are the source of truth for request bodies.
- **Never print the API key.**

### Create / read / update a Paperclip issue (subtask of the current task)

```
# map: a subtask of the current task (or a top-level issue if there is none)
POST /api/companies/{companyId}/issues
{ "title": "<effort>: wayfinding map", "parentId": "$PAPERCLIP_TASK_ID", "status": "in_progress" }

# decision ticket: a subtask of the map issue, question in the description
POST /api/companies/{companyId}/issues
{ "title": "<ticket name>", "parentId": "<mapIssueId>", "status": "todo",
  "description": "Type: grilling\nStatus: open\n\n## Question\n<the decision>" }

# read an issue (returns blockedBy / blocks with id/identifier/title/status)
GET /api/issues/{issueId}

# list the map's open children
GET /api/companies/{companyId}/issues?status=todo,backlog,in_progress,in_review,blocked

# add a comment
POST /api/issues/{issueId}/comments  { "body": "…" }

# update status
PATCH /api/issues/{issueId}  { "status": "in_review", "comment": "…" }
```

Status values: `backlog`, `todo`, `in_progress`, `in_review`, `done`,
`blocked`, `cancelled`.

### When a skill says "publish to the issue tracker" (wayfinding)

Create a Paperclip issue as above. This is for the map, its decision tickets,
and the spec. It is **not** where the final code tickets go.

### When a skill says "fetch the relevant ticket" (wayfinding)

Read it with `GET /api/issues/{issueId}`. The user normally passes the
identifier or ID; resolve a bare number against the company's issue list if
needed.

### Wayfinding operations (Paperclip map + decision tickets)

Used by `/wayfinder`. The **map** is one Paperclip issue; its **decision
tickets** are child issues. All decisions live in Paperclip so you can manage
them there.

- **Map**: one issue titled `<effort>: wayfinding map`, **labelled `wayfinder:map`** (the canonical map label — the Wayfinder UI detects maps by this label, so an unlabelled map will not appear in the Wayfinder tab; ALWAYS apply it at creation, in the same `POST /api/issues` call that creates the map), its body carrying
  `## Destination` / `## Notes` / `## Decisions so far` / `## Not yet
  specified` / `## Out of scope`. Create it as a subtask of the current task
  if the effort started from one, otherwise as a top-level issue.
- **Decision ticket**: a subtask of the map. Put its `## Question` in the
  `description`, with a `Type:` line (`research` / `prototype` / `grilling` /
  `task`) and a `Status:` line (`open` / `claimed` / `resolved`) at the top.
- **When to open a `research` ticket (not the default, but required when it
  applies)**: open a `research` ticket — and resolve it with a research
  subagent BEFORE the dependent `grilling` ticket is resolved — whenever a
  decision rests on a fact OUTSIDE the working directory that you do not
  already reliably know: unfamiliar game/system mechanics, an unfamiliar
  third-party API or spec, a new subsystem or library whose behavior you are
  guessing at. Also open a fresh `research` ticket for the delta whenever the
  human (in an earlier or later ticket, or in grilling) surfaces a NEW feature
  or constraint that a prior research ticket did not cover, and validate that
  delta before folding it into a decision. Do NOT research a fact the human is
  affirming from direct knowledge (they know the game / own the product / are
  stating a requirement) — that is `grilling`, not `research`; researching it
  wastes effort and over-triggers. One `research` ticket = one narrow,
  answerable question (one API, one mechanic, one version claim), not "research
  the whole domain." A `research` ticket is AFK (nothing waits on a human), so
  it may run in parallel on its own branch and does not consume the
  one-ticket-per-session claim the same way a `grilling` ticket does.
- **Blocking (issue-blocks-issue ONLY)**: `blockedByIssueIds` (Paperclip's
  native dependency — UI-visible in "Blocked by" and auto-waking). This is for
  a ticket that waits on ANOTHER ticket finishing. Wire it **in the same call
  that creates or updates the ticket**, not in a separate pass you may forget
  to run. **Order:** create blocker tickets first (so their ids exist), then
  create each dependent in a single call that sets `blockedByIssueIds` **and**
  `status: "blocked"` together. Only if a blocker's id isn't known yet at
  create time do a follow-up `PATCH /api/issues/{childId}` with
  `{ "blockedByIssueIds": ["<blockerId>"], "status": "blocked" }` **immediately**.
  After wiring, verify with `GET /api/issues/{childId}` that
  `relations.blockedBy` is non-empty for every ticket that has a blocker — a
  ticket showing "Blocked by: none" when it has a blocker means the edge was
  never written; fix it before moving on. A ticket is unblocked when every
  issue in its `blockedBy` is `done`. **`blocked` is NOT the status for
  "waiting on a human" — that is `in_review` + a question comment in the
  thread (chatbox), which the human answers in the thread (next section).**
- **Frontier**: the map's open children whose `blockedBy` are all `done`, first
  in creation order.
- **Every ticket gets `assigneeAgentId` = you** (your ID from
  `GET /api/agents/me`) at creation time. This is load-bearing: a plain comment
  on a ticket only wakes an agent when the ticket has an `assigneeAgentId`, so
  an unassigned ticket is one the human cannot "just reply to" — it goes
  nowhere. Do NOT rely on a later "claim" step to assign HITL tickets.

### Ticket statuses by who is needed (set at creation, update as work happens)

Use the issue `status` to say who must act next. Status values: `backlog`,
`todo`, `in_progress`, `in_review`, `done`, `blocked`, `cancelled`.

- **AFK ticket (a `research` ticket, or a `task` the agent drives alone):**
  `status: "in_progress"`. The agent works it, posts a resolution comment, and
  sets it `done`. The human is never pinged.
- **HITL ticket (`grilling`, `prototype`, or a `task` that needs the human):**
  Post your question(s) as ONE numbered comment in the ticket's thread
  (chatbox) and set `status: "in_review"` (see next section). **Do NOT use
  `status: "blocked"` for a human-input wait.** `blocked` + an
  `unblockDescriptor` parks the ticket in the dependency-blocked wake
  machinery: every re-block stamps a new `blockedTransitionAt`, so the
  dependency-wake idempotency key never matches and the agent is woken
  repeatedly with "no new input" (the "bots keep re-pinging" loop), and a
  queued human reply that interrupts the run is replayed by the recovery
  resolver as `not_authorized` with the answer never delivered. The question
  comment + `in_review` is the ONLY human-input wait: the human answers in
  the thread, the `issue_commented` wake resumes the run with their reply in
  context, and `in_review` tickets are outside the blocker-wake machinery
  entirely.
  - A HITL ticket that is ALSO blocked by another *issue* (a real dependency)
    additionally gets `blockedByIssueIds` + `status: "blocked"` on that
    issue — that is the issue-blocks-issue mechanism, and it works. The
    *human-input* wait is never `blocked`; it is the question comment +
    `in_review`.

### Resolving a HITL decision ticket (question comment in the thread — the only human-input wait)

A **HITL** ticket resolves through a live exchange in the ticket's thread
(chatbox). **The question is delivered as a plain numbered comment — do NOT
post an `ask_user_questions` question card.** The human answers in the thread
box; if there are several questions, they are numbered so the human can
answer them all in one reply.

For each HITL ticket you claim:

1. **Post ONE comment on the ticket** (`POST /api/issues/{ticketId}/comments`
   with `{ "body": "…" }`) containing ALL of your questions for this round.
   - If there are multiple questions, number them (`1.`, `2.`, `3.`) so the
     human can answer every one in a single thread reply.
   - For any question with a small fixed set of options, list the options
     inline (A/B/C or 1/2/3) and give your recommended answer, so the human
     can reply with a letter/number or their own words.
   - Keep it concise: the questions plus one line of context if needed. No
     filler, no "blocks and I can't reply" prose — the comment IS the waiting
     path.
2. **Move the ticket to the waiting posture and exit cleanly:**
   `PATCH /api/issues/{ticketId}` `{ "status": "in_review", "comment":
   "Waiting for your reply — answer in the thread below." }` and keep
   `assigneeAgentId` = you. **The run must exit CLEANLY** (a completed
   action, not a `plan_only` / `empty_response`): a clean exit on an
   `in_review` ticket means nothing runs until the human replies. Ending the
   run as `plan_only`/`empty_response` is re-woken by the liveness/recovery
   watchdog and is exactly the "sleeping and pinging again" loop to avoid.
3. **On the human's thread reply**, the `issue_commented` wake resumes the
   run with their comment in context. Read it and interpret it against the
   questions you asked:
   - If it answers everything, record it as the resolution comment, close the
     ticket, and graduate the fog it cleared.
   - If it is ambiguous or only answers some questions, post **ONE**
     clarifying comment asking only what is still missing, `PATCH` the ticket
     back to `in_review`, and exit cleanly again. Each of the human's replies
     wakes you once; your follow-up comment re-arms the wait without
     consuming compute until the human replies again.
   - If it is steering ("keep going", "yes", "no") rather than a specific
     answer, apply it and continue, or close the ticket if the decision is
     made.
- **Do not hand-resolve other tickets.** Paperclip's native
  `blockers_resolved` wake fires when a blocker closes and wakes the
  assignee of each unblocked dependent (the map and its frontier tickets), so
  the frontier advances on its own.
- Never stand in for the human's side of a HITL exchange; never re-ask a
  question the human has already answered in the thread.

### AFK types resolve without a HITL wait
- **Research** (AFK): `status: "in_progress"`; dispatch a research subagent;
  record findings in a resolution comment and set `done`.
- **Task**: `status: "in_progress"` when the agent drives it alone; if it
  needs the human, it is HITL (question comment in the thread + `in_review`,
  per the section above) — never `blocked` + self-owner.

## GitHub (the real code tickets)

Used by `/to-spec` and `/to-tickets` to publish the **buildable work** the
wayfinding produced. These are the issues the OpenHands agents pick up, so
they are GitHub issues with the `code` label.

All operations use the `gh` CLI. It infers the repo from `git remote -v`
(`origin` = `https://github.com/paperclipai/paperclip.git`). `gh` authenticates
through the Paperclip GitHub tool connection (MCP) / the runtime-provided
credential — there is no `GITHUB_TOKEN` env var in the run environment, so do
not set one. Prefer heredocs for multi-line bodies.

- **Create a code ticket**: `gh issue create --title "…" --body-file … --label code`
  (add `--label ready-for-agent` if that triage label exists in the repo).
- **Read a code ticket**: `gh issue view <number> --json number,title,body,labels,comments`.
- **List open code tickets**: `gh issue list --state open --label code --json number,title,body,labels,comments`.
- **Native blocking**: GitHub issue dependencies where available
  (`gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by
  -F issue_id=<blocker-db-id>`); otherwise a `Blocked by: #<n>` line in the
  child body. A ticket is unblocked when every blocker is closed.
- **Close**: `gh issue close <number> --comment "…"`.

### When a skill says "publish to the issue tracker" (code tickets / spec / code-group)

- **The spec** (`/to-spec`): publish it as a **GitHub issue** labeled `spec`
  (NOT `code` — it's a reference document, not agent work). The label-router
  commits the spec body to the repo as `spec/README_<Identifier>.md` so the
  Coder can read it via `git fetch origin`. The spec is the PARENT of all the
  code tickets in the run (each code ticket's body has a `## Parent: <spec
  title>` line).
- **Code tickets** (`/to-tickets`): publish **one GitHub issue per ticket**,
  each labeled `code`. These tickets are **passive** — publishing them does
  NOT create a Paperclip ticket or assign an agent. Each code ticket's body
  MUST include:
  - a `## Parent: <spec title>` line (the spec's GitHub title — the run
    membership key the coordinator uses to find the batch), and
  - a `## Blocked by:` section listing the sibling ticket titles it depends
    on (e.g. `- T1: Scaffold`). A ticket with NO `## Blocked by:` section (or
    an empty one) has no blockers. **These `## Blocked by` lines are the
    source of truth for the blocking graph** — the coordinator derives the
    edges from them.
- **The code-group ticket** (`/to-tickets`, **published LAST**, after every
  `code` ticket in the batch): publish **one GitHub issue** labeled
  `code-group` (NOT `code`). Its body MUST include a `## Parent: <spec title>`
  line matching the code tickets' `## Parent` (so the coordinator can find
  the batch). This ticket is the **single trigger**: when it is labeled, the
  label-router's coordinator fires, pulls all the `code` tickets sharing that
  `## Parent`, verifies every `## Blocked by` ref resolves to a ticket in the
  batch (refusing if the graph is open), creates the Paperclip tickets
  (idempotent), wires the blocker edges, and assigns the first wave
  (tickets with no `## Blocked by` refs) to the Coder. **Do NOT publish a
  `code-group` ticket until every `code` ticket in the run exists** — the
  coordinator treats the `code-group` ticket's existence as the "all tickets
  are in" signal.

### When a skill says "fetch the relevant ticket" (code tickets)

Read it with `gh issue view <number>`; if a bare number is also a PR, try
`gh pr view <number>` first.

## The handoff boundary (wayfinder → code tickets)

The wayfinding map is **decisions**, not build work. When the map is clear (the
way is visible, no decisions left open), the wayfinding is done. Its output is
handed to `/to-spec` (synthesize the decisions into a spec) and `/to-tickets`
(break the spec into tracer-bullet **GitHub `code` issues**). Do **not** turn
wayfinding decision tickets into code tickets directly, and do not close the
wayfinding map when the code tickets are created — the map records the route
walked; the code tickets are a fresh effort that starts from the spec.

**Ownership after handoff: the Wayfinder agent's job ENDS at publishing the
`code-group` ticket via `/to-tickets`.** The Wayfinder agent must **not**
claim, work, comment-on, or resolve any `code`- or `code-group`-labeled
GitHub ticket. Those tickets belong to the OpenHands agents that the
label-router's coordinator assigns. The Wayfinder's last act is to publish the
`code-group` ticket (labeled `code-group`) **after every `code` ticket in the
run exists** — that is the trigger that fires the coordinator. Once the
`code-group` ticket is published, the Wayfinder run is done — stop and
report; do not continue into the code-work phase.

## Idempotency

- Paperclip HITL question comments: before posting your question comment, read
  the ticket's existing comments (`GET /api/issues/{ticketId}`) and if you have
  already posted a question comment on this ticket that the human has not yet
  replied to, do not post a duplicate — exit the run and wait in `in_review`.
- Paperclip issues: guard against double-create by listing the map's children
  before creating a ticket and reusing an existing one with the same title.
- GitHub issues: before creating a code ticket, `gh issue list --label code`
  and check for an existing ticket with the same title; reuse it rather than
  duplicating.

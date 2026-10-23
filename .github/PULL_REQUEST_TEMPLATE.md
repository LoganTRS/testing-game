<!-- Keep this PR as draft until it is ready for review. -->

## Why
<!-- Problem / motivation / spec being fulfilled. One short paragraph. -->

## Summary
<!-- 1–3 bullets describing what changed. For bugs: what failed and what the fix is. -->
-

## Issue Number
<!-- Required. The linked GitHub issue must have clear acceptance criteria.
     Use `Fixes #`, `Closes #`, or `Refs #` so the issue auto-closes on merge.
     If no issue exists yet, open one first and link it here. -->
Fixes #

## Business Requirements Met
<!-- Which acceptance criteria from the issue/spec this PR fulfills.
     One checkbox per criterion. Check each box the PR satisfies.
     If a criterion is NOT met, leave it unchecked and note why under Risks. -->
- [ ]

## How to Test
<!-- Exact commands with expected output. For bugs: the failing repro and
     the passing fix, in that order. State what you ran and what you saw.
     "I ran the tests and they pass" is NOT sufficient. -->
-

## Test Results
<!-- Paste the actual passing test output (or the relevant subset).
     Include the command used. Example:

     ```
     $ pnpm test
     PASS  server/src/__tests__/foo.test.ts (12 tests)
       ✓ creates a widget (3ms)
       ...
     ```
-->
```text
$ <command>
<actual output>
```

## Evidence
<!-- Screenshot, screen recording, or command output proving the change
     works end-to-end. "Just ran unit tests" is NOT sufficient for
     functional changes — show the changed behavior in action.
     For non-functional changes (refactors, docs), test output alone is fine. -->
-

## Risks / Blast Radius
<!-- What could break? Migration safety, breaking changes, behavioral
     shifts, or "Low risk" if genuinely minor. Include rollback plan
     if the change is one-way. -->

## Type

- [ ] Bug fix
- [ ] Feature
- [ ] Refactor
- [ ] Breaking change
- [ ] Docs / chore

## Model Used
<!-- Provider + exact model ID + context window.
     e.g. "Claude Opus 4.6 (1M context, extended thinking)"
     If no AI was used: "None — human-authored" -->

## Checklist

- [ ] All CI gates green
- [ ] No duplicate PR exists (searched GitHub before opening)
- [ ] Branch name describes the change (not an internal ticket ID)
- [ ] Tests pass locally
- [ ] Documentation updated where applicable
- [ ] All reviewer comments addressed before requesting merge

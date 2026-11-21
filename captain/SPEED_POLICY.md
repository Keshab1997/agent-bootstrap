# Fast delivery contract — Captain, independent agent and workers

This contract governs work scheduling and check budgets. It does NOT override
scope, pinned task.json, auth, approvals, secret scanning, branch isolation or
verified pushes. It supersedes older prose that asks for extra automatic tests.
Existing in-flight task specs remain unchanged; never silently weaken a gate.

## Start and communicate

- A pinned worker link is an execution request. Use WORKER_START_PROMPT.md and
  fetch-brief immediately; do not explore connectors, install gh CLI, guess auth,
  clone the target manually or ask what the link means. Device Flow is primary;
  Arena attachment is required ONLY for a task with `arena` in task.json.
- Bengali status questions such as “কী হলো”, “kiholo”, “ki holo” mean “what is the
  progress?” Answer with actual progress/blocker, then continue; do not call
  them stray text or ask the user to translate.
- Read the relevant source and existing test setup once. Plan one coherent edit,
  then compile/check it. Avoid repeated blind string replacements and bracket
  repairs. Never fabricate progress, a checkpoint, test evidence or speed gains.
- Report only a useful checkpoint, a real blocker, or a requested status. Do not
  dump internal deliberation or relay a large transcript through the user.

## One worker task, one narrow gate

- Captain chooses ONE matching existing test file when possible. New regression
  cases go into that file; a new suite is not a mandatory deliverable for every
  visual tweak. Tests accompany behavior changes where needed, not as filler.
- Worker runs EXACTLY task.json's check. Do not add full analyze, a full suite,
  multiple related suites, screenshots, coverage or builds by reflex. An extra
  diagnostic may target ONE failing test; do not rerun a passing gate unchanged.
- Flutter check formats changed Dart files, resolves the locked dependencies,
  runs preflight when present, then ONE named test with `--fail-fast --timeout
  30s`. The test process has a 120-second wall limit, including its child
  processes. A passing check remains tied to the exact tested tree.
- Cold SDK/dependency setup is separate and may take longer; report a setup
  blocker instead of pretending tests ran. Non-Flutter check commands retain
  their 300-second command bound. No full-project tests are smuggled into
  preflight. Preflight is not equivalent to behavioral or widget testing.
- No automatic gate bypass, no worker task.json edits, no skipping a failing
  test, no weakening assertions or production behavior to satisfy a test.
  Captain may issue a fresh pinned brief with a cheaper appropriate gate and
  explicitly retain the missing verification before landing. The worker must
  not publish a failed gate as successful.

## Stop debugging loops

- First failure: read the exact error, identify a concrete cause, fix once and
  run the single failing case first. At most TWO corrective attempts for the
  same unresolved failure; after that report BLOCKED immediately with task,
  branch/base, changed files, exact command, first relevant error and remaining
  acceptance items. Preserve local edits. Do not claim PUSHED without publish.
- Any timeout: stop and report; do not immediately rerun or increase the limit.
  Do not spend ten minutes in pumpAndSettle, add arbitrary pump counts, suppress
  exceptions or disable tests. For database-backed widget tests, reuse the
  repo's proven async initialization/teardown, await real completion, and dispose
  stores/databases. Bounded pumping is valid for a known animation, not proof
  that external I/O completed. Fix the cause, not the clock.
- Captain takes over a small blocker rather than sending another relay task.
  If useful work exists only in an unpushed worker tree, request an honest
  blocker report; never imply the Captain can fetch edits that were not pushed.

## Captain integration without duplicate work

- Launch big file-disjoint tasks together; make prerequisites yourself. Never
  idle when an unowned lane exists. Do not invent tasks just to occupy workers.
- Fast-verify the exact branch/base/tip/scope, then start a justified next big
  task before deep review. Do not move live ownership or revise an active task
  silently. New global speed prose does not cancel its pinned acceptance.
- Read the actual diff and check evidence. For a clean file-disjoint integration,
  run preflight and ONE risk-focused integration check. Do not repeat every
  worker test plus analyze plus screenshots plus full tests at each checkpoint.
  Reuse verified evidence only for the same tree/range, SDK and command; a tree
  change affecting it requires fresh evidence. Never trust a report without
  checking its source/diff and remote checkpoint.
- Shared surface is a reason to assess risk, not an automatic full test battery:
  whitespace/docs-only need no full Flutter suite. Run full analyze/full tests
  only for a concrete cross-module risk or the user's explicit request. Explain
  the reason before spending that time. For UI, do ONE focused visual review
  of changed screens, not every language/device permutation on every push.
- Batch-ready CI is dispatched once after local integration. Do not block the
  turn merely watching CI; do useful work or report that CI is pending. Read
  the first failed step/log before fixing and rerunning. Never call pending CI
  successful. Workers never dispatch CI.

## Pairing is separate from speed

Reuse each workspace's saved session, refresh first, resume pending codes.
Never copy credentials to workers or force a new approval on network/config
errors. A fresh workspace needs its own first approval. Authentication refresh
bugs are not fixed by this policy and must be reported honestly.

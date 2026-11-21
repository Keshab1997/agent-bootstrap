# Fast delivery contract — Captain, independent agent and workers

This contract governs work scheduling and check budgets. It does NOT override
scope, pinned task.json, auth, approvals, secret scanning, branch isolation or
verified pushes. It supersedes older prose that asks for extra automatic tests.
Existing in-flight task specs remain unchanged; never silently weaken a gate.

## Start and communicate

- **Default lane: the repo is attached in Arena.** Keshab opens a worker chat
  with the target repo attached and pastes the Captain's one assignment message.
  The worker reads the brief from `docs/agent-briefs/`, edits `allowed` files,
  pushes its own `arena/*` branch, and reports `PUSHED`. No pairing, no
  connector exploration, no `fetch-brief`, no "what does this link mean".
  Device Flow (`worker_lane.py`, `agent/<W>/<task>`) is Option B, only for a
  chat with no attached repo or when the Captain says so.
- Bengali status questions such as “কী হলো”, “kiholo”, “ki holo” mean “what is the
  progress?” Answer with actual progress/blocker, then continue; do not call
  them stray text or ask the user to translate.
- Read the relevant source and existing test setup once. Plan one coherent edit,
  then compile/check it. Avoid repeated blind string replacements and bracket
  repairs. Never fabricate progress, a checkpoint, test evidence or speed gains.
- Report only a useful checkpoint, a real blocker, or a requested status. Do not
  dump internal deliberation or relay a large transcript through the user.

## One worker task, one cheap local check

- Captain chooses ONE matching existing test file when possible. New regression
  cases go into that file; a new suite is not a mandatory deliverable for every
  visual tweak. Tests accompany behavior changes where needed, not as filler.
- Worker runs **one** cheap gate: `python3 tool/preflight.py` (~1 s), or, if the
  repo has none, a single named test file. Do not add full analyze, a full
  suite, multiple related suites, screenshots, coverage or builds by reflex. An
  extra diagnostic may target ONE failing test; do not rerun a passing gate
  unchanged.
- Flutter test: `--fail-fast --timeout 30s`, 120-second wall limit including
  child processes. A passing check stays tied to the exact tested tree.
- Cold SDK/dependency setup is separate and may take longer; report a setup
  blocker instead of pretending tests ran. Non-Flutter commands keep their
  300-second bound. No full-project tests hidden in preflight.
- **The broad gate is CI, and it is the Captain's job.** The worker pushes its
  branch; the Captain dispatches `captain/ci_dispatch.py <repo> --ref <branch>`
  and reads the failing log. Do not make a worker run CI's work locally.
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

## Captain: review fast, run CI, fix the red

- Launch big file-disjoint tasks together; make prerequisites yourself. Never
  idle when an unowned lane exists. Do not invent tasks just to occupy workers.
- On `PUSHED`, verify the exact branch/base/tip/scope quickly, then send that
  worker's next big assignment before deep review. Do not move live ownership
  or revise an active task silently. New global speed prose does not cancel its
  pinned acceptance.
- Review the actual diff, then dispatch ONE CI run on that branch. Read the
  failing step/log; repair small failures yourself in the integration commit
  instead of relaying them back. Workers never dispatch CI.
- Do not repeat every worker test plus analyze plus screenshots plus full tests
  at each checkpoint. Reuse verified evidence only for the same tree/range,
  SDK and command; a tree change affecting it needs fresh evidence.
- Shared surface is a reason to assess risk, not an automatic full local
  battery: whitespace/docs-only need no Flutter suite. CI covers the broad run;
  run a local full analyze/test only for a concrete cross-module risk or when
  Keshab explicitly asks, and explain the reason first.
- Land each checkpoint as soon as CI is green; don't wait for the whole batch.
  Never call pending or red CI successful.

## Pairing (Option B only) is separate from speed

Reuse each workspace's saved session, refresh first, resume pending codes.
Never copy credentials to workers or force a new approval on network/config
errors. A fresh workspace needs its own first approval. Authentication refresh
bugs are not fixed by this policy and must be reported honestly.

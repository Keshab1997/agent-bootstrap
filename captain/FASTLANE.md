# Fast Lane: Captain assigns → worker pushes its branch → Captain runs CI

**Fast delivery:** Read `captain/SPEED_POLICY.md` in agent-bootstrap (or
[SPEED_POLICY.md](SPEED_POLICY.md) from this folder). One cheap local check, one
CI run on the worker's branch, no repeated full suites. Flutter tests fail fast:
30s per test, 120s process wall limit. On timeout report BLOCKED; after two
unsuccessful corrective attempts stop the loop. Preserve
edits and never bypass scope, approvals, secrets or a failed gate.

[বাংলায় শুরু করুন](HOW_TO_START_BN.md) · [Worker starter](WORKER_START_PROMPT.md) · [GitHub briefs](GITHUB_BRIEFS.md) · [Captain playbook](CAPTAIN_PROMPT.md)

There is **one lane**. No pairing, no second mode, no state machine to learn.

```text
Keshab: repo attach করে worker chat খোলে
   ↓
Captain: BRIEF.md + task.json publish করে, একটাই paste-করা message দেয়
   ↓
Worker: brief পড়ে → allowed file edit → cheap check → নিজের arena/* branch-এ commit + push → PUSHED report
   ↓
Captain: branch fetch → diff review → CI চালায় (branch ref) → ঠিক আছে হলে main-এ land; লাল হলে নিজেই fix
```

| Who | Does exactly this | Never |
|---|---|---|
| Keshab | worker chat-এ target repo attach করেন, Captain-এর message paste করেন, `PUSHED` রিপোর্ট Captain-কে দেন | token, file বা পুরো brief টানা-টানি |
| Worker | `git pull --ff-only`, `allowed` file edit, এক cheap check, commit, `git push` নিজের branch-এ, `PUSHED` block | full suite/analyze/build, CI dispatch, `main` push, PR merge/close, task.json edit |
| Captain | brief লেখা, cheap-gate প্রি-ওয়ার্ম, diff review, **CI dispatch + লাল হলে fix**, integration, পরের বড় task | অপেক্ষা করে বসে থাকা, micro-task, একই file দুই worker-কে দেওয়া |

## 1. Worker chat

Keshab শুধু দুটো জিনিস করেন: Arena UI-তে **target repo attach** + Captain-এর
পাঠানো **assignment message** paste। Agent-কে আর কিছু বলতে হয় না।

Worker agent যা করে, ঠিক এই ক্রমে:

```bash
# 1) repo already attached: confirm branch, never switch off it
git branch --show-current          # arena/<...> — এই branch-এই থাকো
git status --short                 # নিজের unsaved কাজ থাকলে আগে জানাও
git pull --ff-only                 # শুধু clean থাকলে; conflict হলে থামো

# 2) brief পড়ো (Captain-এর message-এ path দেওয়া থাকে)
cat docs/agent-briefs/<batch>/<task>/BRIEF.md
cat docs/agent-briefs/<batch>/<task>/task.json   # allowed list = তোমার সীমা

# 3) allowed file-গুলো edit করে cheap check
python3 tool/preflight.py          # ~1s; না থাকলে task.json-এর একটাই test

# 4) One commit, push your branch (arena/*; never main)
git add -- <allowed files only>
git commit -m "<task.json-এর commit message>"
git push origin HEAD
```

`tool/preflight.py` নেই? তবে শুধু **এক** টার্গেটেড test:
`flutter test --no-pub --fail-fast <task.json-এর test>` (30s per test, 120s wall)।
Build (`flutter build`, `gradlew`), `flutter analyze`, full suite কখনো নয়।
Timeout হলে থামো, rerun নয়।

তারপর chat-এ ঠিক এই block দাও:

```text
AGENT <W> PUSHED
repo: Keshab1997/<repo>
task: <task-id>
branch: <arena/...>
sha: <full 40-char commit>
files: <allowed paths touched>
check: preflight passed | <one test> passed
```

Push না হলে: `AGENT <W> BLOCKED` + exact reason + কী কী edit পড়ে আছে।
কোনো ফল নেই এমন "PUSHED" কখনো নয়।

## 2. Captain per checkpoint

1. **Review the range, not the whole branch:** `git fetch origin <arena/...>`
   → `git diff --name-status $base..$tip` must equal the `allowed` list, no
   secrets, no version bumps, then read the diff (`git diff $base..$tip`).
2. **CI on the worker branch** (a push alone does not run it):

   ```bash
   python3 captain/ci_dispatch.py Keshab1997/<repo> --ref <arena/...> --watch 900 --logs
   ```

   `--watch` লম্বা হলে background process-এ চালাও, আর কাজ চালিয়ে যাও।
   Workers CI কখনো dispatch করে না।
3. **লাল হলে:** প্রথম failing step/log পড়ো (`--logs` ওটাই দেয়), তারপর —
   - ছোট/স্পষ্ট ভুল (typo, import, formatting, একটা assertion): **Captain নিজেই**
     নিজের integration commit-এ ঠিক করে land করে।
   - worker-এর কাজের ধরন বদলাতে হবে: **একটাই** corrective task, ভেতরে exact
     failing step, log-এর প্রথম ২০ লাইন আর বাকি acceptance item দিয়ে।
     নতুন task ID; পুরোনোটা supersede করো, silently বদলিও না।
4. **সবুজ হলে:** reviewed diff `main`-এ land করো (§3), ledger-এ
   `checkpoint --status landed`।
5. **পরের বড় task সঙ্গে সঙ্গে publish করো** (worker অপেক্ষা করবে না):

| পরের task কীসের উপর | task.json-এ |
|---|---|
| `main`-এ আগের কাজ land হয়ে গেছে | `"arena": {"branch": "auto", "base_sha": null}` |
| আগের checkpoint এখনো merge হয়নি, একই worker-এর lane | `"arena": {"branch": "auto", "base_sha": "<verified tip>"}` |
| অন্য worker-এর unmerged কাজ দরকার | **করো না** — আগে সেটা land করো, বা নিজে prerequisite লিখে দাও |

## 3. Land the reviewed diff

```bash
set -euo pipefail
test -z "$(git status --porcelain)"
git switch main && git pull --ff-only origin main
git switch -c "captain/review/<slug>"
git diff --binary --full-index --no-ext-diff --no-textconv "$base" "$tip" -- | git apply --3way --index
git diff --cached --check
git diff --cached                # read it once more
python3 tool/preflight.py        # repo's own cheap gate
git commit -m "fix(scope): reviewed worker change"
git switch main && git merge --ff-only captain/review/<slug> && git push origin HEAD:refs/heads/main
```

Branch rules থাকলে PR খোলো; conflict হলে জোর করো না। `arena/*` branch মুছো না —
worker chat সেটার উপরেই চলছে।

## 4. Ledger: one line per checkpoint

`python3 captain/ledger.py upsert …` at assignment, `checkpoint …` on
verify/land (gitignored `captain/LEDGER.json`, schema in [LEDGER.md](LEDGER.md)).
`python3 captain/batch_status.py` এক কলে ledger vs live `arena/*` tips, tracker
mentions আর CI runs দেখায় — "কী হলো" প্রশ্নের সবচেয়ে দ্রুত উত্তর।

Brief লেখার আগে `python3 captain/task_spec.py <task.json>` দিয়ে scope যাচাই
করো; ভুল path, shared surface বা secret-ওয়ালা path ধরা পড়বে।

## 5. Finalize only when explicitly asked

**`Finalize batch <id>`** — Captain সিদ্ধান্ত, worker command নয়। নতুন assignment
বন্ধ, প্রতিটা checkpoint verified/blocked কিনা দেখাও, কী landed আর কী বাকি এক
টেবিলে দাও। merging না হয়ে থাকা reviewed কাজ Captain-এর PR-এ শেষ করো।

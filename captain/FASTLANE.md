# Fast Lane: Captain assigns → worker pushes its branch → Captain runs CI

**Fast delivery:** Read `captain/SPEED_POLICY.md` in agent-bootstrap (or
[SPEED_POLICY.md](SPEED_POLICY.md) from this folder). One cheap local check, one
CI run on the worker's branch, no repeated full suites. On timeout report
BLOCKED; after two unsuccessful corrective attempts stop the loop. Preserve
edits and never bypass scope, approvals, secrets or a failed gate.

[বাংলায় শুরু করুন](HOW_TO_START_BN.md) · [Worker starter](WORKER_START_PROMPT.md) · [GitHub briefs](GITHUB_BRIEFS.md) · [Captain playbook](CAPTAIN_PROMPT.md)

## The default flow (Lane A — Arena-attached)

This is the normal way to work. Four steps, no state machine:

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
| Worker | `git pull --ff-only`, `allowed` file edit, `python3 tool/preflight.py`, commit, `git push` নিজের branch-এ, `PUSHED` block | full suite/analyze/build, CI dispatch, `main` push, PR merge/close, task.json edit |
| Captain | brief লেখা, cheap-gate প্রি-ওয়ার্ম, diff review, **CI dispatch + লাল হলে fix**, integration, পরের বড় task | অপেক্ষা করে বসে থাকা, micro-task, একই file দুই worker-কে দেওয়া |

Worker-এর আর কোনো ceremony নেই: `fetch-brief`, `start`, `check`, `publish`,
`mention` — এগুলোর দরকার নেই, কারণ repo-টা chat-এই attach করা আছে এবং
push-টা Arena-র নিজের branch-এ যায়। `worker_lane.py` শুধু **Option B**-তে লাগে।

## 1. Worker chat (Lane A)

Keshab শুধু দুটো জিনিস করেন: Arena UI-তে **target repo attach** + Captain-এর
পাঠানো **assignment message** paste। Agent-কে আর কিছু বলতে হয় না।

Worker agent যা করে, ঠিক এই ক্রমে:

```bash
# 1) repo already attached: confirm branch, never switch off it
git branch --show-current          # arena/<...> — এই branch-এই থাকো
git status --short                 # নিজের unsaved কাজ থাকলে আগে জানাও
git pull --ff-only                 # শুধু clean থাকলে; conflict হলে থামো

# 2) brief পড়ো (Captain-এর message-এ path/লিংক দেওয়া থাকে)
cat docs/agent-briefs/<batch>/<task>/BRIEF.md
cat docs/agent-briefs/<batch>/<task>/task.json   # allowed list = তোমার সীমা

# 3) allowed file-গুলো edit করে cheap check
python3 tool/preflight.py          # ~1s; tool/preflight.py না থাকলে নিচের ছক দেখো

# 4) One commit, push your branch (arena/*; never main)
git add -- <allowed files only>
git commit -m "<task.json-এর commit message>"
git push origin HEAD                # arena/* branch; main-এ কখনো নয়
```

`tool/preflight.py` নেই? তবে শুধু **এক** টার্গেটেড test:
`flutter test --no-pub --fail-fast <test.json-এর test>` (৩০s/কেস, ১২০s wall)।
Build (`flutter build`, `gradlew`) কখনো নয়। Timeout হলে থামো, rerun নয়।

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
   → verify `base..tip` touches only `allowed` files, no secrets
   (`worker_lane.py review` এই যাচাইটা করে, Arena lane-এ `--checkout` ছাড়াই
   ব্যবহার করা যায় না — তাই plain `git diff` + checklist যথেষ্ট)।
2. **CI on the worker branch** (a push alone does not run it):

   ```bash
   python3 captain/ci_dispatch.py Keshab1997/<repo> --ref <arena/...> --watch 900
   ```

   `--watch` লম্বা হলে background process-এ চালাও, আর কাজ চালিয়ে যাও।
   Workers CI কখনো dispatch করে না।
3. **লাল হলে:** প্রথম failing step/log পড়ো, তারপর —
   - ছোট/স্পষ্ট ভুল (typo, import, formatting, একটা assertion): **Captain নিজেই**
     নিজের integration commit-এ ঠিক করে land করে।
   - worker-এর কাজের ধরন বদলাতে হবে: **একটাই** corrective task, ভেতরে exact
     failing step, log-এর প্রথম ২০ লাইন আর বাকি acceptance item দিয়ে।
     নতুন task ID; পুরোনোটা supersede করো, silently বদলিও না।
4. **সবুজ হলে:** reviewed diff `main`-এ land করো (direct push authorized হলে
   fast-forward; নাহলে Captain PR), ledger-এ `checkpoint --status landed`।
5. **পরের বড় task সঙ্গে সঙ্গে publish করো** (worker অপেক্ষা করবে না)। নিচের
   ছক দেখে `base_sha` ঠিক করো:

| পরের task কীসের উপর | task.json-এ |
|---|---|
| `main`-এ আগের কাজ land হয়ে গেছে | `"arena": {"branch": "auto", "base_sha": null}` |
| আগের checkpoint এখনো merge হয়নি, একই worker-এর lane | `"arena": {"branch": "auto", "base_sha": "<verified tip>"}` |
| অন্য worker-এর unmerged কাজ দরকার | **করো না** — আগে সেটা land করো, বা নিজে prerequisite লিখে দাও |

## 3. Option B — Device Flow (repo attach নেই)

কোনো chat-এ repo attach করতে না চাইলে এটাই ব্যাকআপ পথ। তখন worker নিজে
`gh_app.py connect` দিয়ে pair হয়, brief GitHub থেকে নামায়, আর
`worker_lane.py` state machine-এ `agent/<W>/<task>` branch push করে:

```bash
bash worker_up.sh                     # clone/pair/status/pull/guide, এক command
lane=/home/user/agent-bootstrap/captain/worker_lane.py
python3 -B "$lane" fetch-brief --url "<BRIEF_URL>" --worker <A|B|C>   # prints task_json path
task=~/agent-workbench/inbox/<...>/task.json
python3 -B "$lane" start   "$task"    # isolated clone ~/agent-workbench/repos/<W>/<repo>
python3 -B "$lane" check   "$task"    # preflight | pinned Flutter test | pytest | selftest
python3 -B "$lane" diff    "$task"    # read the whole diff yourself
python3 -B "$lane" publish "$task"    # commit + push + remote verify → PUSHED
```

`mention` শুধু approved tracker issue থাকলে। Pinned brief কীভাবে নামায় আর
`--checkout` কখন লাগে: [GitHub briefs](GITHUB_BRIEFS.md#2-worker-fetch-the-pinned-brief)।

Arena lane-এ `worker_lane.py` লাগে না, কিন্তু কেউ চাইলে
`--checkout "$PWD"` দিয়ে `review`-এর মতো যাচাই চালাতে পারে।

## Check profiles (Option B)

| `check` value | Runs |
|---|---|
| `{"kind":"preflight"}` | `python3 -B tool/preflight.py`; suitable only when it covers the task |
| `{"kind":"flutter","version":"3.50.0","test":"test/home_screen_test.dart"}` | Exact SDK, locked pub get, changed-file format, preflight, then ONE test file with `--fail-fast --timeout 30s`; 120s test-process wall limit |
| `{"kind":"pytest","target":"tests"}` | `python3 -m pytest -q tests` (or one named Python test under `test/` or `tests/`) |
| `{"kind":"selftest"}` | `python3 -B selftest.py` |

Use the actual repo's gate. The Flutter version shown is an example, **not** a
global default. The lockfile must not change. No builds or full test battery.

## 4. Ledger: one line per checkpoint

`python3 captain/ledger.py upsert …` at assignment, `checkpoint …` on
verify/land (gitignored `captain/LEDGER.json`, schema in [LEDGER.md](LEDGER.md)).
`python3 captain/batch_status.py` এক কলে ledger vs live `arena/*` + `agent/*`
tips, tracker mentions আর CI runs দেখায় — "কী হলো" প্রশ্নের সবচেয়ে দ্রুত উত্তর।

## 5. Finalize only when explicitly asked

**`Finalize batch <id>`** — Captain সিদ্ধান্ত, worker command নয়। নতুন assignment
বন্ধ, প্রতিটা checkpoint verified/blocked কিনা দেখাও, কী landed আর কী বাকি এক
টেবিলে দাও। merging না হয়ে থাকা reviewed কাজ Captain-এর PR-এ শেষ করো।

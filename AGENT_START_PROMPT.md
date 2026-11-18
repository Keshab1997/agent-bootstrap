# New-agent start prompt — Keshab1997

**এটা কোন agent-কে দেবেন:** যে agent আপনার repo-তে কাজ করবে (নতুন session, নতুন sandbox)।
নিচের দুই ✂ লাইনের মাঝের পুরোটাই copy করে ওকে দিন। শেষের বাংলা অংশটা শুধু আপনার জন্য।

✂ ═══════════════════════ COPY FROM HERE ═══════════════════════ ✂

# You are joining Keshab1997's workspace. Move fast.

Everything below is the whole onboarding. Read it once, then work. **Speed is
the point**: never wait on CI, never run a check the change does not need.

## 0. Check your role and current branch first

If this is a Captain A/B/C assignment, require the **target repo attached in
Arena Agent Mode**. Use the Captain's pinned GitHub `BRIEF.md` link and
`captain/FASTLANE.md` in a separate verified `Keshab1997/agent-bootstrap`
clone. Read `BRIEF.md` and `task.json` at the same commit. Keep the actual
`arena/*` branch and native Arena auth. Missing/wrong repo, missing pin, or
a terminal linked PR means `BLOCKED`, not a clone or new pairing.

For a Captain task, follow only Fast Lane, not the single-agent setup below.
After verifying your checkpoint, mention `@Keshab1997` on the approved
tracking issue, or report `MENTION PENDING` in Arena when you cannot comment.
Do not merge or close the linked PR. The remaining direct-to-main instructions
apply only to independent work explicitly assigned to `main`.

## 1. Restore GitHub access — approve only when recovery is not possible

Skip this pairing setup if the task can use the workspace’s existing Git access.
Captain workers use only the attached repo’s existing Arena access.

```bash
DST=/home/user/agent-bootstrap   # keep the session in this workspace between turns
[ -f "$DST/gh_app.py" ] || git clone https://github.com/Keshab1997/agent-bootstrap "$DST"
python3 "$DST/gh_app.py" connect   # reuse token -> refresh -> reuse pending code
```

| What it printed | What you do |
|---|---|
| `ALREADY CONNECTED -- device flow skipped` | Ask nothing; start working. An expired access token may have been refreshed automatically. |
| A code like `XXXX-XXXX` | Show: *"Open https://github.com/login/device and enter XXXX-XXXX"*. The human approves; never ask for a token or password. |
| `NOT starting a device flow` / `UNCONFIRMED` | Retry later. A network/rate-limit/server error is not a reason to re-authorize. |

- Never re-pair "to be safe", copy another agent's `secrets/`, or use `--force`
  just because the access token expired. `connect` tries the saved refresh first.
- The pending code is saved **before** it is printed. If polling is interrupted,
  resume the same code in a later turn (no `start` step needed):

  ```bash
  python3 /home/user/agent-bootstrap/device_pair.py poll 60
  ```

  Rerunning `connect` also resumes it. A poll budget ending is not code expiry;
  keep polling while it remains valid. For an agent-friendly nonblocking start,
  `connect --show-only` saves/reuses the code and exits immediately.
- `python3 "$DST/gh_app.py" status` checks/recovers without opening a device flow.
  Exit 0 / `PAIRED` means authenticated. Exit 1 may mean a temporary network
  problem; let `connect` decide whether a new approval is actually necessary.
- `/home/user/agent-bootstrap/secrets/` persists in **this workspace**, not every
  new chat/sandbox. An entirely fresh captain workspace still needs approval.
  Reuse your own saved login for independent work across batches. Never share
  tokens or copy them to linked workers; their Arena access is separate.

## 2. Flutter SDK — only for Dart work (Fast Lane runs its own pinned gate)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) \
  --root /var/tmp/flutter --quiet --json
export PATH=/var/tmp/flutter/bin:$PATH PUB_CACHE=/var/tmp/pub-cache
```

Use the repo’s compatible SDK version and keep checked-in lockfiles unchanged.
`/var/tmp` and `~/.cache` are not in the saved workspace snapshot; reuse a warm
SDK when present, but do not rely on it surviving a fresh sandbox.

## 3. Get the repo — and obey its law

If Keshab did not name the repo, ask (or run `python3 gh_app.py repos
--limit 30`). Flutter apps in the account: **docify, keepit, SpeakEasy,
quizbaaz, prescription-scanner, AI-Image-Scan**.

Clone `Keshab1997/<repo>`, then **read its `AGENTS.md` completely before
editing**. The managed block already carries the policy in §4; the notes below
that block are Keshab's own — never delete them.

## 4. The check policy — exactly this, nothing more

| The change | The check |
|---|---|
| anything | `python3 tool/preflight.py` (~1 s) |
| a Dart edit | `flutter test test/<name>_test.dart` — that one file |
| shared surface / risky diff / Keshab asks | `flutter analyze` + full `flutter test` |

- **Never** `flutter build apk|aab|web` or `gradlew` locally "just to check".
- **Never** rerun the full battery after a small edit. If a check takes
  minutes, it belongs to CI — push and move on.

## 5. CI is manual — Keshab's button, not yours

The manual Flutter CI is Keshab's to start; repo-specific previews may still
run on branch pushes. Do **not** wait on CI. Commit on the authorized task
branch. When a standalone `main` batch is done, tell him:
*"batch ready — Actions → Flutter CI → Run workflow"*. Read the
result with `python3 tool/ci_watch.py`. If a run is red: **read the failing
log first**, then fix.

## 6. Working rules

- Only for standalone work assigned straight to `main`, use
  `python3 tool/agent_loop.py -m "feat(scope): what changed"` for preflight,
  secret guard, commit and push. Captain workers never use that shortcut:
  push only the brief's real task branch, no PR or CI dispatch.
- Conventional commits: `feat(update): …`, `fix(auth): …`, `chore(ci): …`.
- Secrets never enter git (`*.jks`, `*.keystore`, `key.properties`,
  `google-services.json`, any token). CI receives them from repo secrets.
- **Ask Keshab first** for: tags/releases, workflow / secret / settings
  changes, and anything public or irreversible. Everything else — just do it.

## 7. Sandbox traps — know them, skip the slow paths

- A clone suddenly says *"not a git repository"* → `.git/config` was dropped
  between turns. Reattach it (do **not** re-clone):
  ```bash
  git remote add origin https://github.com/Keshab1997/<repo>.git
  git config core.fileMode false
  git config user.name "Keshab Sarkar"
  git config user.email "Keshab1997@users.noreply.github.com"
  git config credential.helper '!f(){ echo username=x-access-token; echo "password=$(cat /home/user/agent-bootstrap/secrets/gh_token.txt)"; }; f'
  ```
- Exec-bit noise on `gradlew` / `*.jar` files → fixed by `core.fileMode false`.
- `raw.githubusercontent.com` can serve a **stale file for ~5 minutes** after a
  push. Trust the API (`python3 gh_app.py api GET …`) or the local clone.
- **Cloned agent-bootstrap into the wrong place?** `git clone … && cd agent-bootstrap`
  inside a fresh shell lands in `/var/tmp/...` or `/tmp/...` — those are wiped
  between turns, so `secrets/gh_token.txt` disappears and you look unpaired after
  every turn. Always `/home/user/agent-bootstrap`, one clone per sandbox.
- Token expired? Run `connect`: it refreshes first. Show a code only if it
  actually prints one; a temporary error is a retry, not a fresh pairing.

## 8. "Done" looks like

Small focused commits on the authorized branch with local SHA == remote SHA;
checks matched to the change; manual CI only if Keshab dispatches it. A Captain
worker reports the verified `PUSHED` block and pinned brief link on the
approved tracker, or uses `MENTION PENDING` in Arena if unable to comment.
When code has not pushed, report `BLOCKED` with the reason, not done.

✂ ═══════════════════════ COPY ENDS HERE ═══════════════════════ ✂

---

## Working with other agents — captain mode

If Keshab hands you **`CAPTAIN_START_PROMPT.md`** instead of this file, you are the
**captain**: publish task briefs in the target repo's GitHub docs, then send
pinned links to workers with that repo attached in Arena. Workers checkpoint
their real `arena/*` branch. The Captain reviews the exact range and owns
integration. No file handoff and no linked PR merge/close per task. See the
[Captain playbook](captain/CAPTAIN_PROMPT.md) and [GitHub briefs](captain/GITHUB_BRIEFS.md).

---

## সংক্ষিপ্ত version (চ্যাটে দ্রুত paste করার জন্য)

> Captain task হলে Arena-তে কাজের repo attach করো। Captain-এর pinned GitHub brief
> আর একই commit-এর `task.json` পড়ে `captain/FASTLANE.md` মেনে আসল `arena/*` branch-এ
> push করো। Repo attach না থাকলে `BLOCKED`। Push যাচাই হলে অনুমোদিত issue-তে
> `@Keshab1997` mention, না পারলে `MENTION PENDING`। PR merge/close কোরো না।
> আলাদা single-agent কাজে `AGENTS.md` পড়ো; `main` শুধু স্পষ্ট অনুমতি পেলে।
> Saved login থাকলে আবার approval চাইবে না। **CI আমি চালাবো** — অপেক্ষা কোরো না।

---

## বাংলা — এই prompt-এ কী কী আছে আর কেন

**পুরোনো prompt-এর সমস্যা ছিল:** (১) প্রতিটা ছোট কাজেও "pub get + analyze +
full test" — সময় শেষ; (২) CI কে চালাবে, কতবার, অপেক্ষা করবে কিনা — কিছুই লেখা
ছিল না; (৩) sandbox-এর ফাঁদগুলো (SDK মুছে যাওয়া, `.git/config` হারানো) প্রতিবার
নতুন করে আবিষ্কার করতে হতো।

**নতুন prompt-এ যা ঠিক করা হয়েছে:**

| আগে | এখন |
|---|---|
| সব change-এ analyze + full test | preflight (~১ সে.) সবসময়; Dart edit-এ শুধু একটা test ফাইল |
| CI-র কথা লেখাই নেই | স্পষ্ট: CI manual, **agent অপেক্ষা করবে না**, আপনি একবার চালাবেন |
| `<repo>` ফাঁকা placeholder | repo জিজ্ঞেস করবে + account-এর app-দের নাম দেওয়া আছে |
| environment-এর ফাঁদ অজানা | তিনটা ফাঁদ আগেই লেখা — প্রথমবারেই সঠিক পথ নেবে |
| "সব করতে হবে" অস্পষ্ট | "Done" কী দেখতে হয় — পরিষ্কার |

**ব্যবহারের নিয়ম:** উপরের দুই ✂ লাইনের মাঝের অংশটা copy করে নতুন agent-কে
দিন। ও নিজে থেকে pairing-এর code দেখাবে, আপনার approval নেবে, তারপর দ্রুত
কাজ শুরু করবে — mাঝে মাঝে জিজ্ঞেস করার দরকার নেই, শুধু tag/release/secret-এর
আগে অনুমতি চাইবে।

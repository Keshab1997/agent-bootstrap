# New-agent start prompt — Keshab1997

**এটা কোন agent-কে দেবেন:** যে agent আপনার repo-তে কাজ করবে (নতুন session, নতুন sandbox)।
নিচের দুই ✂ লাইনের মাঝের পুরোটাই copy করে ওকে দিন। শেষের বাংলা অংশটা শুধু আপনার জন্য।

✂ ═══════════════════════ COPY FROM HERE ═══════════════════════ ✂

# You are joining Keshab1997's workspace. Move fast.

Everything below is the whole onboarding. Read it once, then work. **Speed is
the point**: never wait on CI, never run a check the change does not need.

## 1. Pair with GitHub — once per session, and only if you are not already paired

```bash
DST=/home/user/agent-bootstrap   # /home/user is the ONLY path that survives turns
[ -f "$DST/gh_app.py" ] || git clone https://github.com/Keshab1997/agent-bootstrap "$DST"
python3 "$DST/gh_app.py" connect   # safe to run: it skips itself if already paired
```

**Read its output, then behave accordingly — this is the whole trick:**

| What it printed | What you do |
|---|---|
| `ALREADY CONNECTED -- device flow skipped` | You are paired. Show nothing, ask nothing. Start working. |
| A code like `XXXX-XXXX` | **Show it as a headline, not fine print:** *"Open https://github.com/login/device and enter XXXX-XXXX"*. He approves in his browser; the script polls and finishes on its own. Never ask him for a token or a password — ever. |

- **Never re-pair "to be safe".** Asking him to authorize a session that is
  already authorized is the #1 complaint about agents in this workspace.
  The token is at `/home/user/agent-bootstrap/secrets/gh_token.txt` (~8 h,
  auto-refreshes). Never print it in full. `connect --force` exists only for a
  genuinely dead token.
- **If his approval arrives after your turn ended** (the poll gets cut off),
  the code is still valid ~15 min — do **not** mint a new one. Use the
  resumable helper, which keeps the pending code in `secrets/device_state.json`:

  ```bash
  python3 /home/user/agent-bootstrap/device_pair.py start      # same code, saved
  python3 /home/user/agent-bootstrap/device_pair.py poll 60    # resume in a later turn
  ```

  Repeat `poll 60` until it prints `APPROVED`; start a new code only if it says
  `EXPIRED`. (`connect` alone cannot do this — its poll dies with the turn.)
- Verify with `python3 "$DST/gh_app.py" status` → `verdict: PAIRED`
  (exit code 0 = paired, 1 = not paired, so `status || connect` also works) or
  `python3 "$DST/gh_app.py" whoami`.

## 2. Flutter SDK — only when Dart work is coming (~50 s; skip for docs/YAML)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) \
  --root /var/tmp/flutter --quiet --json
export PATH=/var/tmp/flutter/bin:$PATH PUB_CACHE=/var/tmp/pub-cache
```

Sandbox fact: only `/home/user` survives between tool calls; `/var/tmp` and
`~/.cache` are wiped between turns. A 50-second reinstall is normal — not a
problem to solve.

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

Nothing runs on a push. Do **not** wait for a run after pushing your work.
Push to `main` directly, commit often, batch freely. When a batch is done,
tell him: *"batch ready — Actions → Flutter CI → Run workflow"*. Read the
result with `python3 tool/ci_watch.py`. If a run is red: **read the failing
log first**, then fix.

## 6. Working rules

- Push straight to `main` — no branches, no PRs.
  `python3 tool/agent_loop.py -m "feat(scope): what changed"` = preflight +
  secret guard + commit + push, one call.
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
- Token expired (`HTTP 401` from `status`)? Get a fresh code — but only after
  checking `status` shows `NOT WORKING`, and show the code to him.

## 8. "Done" looks like

Small focused commits on `main`, local sha == remote sha; checks matched to
the change (never the full battery by reflex); at most one CI run — dispatched
by Keshab, never waited on by you; and a short report: **what changed, the
evidence, what you deliberately did not touch**.

✂ ═══════════════════════ COPY ENDS HERE ═══════════════════════ ✂

---

## Working with other agents — captain mode

If Keshab hands you **`CAPTAIN_START_PROMPT.md`** instead of this file, you are the
**captain**: you split the work into worker briefs, the workers push their own
`agent/A|B|C/<slug>` branches, and you review, fix, merge and report. Your playbook
is `captain/CAPTAIN_PROMPT.md` in this same clone; the brief template is
`captain/WORKER_BRIEF_TEMPLATE.md`.

---

## সংক্ষিপ্ত version (চ্যাটে দ্রুত paste করার জন্য)

> Clone Keshab1997/agent-bootstrap → **`/home/user/agent-bootstrap`** → আমারApproval
> দরকার হলে code দেখাও, নইলে `ALREADY CONNECTED` পেলে নতুন করে authorize চেয়ো না।
> Dart work শুরু করলে Flutter SDK (flutter-bootstrap,
> `/var/tmp/flutter`)। তারপর যে repo বলব তার `AGENTS.md` পড়ে সেটাই follow করো:
> সব change-এ `preflight.py`; Dart edit-এ শুধু সংশ্লিষ্ট test ফাইল; `analyze` +
> full test শুধু দরকারে বা আমি বললে। সরাসরি `main`-এ push করো, **কখনো CI-র জন্য
> অপেক্ষা কোরো না** — CI আমি manual চালাবো।

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

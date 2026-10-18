# agent-bootstrap

**A zero-secret GitHub connector for AI agents.**

Clone this repo — no credentials needed, it is public on purpose — and any AI
agent can pair with **Keshab1997**'s GitHub in one step instead of ten.

```bash
git clone https://github.com/Keshab1997/agent-bootstrap.git /home/user/agent-bootstrap
python3 /home/user/agent-bootstrap/gh_app.py connect   # prints an XXXX-XXXX code
```

Read the code to the human, they tap *Authorize* in a browser, and ~10 seconds
later the agent has a working GitHub token. No secrets are ever stored here.

Or, as a true one-liner from anywhere:

```bash
curl -fsSL https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/setup.sh | bash
```

> 🇧🇩 **বাংলায় ধাপে ধাপে গাইড:** [`NEXT_TIME_BANGLA.md`](NEXT_TIME_BANGLA.md) —
> পরেরবার কী লিখতে হবে, কয়টা ক্লিক লাগবে, টোকেন কতদিন চলবে, আর সমস্যা হলে
> কী করবেন, সব এক জায়গায়। (Human-readable; agents can ignore it.)

---

## For AI agents — read this first

These steps are for a captain or standalone agent that needs authenticated
access. **Public-repo patch workers skip pairing** and follow their no-login
brief instead.

1. **Run** `python3 gh_app.py connect`. It first reuses a working token, then
   tries the saved refresh token if access expired. Successful recovery prints
   `ALREADY CONNECTED -- device flow skipped`: **ask the human nothing**.
   A network/rate-limit/server error means retry, not a new approval. Only an
   absent session or a definitely rejected refresh token leads to pairing.
2. **Only if it printed a code**, tell the human, verbatim and prominently:
   > Open <https://github.com/login/device> and enter the code **XXXX-XXXX**
3. **Wait.** The script polls every 5 s and finishes on its own. Do not ask for
   a token, a password, a PAT, or any secret — the human only approves in the
   browser.
4. **Verify** with `python3 gh_app.py whoami`
5. The token is now in `secrets/gh_token.txt` (`chmod 600`). Use
   `python3 gh_app.py api <METHOD> <PATH>` for any REST call, or read that file
   and set `Authorization: Bearer <token>`.

   **If the task is Flutter/Dart work**, this sandbox has no Flutter SDK — get
   one in ~40 s from the companion repo (see *Flutter projects* below):

   ```bash
   bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) --quiet --json
   ```

**Rules**

- Never print a full token to logs or chat. `gh_app.py` masks it for you.
- Never commit anything under `secrets/` (already git-ignored).
- Access tokens last **8 hours**. API commands refresh near expiry; `connect`
  and `status` also recover an already-expired access token from the saved
  refresh token. Do not use `--force` merely because eight hours passed.
- `status` never starts a device flow. `PAIRED` means API authentication worked;
  `UNCONFIRMED` means retry later, not re-authorize; `NOT PAIRED` means run
  `connect`. Exit 1 alone is **not** proof that credentials are dead.
- `connect`, `connect --show-only`, and `device_pair.py start` share one pending
  code in `secrets/device_state.json`, saved **before** it is displayed. After
  an interrupted turn, use `python3 device_pair.py poll 60` or rerun `connect`.
  Both reuse the same unexpired code; neither extends its original ~15-minute
  lifetime. A bounded poll timeout keeps the code and GitHub's retry interval.
- One saved session per sandbox: keep the clone at `/home/user/agent-bootstrap`.
  Files here survive turns **in this workspace**; an entirely new workspace
  has no credentials and still needs its own approval. Never copy `secrets/`
  to another agent to work around this.

**Already have an older clone?** From a clean checkout, run `git pull --ff-only`
inside `/home/user/agent-bootstrap` once, then `python3 gh_app.py connect`.
Keep local edits if the update refuses; do not reset the repo or delete secrets.
No new PAT, private key, server or repository setting is needed for this update.

---

## Multiple agents — only the captain logs in by default

Start with [`CAPTAIN_START_PROMPT.md`](CAPTAIN_START_PROMPT.md). The captain
restores access and reads [`captain/CAPTAIN_PROMPT.md`](captain/CAPTAIN_PROMPT.md).
For a **verified public repo**, workers receive a frozen-base
[`patch brief`](captain/WORKER_PATCH_BRIEF_TEMPLATE.md), clone without login,
work on local branches and return `.patch` files plus checksums. **No worker
OAuth approval or push.** Keshab attaches the actual files/reports to the
captain's chat; the captain reviews → checks → integrates → pushes `main`.
A path in another chat's sandbox is not a usable attachment.

Private repos or unsuitable attachment handoffs can use explicit authenticated
[branch mode](captain/WORKER_BRIEF_TEMPLATE.md), with a separate worker pairing
if needed. The captain explains that tradeoff first. No source is made public
and no credentials are shared to avoid approval. An entirely new captain
workspace still requires its first approval; this is not cross-sandbox SSO.

Bengali walk-through: [`captain/HOW_TO_START_BN.md`](captain/HOW_TO_START_BN.md).
The playbook ships in the repo, so future fresh clones receive the updated rules.

---

## Starting a fresh agent — one paste

When a new agent session starts, hand it [`AGENT_START_PROMPT.md`](AGENT_START_PROMPT.md):
pairing, the Flutter SDK step, the check-when-needed policy, the manual-CI rule
and the sandbox's traps, all in one copy-paste block. A plain-text twin
([`PROMPT-FOR-NEW-AGENT.txt`](PROMPT-FOR-NEW-AGENT.txt)) and a one-click-copy
page ([`AGENT_PROMPT_COPY.html`](AGENT_PROMPT_COPY.html)) carry the same text.

---

## What you get

| | |
|---|---|
| Account | [Keshab1997](https://github.com/Keshab1997) — Keshab Sarkar |
| GitHub App | `keshab-flutter-assistant` (App ID `4611920`) |
| Client ID | `Iv23lieh6Kastc59yOsf` — *not a secret for GitHub Apps* |
| Installation | `154119208`, **all** repositories |
| Token type | `ghu_…` user access token, 8 h, refreshable for 181 days |
| Rate limit | 5000 requests/hour |
| Permissions | write: contents, workflows, actions, pull_requests, issues, discussions, deployments, environments, merge_queues, checks, pages, packages, administration, secrets… · read: metadata, projects |

That is effectively full control of every repository on the account: pushing
code, opening and merging PRs, editing Actions workflows, writing secrets.
Use it carefully and only for what you were asked to do.

Full machine-readable details: [`app-meta.json`](app-meta.json)

---

## Commands

```bash
python3 gh_app.py connect              # reuse -> refresh -> resume -> pair only if needed
python3 gh_app.py connect --force      # pair again on purpose (new code)
python3 gh_app.py status               # check/recover; never opens a flow; exit 0 = paired
python3 device_pair.py status          # is a device code already pending?
python3 gh_app.py connect --show-only  # save/reuse a code and exit (agent-friendly)
python3 device_pair.py start           # same guard and saved code as connect --show-only
python3 device_pair.py poll 60         # resume polling a saved code
python3 gh_app.py whoami
python3 gh_app.py repos --limit 20
python3 gh_app.py installations        # the App's granted permissions
python3 gh_app.py api GET  /user/repos
python3 gh_app.py api POST /repos/Keshab1997/keepit/issues \
        --data '{"title":"from an agent","body":"hello"}'
python3 gh_app.py env                  # export GITHUB_TOKEN=...
python3 gh_app.py refresh              # force rotation
python3 gh_app.py revoke               # disconnect + wipe local tokens
python3 gh_app.py installation-token --key path/to/app.pem
```

Requirements: **python3 ≥ 3.8 only.** Standard library, no `pip install`.
`openssl` is used solely for the optional installation-token JWT.

---

## Flutter projects — one more command

Pairing with `gh_app.py` gives you GitHub access. It does **not** give you a
Flutter SDK, because a sandbox starts empty and anything installed outside the
workspace disappears next session. The companion repo
[`flutter-bootstrap`](https://github.com/Keshab1997/flutter-bootstrap) installs
one in ~40 seconds, sha256-verified, with no credentials involved:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Keshab1997/flutter-bootstrap/main/setup.sh) --quiet --json
```

**Or do both at once** — connect to GitHub *and* install Flutter in a single
command:

```bash
curl -fsSL https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/setup.sh \
  | bash -s -- --with-flutter
```

`--with-flutter` simply chains the companion installer after the token step
(it is skipped if you are already connected). GitHub access is kept even if the
Flutter download fails, and the flag is never needed for non-Flutter work — the
SDK is 2.5 GB, so it stays opt-in.

| | |
|---|---|
| Install root | auto-picked by the installer, normally `/var/tmp/flutter` |
| Cold install | ~40 s (1.5 GB download, verified against the official manifest) |
| Later shells | plain `flutter …` works — no PATH setup |
| Verified on a real app | `flutter analyze` clean, 200 tests passing |

---

## The one thing this cannot do

An **installation token** (`ghs_…`) needs the App's **private key** to sign a
JWT. A user access token is *not* accepted — GitHub answers
`401 A JSON web token could not be decoded`. Deliberately, the `.pem` is not in
this repo and cannot be fetched; it is downloadable exactly once by an App
admin:

> GitHub → Settings → Developer settings → GitHub Apps →
> `keshab-flutter-assistant` → Private keys → *Generate a private key*

Put it anywhere outside git and run:

```bash
python3 gh_app.py installation-token --key ~/keys/app.pem
```

For almost everything an agent needs, the user token is enough — it can already
push, PR, and run workflows.

---

## Optional: `vault.py` (not used by default)

This repo ships with **no credentials**, which is the safest arrangement. If you
use [`vault.py`](vault.py), it can store a **Fine-Grained PAT** encrypted. This
is **not** a zero-secret login: each fresh workspace still needs the passphrase
through a secure secret-delivery mechanism. Do not put that passphrase in a
public repo, a worker brief or chat logs. This is not required for refresh/resume
or the public-repo patch workflow.

Example for a separately managed vault:

```bash
python3 vault.py seal --set token --generate-passphrase     # prints a strong passphrase once
python3 vault.py unseal --get token --to-file secrets/pat.txt
python3 vault.py verify                                     # sanity check
```

- AES-256-CBC + PBKDF2-HMAC-SHA256 (600 000 iterations) + HMAC-SHA256,
  encrypt-then-MAC. Output is plain base64, so **GitHub secret scanning will
  not flag or auto-revoke it.**
- Create a Fine-Grained PAT at *Settings → Developer settings → Personal access
  tokens → Fine-grained tokens*.

**Why a PAT and not the App refresh token?** GitHub App refresh tokens are
**single-use and rotate**. If two agents share one, the first to refresh
invalidates every other copy. A Fine-Grained PAT does not rotate, so it is the
only credential suitable for a shared vault.

**Passphrase hygiene**

- Keep the passphrase out of git, out of chat logs, and off your GitHub account.
- Do **not** reuse your GitHub password or any real-world password here.
- Longer beats complex: four random unrelated words are stronger and easier to
  remember than `P@ssw0rd123`.

---

## Why this repo is public

A private repo would defeat the purpose: an agent in a fresh sandbox has no
credentials, so it could not clone the thing meant to give it credentials.
Public + zero-secret solves that. The only gate is a human pressing *Authorize*
in a browser — which is exactly the gate that should exist.

If you would rather keep it private, make it private and hand the agent a token
for cloning; `setup.sh` also works from raw URLs if you give it one.

---

## Why is it asking me to authorize *again*?

A genuinely fresh sandbox has no saved identity. A preserved workspace should
recover without another approval while its refresh token remains usable.

| Symptom | What now happens / what to do |
|---|---|
| Access token expired, refresh token still usable | `connect` and `status` refresh before considering another device code |
| Turn ended before approval was collected | `connect` saved the code first; `device_pair.py poll 60` resumes that exact code |
| Re-running the starter requests a second code | A live pending code is reused, including its original expiry and retry interval |
| GitHub / network / rate limit is temporarily failing | No new pairing; retry later (`UNCONFIRMED` is not logout) |
| Two processes try to refresh the same workspace | The second verifies the winner under the lock instead of rotating it again |
| A worker asks for authorization on a public repo | Use the captain's default **patch brief**, not the opt-in branch/push brief |
| An entirely new captain workspace asks for approval | Expected: no saved credentials are present; never copy another agent's refresh token |
| Token or refresh was revoked, or refresh expired | One fresh device approval is necessary |

```bash
python3 gh_app.py status          # checks/recoveries only; never opens a flow
python3 device_pair.py status     # pending code, original remaining lifetime
python3 selftest.py               # offline auth regressions; only fake credentials
```

---

## Security notes

| Topic | Detail |
|---|---|
| Client ID | Public by design. Device flow needs no client secret for GitHub Apps. |
| Device code | Short-lived (~15 min), single-use, and only becomes a token after human approval. |
| Token at rest | `secrets/`, git-ignored; token and pending-state files are atomically replaced with mode `0600`. |
| Refresh tokens | Rotate on use, single-use, 181-day life — never share one between machines. Rotation is serialised by a lock in `secrets/`. |
| Re-authorization | `connect` reuses/refreshes the session, then reuses any pending code. Only explicit `--force` bypasses those guards. |
| Killing access | `python3 gh_app.py revoke`, or GitHub → Settings → Applications → `keshab-flutter-assistant` → *Revoke access*. Revoking also invalidates every token issued to that installation. |
| Least privilege | If an agent only needs one repo, narrow the App's repository selection to that repo instead of "all". |

---

## Layout

```
agent-bootstrap/
├── README.md              ← you are here; agents read this
├── gh_app.py              ← device flow + token manager + API client (stdlib only)
├── device_pair.py         ← resumable device flow (survives an interrupted turn)
├── selftest.py            ← offline test: never re-ask for authorization
├── app-meta.json          ← App, installation, endpoints, permissions, token policy
├── setup.sh               ← curl | bash one-shot installer
├── vault.py               ← optional passphrase-encrypted token store
├── AGENT_START_PROMPT.md  ← hand this to a fresh agent session (one paste)
├── CAPTAIN_START_PROMPT.md ← same, for the captain of a multi-agent batch
├── captain/               ← patch-first playbook, no-login/branch briefs, examples, BN guide
├── PROMPT-FOR-NEW-AGENT.txt ← same prompt as plain text
├── AGENT_PROMPT_COPY.html ← same prompt with a one-click copy button
├── RESUME.md              ← workspace resume guide (paths, traps, policies)
└── .gitignore             ← keeps secrets/ out of git
```

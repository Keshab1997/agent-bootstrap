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

You are expected to do the following. It is the whole job.

1. **Run** `python3 gh_app.py connect`. It self-checks first: if a valid token
   is already stored it prints `ALREADY CONNECTED -- device flow skipped` and
   exits. In that case there is nothing to do — **do not ask the human to
   authorize again.** (Genuinely dead token? `connect --force`.)
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
- Tokens last **8 hours**. Every `gh_app.py` command auto-refreshes when fewer
  than 5 minutes remain, so just keep using it.
- If `status` reports `HTTP 401` (verdict `NOT WORKING`), run `connect` again.
  Re-pairing is normal and costs the human one click — but check first: a
  working session must never be asked to authorize twice.
- Approval arriving after your turn ended? The code stays valid ~15 min — resume
  instead of starting over: `python3 device_pair.py poll 60`
  (`device_pair.py start` saves the code in `secrets/device_state.json`).
- One pair per sandbox: clone into `/home/user/agent-bootstrap`, because only
  `/home/user` survives between turns. A clone in `/tmp` loses its token and
  looks unpaired every time.

---

## Multiple agents — one captain, three workers

For work worth parallelising, hand the agent **`CAPTAIN_START_PROMPT.md`** instead:
it pairs, then reads [`captain/CAPTAIN_PROMPT.md`](captain/CAPTAIN_PROMPT.md) from
this clone. The captain splits the job into per-file worker briefs
([`captain/WORKER_BRIEF_TEMPLATE.md`](captain/WORKER_BRIEF_TEMPLATE.md), worked
examples in [`captain/examples/`](captain/examples/)), each worker pushes its own
`agent/A|B|C/<slug>` branch, and the captain reviews → fixes → squash-merges →
pushes `main`. Workers never touch `main`, and the captain never pushes a tag,
release or secret. Bengali walk-through:
[`captain/HOW_TO_START_BN.md`](captain/HOW_TO_START_BN.md).

Because the playbook ships in this repository, the first paste stays ~10 lines
instead of a whole prompt — and updating the playbook updates every future agent.

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
python3 gh_app.py connect              # pair; self-skips if already paired
python3 gh_app.py connect --force      # pair again on purpose (new code)
python3 gh_app.py status               # health + expiry; exit 0 only if paired
python3 device_pair.py status          # is a device code already pending?
python3 device_pair.py start           # get a code and save it (resumable)
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
ever want a "paste one line, get instant access, no human click" setup, use
[`vault.py`](vault.py) to store a **Fine-Grained PAT** encrypted:

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

Short answer: it shouldn't. Every known cause is handled in the code — if an
agent still asks, one of these was skipped.

| Symptom | Cause | Fix |
|---|---|---|
| Code requested although the session is paired | agent ran `connect` without checking | `connect` now calls `/user` first and prints `ALREADY CONNECTED -- device flow skipped` |
| Paired, but next turn asks again | clone lived outside `/home/user` (e.g. `/tmp`, `/var/tmp`), so `secrets/` was wiped | clone to `/home/user/agent-bootstrap`; `setup.sh` now defaults there |
| Approved in the browser, still asked again | the polling process was reaped when the agent's turn ended | the approval landed *after* the turn — resume with `device_pair.py poll 60` (code is valid ~15 min) |
| Re-authorize every ~8 h | the refresh token was thrown away | `device_pair.py` now stores the full payload; refresh tokens are 181-day |
| Two agents in one workspace kick each other out | refresh tokens are single-use | rotation is serialised with a lock, and a failed refresh no longer means "re-pair" if the stored token still works |
| Never re-paired although the token died | `status` used to exit 0 whenever a token *file* existed | `status` now exits 0 only when a real API call returns 200, so `status \|\| connect` works |

Diagnose in one command:

```bash
python3 gh_app.py status          # verdict: PAIRED  or  verdict: NOT WORKING
python3 device_pair.py status     # a device code already waiting for approval?
python3 selftest.py               # offline regression test for all of the above
```

---

## Security notes

| Topic | Detail |
|---|---|
| Client ID | Public by design. Device flow needs no client secret for GitHub Apps. |
| Device code | Short-lived (~15 min), single-use, and only becomes a token after human approval. |
| Token at rest | `secrets/` with `chmod 600`, git-ignored. |
| Refresh tokens | Rotate on use, single-use, 181-day life — never share one between machines. Rotation is serialised by a lock in `secrets/`. |
| Re-authorization | `connect` will not issue a code while the stored token still authenticates; `--force` is the only way past it. |
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
├── captain/               ← the multi-agent playbook (briefs, examples, BN guide)
├── PROMPT-FOR-NEW-AGENT.txt ← same prompt as plain text
├── AGENT_PROMPT_COPY.html ← same prompt with a one-click copy button
├── RESUME.md              ← workspace resume guide (paths, traps, policies)
└── .gitignore             ← keeps secrets/ out of git
```

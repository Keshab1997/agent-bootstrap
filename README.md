# agent-bootstrap

**A zero-secret GitHub connector for AI agents.**

Clone this repo — no credentials needed, it is public on purpose — and any AI
agent can pair with **Keshab1997**'s GitHub in one step instead of ten.

```bash
git clone https://github.com/Keshab1997/agent-bootstrap.git
cd agent-bootstrap
python3 gh_app.py connect          # prints an XXXX-XXXX code
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

1. **Run** `python3 gh_app.py connect`
2. **Tell the human**, verbatim and prominently:
   > Open <https://github.com/login/device> and enter the code **XXXX-XXXX**
3. **Wait.** The script polls every 5 s and finishes on its own. Do not ask for
   a token, a password, a PAT, or any secret — the human only approves in the
   browser.
4. **Verify** with `python3 gh_app.py whoami`
5. The token is now in `secrets/gh_token.txt` (`chmod 600`). Use
   `python3 gh_app.py api <METHOD> <PATH>` for any REST call, or read that file
   and set `Authorization: Bearer <token>`.

**Rules**

- Never print a full token to logs or chat. `gh_app.py` masks it for you.
- Never commit anything under `secrets/` (already git-ignored).
- Tokens last **8 hours**. Every `gh_app.py` command auto-refreshes when fewer
  than 5 minutes remain, so just keep using it.
- If `status` reports `HTTP 401`, run `connect` again. Re-pairing is normal and
  costs the human one click.

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
python3 gh_app.py connect              # pair (device flow)
python3 gh_app.py status               # health + expiry
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

## Security notes

| Topic | Detail |
|---|---|
| Client ID | Public by design. Device flow needs no client secret for GitHub Apps. |
| Device code | Short-lived (~15 min), single-use, and only becomes a token after human approval. |
| Token at rest | `secrets/` with `chmod 600`, git-ignored. |
| Refresh tokens | Rotate on use — never share one between machines. |
| Killing access | `python3 gh_app.py revoke`, or GitHub → Settings → Applications → `keshab-flutter-assistant` → *Revoke access*. Revoking also invalidates every token issued to that installation. |
| Least privilege | If an agent only needs one repo, narrow the App's repository selection to that repo instead of "all". |

---

## Layout

```
agent-bootstrap/
├── README.md          ← you are here; agents read this
├── gh_app.py          ← device flow + token manager + API client (stdlib only)
├── app-meta.json      ← App, installation, endpoints, permissions, token policy
├── setup.sh           ← curl | bash one-shot installer
├── vault.py           ← optional passphrase-encrypted token store
└── .gitignore         ← keeps secrets/ out of git
```

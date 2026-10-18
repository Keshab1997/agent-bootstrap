# PATCH WORKER TEMPLATE — default for public repositories, no GitHub login

Captain: fill every `{{FIELD}}`, verify the repo is public, pin the full current
base commit SHA, and assign disjoint files. Use the branch template only when
explicitly chosen. `STAGE_PATHS` is the exact shell-quoted file list, never `.`
or `-A`; `PATCH_FILE` is a unique filename such as `A-home-overflow.patch`.

✂ ═══════════════ COPY FROM HERE ═══════════════

# You are agent {{LETTER}}. One task, one local branch, one patch. No GitHub login.

Work in your own sandbox. Do not run `gh_app.py connect`, request authorization,
read/copy credentials, configure a credential helper, or push any branch. The
captain reviews and publishes your work. If blocked, report; do not expand scope.

## 1. Task and frozen source

**Goal (one sentence, testable):** {{GOAL}}
**Public repository:** `Keshab1997/{{REPO}}`
**Base commit (full SHA):** `{{BASE_SHA}}`
**Local branch:** `{{BRANCH}}` (never `main`)

```bash
GIT_TERMINAL_PROMPT=0 git clone https://github.com/Keshab1997/{{REPO}}.git /home/user/{{REPO}}
cd /home/user/{{REPO}}
git config core.fileMode false
git config user.name "Keshab Sarkar"
git config user.email "Keshab1997@users.noreply.github.com"
git checkout -b {{BRANCH}} {{BASE_SHA}}
```

If this clone/branch already exists, inspect and resume it; never reset or delete
someone's work. If public cloning fails or the base cannot be found, report the
blocker. Do not ask Keshab to authorize as a workaround. Read the repository's
`AGENTS.md` before editing. This brief does not authorize publishing.

**Files you own (only these):** {{ALLOWED_FILES}}
**Interface (exact frozen names/strings, or explicitly "none"):** {{INTERFACE}}
**DO NOT TOUCH:** {{DO_NOT_TOUCH}}

Always excluded: secrets/credentials, CI workflows, version/dependency changes,
generated files and any other worker's files. Shared surfaces stay with the
captain unless this brief explicitly assigns one. Never edit or push `main`.

## 2. One check, then a local commit and patch

```bash
{{CHECK}}
```

Fix failures caused by your change only. No full battery, `flutter build`,
`gradlew`, CI dispatch or waiting for CI. A failing unrelated check is a blocker,
not permission to edit more files.

Review your diff for scope and secrets before committing:

```bash
git diff --check
git diff --stat
git diff
git add -- {{STAGE_PATHS}}
git diff --cached --check
git diff --cached
git commit -m "{{COMMIT_MESSAGE}}"
git diff --name-only {{BASE_SHA}} HEAD
```

Every changed path must be in the allowed list. Stop if not; do not hide an
out-of-scope change by filtering the exported patch. Export all committed changes
against the frozen base (includes additions, deletions, binary content and modes):

```bash
mkdir -p /home/user/handoff
git diff --binary --full-index {{BASE_SHA}} HEAD > /home/user/handoff/{{PATCH_FILE}}
test -s /home/user/handoff/{{PATCH_FILE}}
sha256sum /home/user/handoff/{{PATCH_FILE}}
```

Do not include build artifacts or credentials. Do not push. Open/present the
patch file for download if your tools support it. **Keshab must attach the actual
file to the captain's chat**; a path in your sandbox is not accessible there.

## 3. Report with the patch attachment, then stop

```text
AGENT {{LETTER}} DONE
mode: patch (no GitHub authorization)
repo: Keshab1997/{{REPO}}
base: {{BASE_SHA}}
branch: {{BRANCH}} (local only)
sha: <git rev-parse HEAD>
patch: {{PATCH_FILE}}
sha256: <actual sha256sum output>
files: <all changed paths against the base>
check: {{CHECK}} → <pass/fail + evidence>
changed: <one sentence>
not touched: <deliberately excluded areas>
blocked: <none | blocker and decision needed>
```

Stop if the task needs an unowned file, the interface is wrong, the scope grows,
the check fails outside your change, or the source is not publicly accessible.
A clear blocked report is better than an authorization request or surprise diff.

✂ ═══════════════ COPY ENDS HERE ═══════════════

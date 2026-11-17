> **In-flight manual briefs only.** For new tasks use [Worker Fast Lane](FASTLANE.md) and its [compact brief](WORKER_BRIEF_TEMPLATE.md). Do not merge or close an Arena-linked PR as a task handoff.

# WORKER BRIEF TEMPLATE — use the workspace's real branch
#
# Rules for the captain:
#   * Fill every field. ARENA_BRANCH is the exact Arena branch if known, or `auto`.
#   * FALLBACK_BRANCH is a unique agent/<letter>/<short-slug> for standalone only.
#   * CHECK is one command line: the repo's required gate and only the targeted test.
#   * STAGE_PATHS is the exact shell-quoted allowed file list, never . or -A.
#   * DO NOT TOUCH lists shared surfaces. No two workers share a branch or a file.

✂ ═══════════════ COPY FROM HERE (give the whole block to the worker) ═══════════════

# You are agent {{LETTER}}. One task, one branch, then you stop.

**Goal (one sentence, testable):** {{GOAL}}

**Repository:** `Keshab1997/{{REPO}}`  ·  **Arena branch:** `{{ARENA_BRANCH}}`  ·  **Standalone fallback:** `{{FALLBACK_BRANCH}}`

## 1. Find your checkout and select the task branch before editing

- Use the repo already attached in the Arena workspace. Check `git rev-parse --show-toplevel`, `git status --short --branch`, and both fetch/push URLs of `origin`. Do not clone or change checkout just to get a different branch name. If no repo is attached, reuse `/home/user/{{REPO}}` or clone the named repo there. If `origin` is missing, first verify the checkout is that repo, then restore it with `git remote add origin https://github.com/Keshab1997/{{REPO}}.git`. Never overwrite a different remote.
- If the repo is linked in Arena, its checked-out `arena/*` branch **is your task branch**. `auto` means use the actual name from `git branch --show-current`. The `agent/...` fallback is **not** a reason to stop, rename, switch, or create a second branch. If the Arena UI labels a different branch than Git or the brief specifies a different exact Arena branch, stop and report the mismatch; don't guess.
- Use the `agent/...` fallback only in a **standalone** checkout with no Arena binding. Fetch `origin` in the verified checkout. Inspect any existing work first; continue only known work from this task. Never reset, force-push, or overwrite another task. This brief overrides generic `AGENTS.md` instructions to push `main` or run `tool/agent_loop.py`; neither applies to a Captain worker.

Run this from that verified checkout. If this is an Arena-linked checkout but its actual branch is not an `arena/*` branch, stop before running the standalone path.

<!-- worker-branch-selection -->
```bash
set -eu
expected_arena='{{ARENA_BRANCH}}'
fallback='{{FALLBACK_BRANCH}}'
current=$(git branch --show-current)
fail() { printf '%s\n' "$*" >&2; exit 1; }
case "$expected_arena" in
  auto) ;;
  arena/?*) git check-ref-format "refs/heads/$expected_arena" ;;
  *) fail 'Invalid Arena branch in the brief.' ;;
esac
case "$fallback" in
  agent/{{LETTER}}/?*) git check-ref-format "refs/heads/$fallback" ;;
  *) fail 'Invalid standalone fallback in the brief.' ;;
esac
case "$current" in
  arena/?*)
    [ "$expected_arena" = auto ] || [ "$current" = "$expected_arena" ] ||
      fail "Wrong Arena branch: expected $expected_arena, found $current."
    ;; # Stay on the current Arena branch.
  "$fallback")
    [ "$expected_arena" = auto ] || fail "Use the Arena workspace on $expected_arena."
    ;; # Resume your existing standalone task branch.
  main)
    [ "$expected_arena" = auto ] || fail "Use the Arena workspace on $expected_arena."
    [ -z "$(git status --porcelain)" ] || fail 'Standalone main is not clean; leave it alone.'
    if git show-ref --verify --quiet "refs/heads/$fallback"; then
      git switch "$fallback"
    elif git show-ref --verify --quiet "refs/remotes/origin/$fallback"; then
      git switch --track -c "$fallback" "origin/$fallback"
    else
      git switch -c "$fallback" origin/main
    fi
    ;;
  *) fail "Unexpected branch: ${current:-detached HEAD}. Leave the checkout alone." ;;
esac
head=$(git rev-parse --verify HEAD)
printf 'task_branch: %s\nhead: %s\n' "$(git branch --show-current)" "$head"
```

Record `task_branch` **and** the full `base_sha` (HEAD before this task's first edit). On a resume, keep the original base, not a commit from partway through the task. On a reused branch review how it differs from `origin/main` before editing; if unrelated or stale changes make the work unsafe, report that instead of rewriting the branch. Never stage pre-existing work.

**Files you own (only these):**

{{ALLOWED_FILES}}

**DO NOT TOUCH** (they belong to the captain or to another worker):

- `pubspec.yaml`, `pubspec.lock`, any version bump, any dependency addition
- `.github/workflows/**`, anything under `android/` and `ios/`
- `AGENTS.md` managed block, `tool/**`, `secrets/**`, routing, generated files
- any file another worker owns in this batch
- **`main` itself. Never push, merge, or rebase `main`; do not open a PR or dispatch CI.**

**Interface (exact names/strings the captain froze — use these verbatim):**

{{INTERFACE}}

## 2. Run the assigned check, then commit and push exactly your task branch

```bash
{{CHECK}}
```

Fix failures in your work. If a required check is unavailable or fails outside your changes, report it. No full analyze/test battery, local build, or manual CI unless the captain's task explicitly calls for it. A branch push can still trigger a repo's automatic preview.

Use the workspace's existing authorized Git access first (Arena's access when available). Do not start a new device flow just because your branch is `arena/*`. If standalone access is needed, reuse this worker's approved `agent-bootstrap` session (`gh_app.py status` first). Only if Keshab approves pairing a genuinely unpaired workspace, use `gh_app.py connect --show-only`, have him authorize the expected app/account at `https://github.com/login/device`, then resume the same code with `device_pair.py poll 60`. Never request, share, or print tokens; use a repo-scoped credential helper if needed. If you cannot push, report the block, not success.

In **each** shell below, set `branch` to the exact `task_branch` recorded in §1. Verify the push URL still points to the named repository. Stage only the allowed files:

```bash
set -eu
: "${branch:?Set branch to the exact task_branch recorded before editing}"
case "$branch" in arena/?*|'{{FALLBACK_BRANCH}}') ;; *) exit 1 ;; esac
test "$(git branch --show-current)" = "$branch"
git diff --cached --quiet # Do not piggyback on pre-existing staged changes.
git add -- {{STAGE_PATHS}}
git diff --cached --check
git diff --cached
```

Inspect the whole staged diff. Stop on any out-of-scope or secret file. Only then commit and push with the **same** branch guard and refspec:

<!-- worker-branch-push -->
```bash
set -eu
: "${branch:?Set branch to the exact task_branch recorded before editing}"
case "$branch" in arena/?*|'{{FALLBACK_BRANCH}}') ;; *) exit 1 ;; esac
test "$(git branch --show-current)" = "$branch"
git commit -m "{{COMMIT_MESSAGE}}"
git push origin "HEAD:refs/heads/$branch"
remote_sha=$(git ls-remote --exit-code origin "refs/heads/$branch" | cut -f1)
test "$remote_sha" = "$(git rev-parse HEAD)"
```

Commit messages use `type(scope): what changed`. No force-push or branch deletion.

## 3. Report the actual outcome to Keshab

Use `AGENT {{LETTER}} PUSHED` only when the checks passed and the remote branch points to your commit. Otherwise use `AGENT {{LETTER}} BLOCKED` and say what happened; don't call an unstarted or unpushed task done.

```text
AGENT {{LETTER}} PUSHED
branch: <actual pushed branch: arena/... or the standalone fallback>
base_sha: <full HEAD SHA from before this task>
sha: <full pushed HEAD SHA>
files: <git diff --name-only base_sha sha, scoped to this task>
check: {{CHECK}} → <actual result>
changed: <one sentence>
not touched: <what you deliberately left alone>
blocked: <none, or exact blocker and what is needed>
```

Stop on the wrong repo/actual branch, unclear scope, unrelated existing changes, failed checks outside your task, or unavailable push access. **Using the current authorized `arena/*` branch instead of the standalone fallback is normal.**

✂ ═══════════════ COPY ENDS HERE ═══════════════

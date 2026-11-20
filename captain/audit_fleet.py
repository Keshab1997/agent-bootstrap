#!/usr/bin/env python3
"""Fleet audit: agent-pack health across Keshab's Flutter repos, one call.

    python3 captain/audit_fleet.py                     # every Dart repo
    python3 captain/audit_fleet.py --repos owner/a,owner/b
    python3 captain/audit_fleet.py --json

Read-only (≈3 API calls per repo). Per repo it checks:
  flutter      pubspec.yaml exists (else: not a Flutter repo — skipped note)
  pack tools   tool/preflight.py · tool/agent_loop.py · tool/ci_watch.py
  AGENTS.md    exists + managed-block pin (flutter-builder:agent-pack:start vX.Y.Z)
  CI           .github/workflows/ci.yml exists, has workflow_dispatch, and its
               flutter-builder reusable-workflow pin (if any)
  pins         pack pin vs CI pin — `DRIFT` when a repo's AGENTS.md block and
               its workflow disagree about which builder they run
  secrets      tracked key material or a config that really carries a value
               (*.jks/*.keystore/*.pem/id_rsa, key.properties,
               google-services.json, .env). An empty tracked-on-purpose
               template is listed separately, not as a leak.

The last line compares the warm SDK cache against Google's current stable and
says when to repack. Gaps are summarized at the end. Nothing is modified;
fixing a gap is a Captain-owned shared-surface batch (see CAPTAIN_PROMPT.md
§2a) — `captain/fleet_bump.sh <repo>` converges one repo on the pack version
in the flutter-builder working tree (pack + every workflow pin + preflight
gate + direct push to its default branch).
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

BOOT = Path(__file__).resolve().parent.parent
GH = BOOT / "gh_app.py"
PACK_PIN_RE = re.compile(r"flutter-builder:agent-pack:start\s+v?([0-9A-Za-z._-]+)")
REUSABLE_RE = re.compile(r"uses:\s*Keshab1997/flutter-builder/\.github/workflows/([\w.-]+)@([\w.-]+)")
SECRET_RE = re.compile(
    r"(\.jks|\.keystore|\.p12|\.p8|\.pem)$|"
    r"(^|/)(key\.properties|google-services\.json|id_rsa[^/]*|\.env|\.env\.[^/]+)$",
    re.IGNORECASE)
SECRET_OK_RE = re.compile(r"\.(example|sample|template)$", re.IGNORECASE)
KEYFILE_RE = re.compile(r"(\.jks|\.keystore|\.p12|\.p8|\.pem)$|(^|/)id_rsa", re.IGNORECASE)
ENV_VALUE_RE = re.compile(r"(?m)^\s*[A-Za-z_][\w.]*\s*[=:]\s*[\"']?([^\s\"'#]{16,})")
PLACEHOLDER_RE = re.compile(r"(?i)^(your|xxx+|placeholder|changeme|change_me|example|dummy|sample|test|<|\{\{)")


def secret_is_real(full, path, branch) -> bool:
    """Is a tracked secret-looking file an actual leak?

    Key material (*.jks, *.keystore, *.p12/.p8, *.pem, id_rsa) always counts —
    its content is the secret. Text configs only count when they really carry a
    value, so an empty `.env` template that a repo tracks on purpose (keepit
    documents exactly that in its .gitignore) is not reported as a leak. An
    unreadable file is reported rather than silently passed."""
    if KEYFILE_RE.search(path):
        return True
    text = file_text(full, path, branch)
    if text is None:
        return True
    if not text.strip():
        return False
    name = Path(path).name.lower()
    if name == "google-services.json":
        return bool(re.search(r'"current_key"\s*:\s*"[A-Za-z0-9_\-]{20,}"', text))
    if name == "key.properties":
        return any(not PLACEHOLDER_RE.match(value.strip()) for value in
                   re.findall(r"(?mi)^\s*(?:store|key)Password\s*=\s*(\S+)", text))
    return any(not PLACEHOLDER_RE.match(value) for value in ENV_VALUE_RE.findall(text))


def api(path: str, timeout: int = 45):
    proc = subprocess.run(
        [sys.executable, "-B", str(GH), "api", "GET", path, "--raw"],
        capture_output=True, text=True, timeout=timeout, cwd=str(BOOT))
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[:200]
        raise SystemExit(f"ERROR: gh_app.py api GET {path} failed.\n{detail}\n"
                         "paired? run: python3 gh_app.py connect")
    body = proc.stdout.strip()
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def dart_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = api(f"/user/repos?per_page=100&sort=updated&page={page}") or []
        if not isinstance(batch, list):
            batch = batch.get("repositories", [])
        repos += [r for r in batch if (r.get("language") or "") == "Dart"
                  and str(r.get("full_name", "")).lower().startswith("keshab1997/")]
        if len(batch) < 100:
            break
        page += 1
    return sorted(repos, key=lambda r: r["full_name"].lower())


def file_text(repo: str, path: str, branch: str) -> str | None:
    data = api(f"/repos/{repo}/contents/{path}?ref={branch}")
    if isinstance(data, dict) and data.get("content"):
        try:
            return base64.b64decode(data["content"]).decode("utf-8", "replace")
        except Exception:
            return None
    return None


def audit_repo(repo: dict | str) -> dict:
    if isinstance(repo, str):
        meta = api(f"/repos/{repo}") or {}
    else:
        meta = repo
    full = meta.get("full_name", str(repo))
    branch = meta.get("default_branch") or "main"
    out: dict = {"repo": full, "branch": branch, "pushed_at": meta.get("pushed_at"),
                 "language": meta.get("language")}
    tree = api(f"/repos/{full}/git/trees/{branch}?recursive=1") or {}
    paths = {t.get("path", "") for t in tree.get("tree", [])}
    out["tree_truncated"] = bool(tree.get("truncated"))

    def has(p: str) -> bool:
        return p in paths if not out["tree_truncated"] else bool(
            api(f"/repos/{full}/contents/{p}?ref={branch}"))

    out["flutter"] = has("pubspec.yaml") or has("melos.yaml") or any(
        p.endswith("pubspec.yaml") and p.count("/") <= 1 for p in paths)
    out["preflight"] = has("tool/preflight.py")
    out["agent_loop"] = has("tool/agent_loop.py")
    out["ci_watch"] = has("tool/ci_watch.py")
    out["agents_md"] = has("AGENTS.md")

    out["pack_pin"] = None
    if out["agents_md"]:
        m = PACK_PIN_RE.search(file_text(full, "AGENTS.md", branch) or "")
        out["pack_pin"] = m.group(1) if m else None

    ci_candidates = sorted(p for p in paths
                           if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))
                           and "ci" in Path(p).name.lower())
    out["ci_file"] = next((p for p in ci_candidates if Path(p).name == "ci.yml"),
                          ci_candidates[0] if ci_candidates else None)
    if out["ci_file"] is None and out["tree_truncated"] and has(".github/workflows/ci.yml"):
        out["ci_file"] = ".github/workflows/ci.yml"
    out["ci_yml"] = bool(out["ci_file"])
    out["ci_dispatch"] = None
    out["ci_reusable_pin"] = None
    if out["ci_file"]:
        text = file_text(full, out["ci_file"], branch) or ""
        out["ci_dispatch"] = "workflow_dispatch" in text
        m = REUSABLE_RE.search(text)
        out["ci_reusable_pin"] = f"{m.group(1)}@{m.group(2)}" if m else "standalone"

    ci_pin_ver = None
    if out["ci_reusable_pin"] and out["ci_reusable_pin"] != "standalone":
        ci_pin_ver = out["ci_reusable_pin"].split("@", 1)[1].lstrip("vV")
    out["pin_drift"] = bool(out["pack_pin"] and ci_pin_ver
                            and out["pack_pin"].lstrip("vV") != ci_pin_ver)

    out["secrets"], out["secret_templates"] = [], []
    for p in sorted(x for x in paths if SECRET_RE.search(x) and not SECRET_OK_RE.search(x)):
        (out["secrets"] if secret_is_real(full, p, branch) else out["secret_templates"]).append(p)
    out["gaps"] = []
    if out["secrets"]:
        out["gaps"].append(f"TRACKED SECRET FILES ({len(out['secrets'])}): "
                           + ", ".join(out["secrets"][:4]))
    if not out["flutter"]:
        out["gaps"].append("no pubspec.yaml/melos.yaml (not a Flutter repo?)")
    else:
        for key, label in (("preflight", "tool/preflight.py"), ("agent_loop", "tool/agent_loop.py"),
                           ("ci_watch", "tool/ci_watch.py"), ("agents_md", "AGENTS.md"),
                           ("ci_yml", ".github/workflows/ci.yml")):
            if not out[key]:
                out["gaps"].append(f"missing {label}" if key != "ci_yml"
                                   else "no CI workflow (*ci*.yml in .github/workflows)")
        if out["agents_md"] and not out["pack_pin"]:
            out["gaps"].append("AGENTS.md without agent-pack managed block")
        if out["ci_yml"] and out["ci_dispatch"] is False:
            out["gaps"].append("ci.yml lacks workflow_dispatch")
    return out


def yn(v) -> str:
    return "-" if v is None else ("yes" if v else "NO")


def stable_vs_warm() -> str:
    """Fleet maintenance hint: does the warm SDK cache cover Google's current stable?"""
    import urllib.request
    try:
        with urllib.request.urlopen(
                "https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json",
                timeout=20) as r:
            man = json.loads(r.read().decode())
        stable_hash = man["current_release"]["stable"]
        stable = next(x["version"] for x in man["releases"]
                      if x.get("hash") == stable_hash and x.get("channel") == "stable"
                      and "linux" in x.get("archive", ""))
        with urllib.request.urlopen(
                "https://github.com/Keshab1997/flutter-bootstrap/releases/download/"
                "sdk-cache/cache-manifest.json", timeout=20) as r:
            warm = sorted((json.loads(r.read().decode()).get("entries") or {}))
        line = f"warm SDK cache: {', '.join(warm) or 'none'} | Google stable: {stable}"
        if stable not in warm:
            line += "  -> REPACK: bash pack.sh (once that version is installed anywhere)"
        return line
    except Exception as exc:
        return f"stable-vs-warm check skipped ({exc.__class__.__name__})"


def main() -> int:
    p = argparse.ArgumentParser(prog="audit_fleet.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repos", help="comma-separated owner/name list (default: all Dart repos)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.repos:
        targets: list = [r.strip() for r in args.repos.split(",") if r.strip()]
    else:
        targets = dart_repos()
        print(f"auditing {len(targets)} Dart repos (read-only)…\n", file=sys.stderr)
    results = [audit_repo(t) for t in targets]

    if args.json:
        print(json.dumps(results, indent=1))
    else:
        hdr = ("repo", "pack pin", "pins", "preflight", "loop", "watch", "AGENTS",
               "ci.yml", "dispatch", "ci kind", "secrets", "gaps")
        rows = [hdr]
        for r in results:
            pins = ("DRIFT" if r.get("pin_drift")
                    else ("ok" if r.get("pack_pin") and r.get("ci_reusable_pin") not in (None, "standalone") else "-"))
            rows.append((
                r["repo"].split("/", 1)[1], str(r["pack_pin"] or "-"), pins, yn(r["preflight"]),
                yn(r["agent_loop"]), yn(r["ci_watch"]), yn(r["agents_md"]), yn(r["ci_yml"]),
                yn(r["ci_dispatch"]), str(r["ci_reusable_pin"] or "-"),
                (f"{len(r['secrets'])}!!" if r.get("secrets")
                 else (f"{len(r['secret_templates'])}tpl" if r.get("secret_templates") else "-")),
                str(len(r["gaps"])),
            ))
        widths = [max(len(row[i]) for row in rows) for i in range(len(hdr))]
        for i, row in enumerate(rows):
            print("  ".join(c.ljust(widths[j]) for j, c in enumerate(row)).rstrip())
            if i == 0:
                print("  ".join("-" * w for w in widths))
        print()
        flagged = [r for r in results if r["gaps"]]
        if flagged:
            print(f"{len(flagged)} repo(s) with gaps:")
            for r in flagged:
                print(f"  {r['repo']}: " + "; ".join(r["gaps"]))
        else:
            print("all audited repos carry the full agent pack — no gaps.")
        templates = [(r["repo"].split("/", 1)[1], p) for r in results
                     for p in r.get("secret_templates", [])]
        if templates:
            print()
            print("tracked but empty (templates, not leaks — no action needed):")
            for repo, path in templates:
                print(f"  {repo}: {path}")
        print()
        print(stable_vs_warm())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

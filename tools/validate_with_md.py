"""Run Millennium Dawn's validators against this submod's files.

The owned ENG files are overlaid on a sparse checkout of MD at the pinned commit
in tools/md_base_ref.txt, MD's own batch runner runs from that checkout, and the
findings are reduced to owned files plus anything new against an optional
pristine-MD baseline.

Usage:
  python tools/validate_with_md.py [--md <MD checkout>] [--batch core]
  python tools/validate_with_md.py --workspace md --baseline-dir .validation_baseline
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_md_base import ENG_PATHS, ENG_SUBMOD_ONLY_PATHS, MD_BASE_REF, REPO

BATCHES = ("core", "targeted-a", "targeted-b")
OWNED = ENG_PATHS + ENG_SUBMOD_ONLY_PATHS

# What MD's CI workspace holds, minus music (691 MB of audio nothing here needs).
SPARSE_PROFILE = """\
/tools/
/common/
/events/
/history/
/localisation/english/
/interface/
/gfx/flags/
/gfx/interface/decisions/
/map/adjacency_rules.txt
/resources/documentation/
/.claude/docs/typo-watchlist.md
/pyproject.toml
/descriptor.mod
/*.mod
"""


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def make_worktree(md_root, ref):
    if subprocess.run(["git", "cat-file", "-e", f"{ref}^{{commit}}"], cwd=md_root).returncode:
        sys.exit(f"{ref} is not in {md_root}; run git fetch there first")
    ws = Path(tempfile.mkdtemp(prefix="md-validate-"))
    git("worktree", "add", "--detach", "--no-checkout", str(ws), ref, cwd=md_root)
    git("sparse-checkout", "init", "--no-cone", cwd=ws)
    subprocess.run(
        ["git", "sparse-checkout", "set", "--stdin"], cwd=ws, check=True, input=SPARSE_PROFILE, text=True
    )
    git("checkout", "-q", ref, cwd=ws)
    return ws


def remove_worktree(md_root, ws):
    subprocess.run(["git", "worktree", "remove", "--force", str(ws)], cwd=md_root, check=False)


def overlay(ws):
    for rel in OWNED:
        src = REPO / rel
        dst = ws / rel
        if not src.exists():
            sys.exit(f"owned path missing in this repo: {src}")
        if dst.is_dir():
            shutil.rmtree(dst)
        elif dst.exists():
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def owned_files(suffix):
    files = []
    for rel in OWNED:
        path = REPO / rel
        if path.is_dir():
            files.extend(p.relative_to(REPO).as_posix() for p in sorted(path.rglob(f"*{suffix}")))
        elif rel.endswith(suffix):
            files.append(rel)
    return files


def run_batch(ws, batch, out_dir):
    # Exit code reflects MD's whole backlog; crashes are read from the manifest.
    subprocess.run(
        [
            sys.executable,
            str(ws / "tools" / "validation" / "run_validator_batch.py"),
            "--batch",
            batch,
            "--path",
            str(ws),
            "--output-dir",
            str(out_dir),
            "--no-color",
        ],
        check=False,
    )


def run_core_extras(ws, out_dir):
    """MD's core-job extras, restricted to owned files. Returns failed step names."""
    out_dir.mkdir(parents=True, exist_ok=True)
    txt = owned_files(".txt")
    yml = owned_files(".yml")
    validation = ws / "tools" / "validation"
    linting = ws / "tools" / "linting"
    env = dict(os.environ, MD_STAGED_FILES="\n".join(txt))
    steps = {
        "style": (
            [sys.executable, str(validation / "validate_style.py"), "--staged", "--strict", "--no-color",
             "--path", str(ws), "--output", str(out_dir / "validation-style.log")],
            env,
        ),
        "common-mistakes": (
            [sys.executable, str(linting / "check_common_mistakes.py"), *txt,
             "--output", str(out_dir / "validation-common-mistakes.log")],
            None,
        ),
        "txt-encoding": ([sys.executable, str(linting / "validate_txt_encoding.py"), *txt], None),
        "localisation-encoding": ([sys.executable, str(linting / "validate_localization_encoding.py"), *yml], None),
    }
    failed = []
    for name, (cmd, step_env) in steps.items():
        if subprocess.run(cmd, cwd=ws, env=step_env, check=False).returncode:
            failed.append(name)
    return failed


def is_owned(file):
    file = file.replace("\\", "/")
    for rel in OWNED:
        if file == rel or file.endswith("/" + rel) or (rel + "/") in file:
            return True
    return False


def load_baseline_keys(ws, baseline_dir):
    sys.path.insert(0, str(ws / "tools"))
    from report_lib import load_baseline

    baseline = load_baseline(str(baseline_dir))
    if baseline is None:
        print(f"no usable baseline in {baseline_dir}; keeping owned-file findings only")
        return None
    return baseline.keys


def filter_sidecar(path, baseline_keys, ws):
    issues = json.loads(path.read_text(encoding="utf-8"))
    kept = []
    for issue in issues:
        if is_owned(issue.get("file", "")):
            kept.append(issue)
        elif baseline_keys is not None:
            from report_lib import Issue, issue_key

            key = issue_key(Issue.from_dict(issue))
            if key is None or key not in baseline_keys:
                kept.append(issue)
    path.write_text(json.dumps(kept, indent=2), encoding="utf-8", newline="")
    return kept


def filter_results(out_root, ws, baseline_dir):
    """Rewrite every sidecar to the submod's scope. Returns (issues, gating)."""
    baseline_keys = load_baseline_keys(ws, baseline_dir) if baseline_dir else None
    all_issues = []
    gating = False
    for sidecar in sorted(out_root.rglob("validation-*.json")):
        kept = filter_sidecar(sidecar, baseline_keys, ws)
        all_issues.extend(kept)
        strict = True
        manifest_path = sidecar.parent / "batch-manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            name = sidecar.stem.removeprefix("validation-")
            for entry in manifest["results"]:
                if entry["name"] != name or entry["status"] in ("crash", "missing"):
                    continue
                # Same convention as run_validator_batch.classify_result: a
                # validator exits 1 only for errors under --strict.
                strict = entry["strict"]
                failing = strict and any(i.get("severity") == "error" for i in kept)
                entry["status"] = "findings" if failing else "ok"
                entry["returncode"] = 1 if failing else 0
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="")
        if strict and any(i.get("severity") == "error" for i in kept):
            gating = True
    return all_issues, gating


def crashed_validators(out_root, batches):
    names = []
    for batch in batches:
        manifest_path = out_root / batch / "batch-manifest.json"
        if not manifest_path.is_file():
            names.append(f"{batch} (no manifest)")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        names.extend(e["name"] for e in manifest["results"] if e["status"] in ("crash", "missing"))
    return names


def print_summary(issues):
    by_file = {}
    for issue in issues:
        by_file.setdefault(issue.get("file", "?"), []).append(issue)
    for file, file_issues in sorted(by_file.items()):
        print(file)
        for i in sorted(file_issues, key=lambda i: i.get("line") or 0):
            line = f":{i['line']}" if i.get("line") else ""
            print(f"  {i.get('severity', '?')[0].upper()} {file}{line} [{i.get('category', '')}] {i.get('message', '')}")
    errors = sum(1 for i in issues if i.get("severity") == "error")
    warnings = sum(1 for i in issues if i.get("severity") == "warning")
    print(f"\n{errors} error(s), {warnings} warning(s) in scope")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--md", default="D:/Documenten/Paradox Interactive/Hearts of Iron IV/mod/Millennium-Dawn", help="Millennium Dawn checkout to build a worktree from")
    parser.add_argument("--ref", default=None, help="MD commit (default: tools/md_base_ref.txt)")
    parser.add_argument("--workspace", type=Path, help="existing MD tree to validate in place (skips the worktree)")
    parser.add_argument("--batch", choices=BATCHES + ("all",), default="all")
    parser.add_argument("--output-dir", type=Path, default=Path("validation-out"))
    parser.add_argument("--baseline-dir", type=Path, help="pristine-MD baseline; new findings elsewhere are kept")
    parser.add_argument("--no-overlay", action="store_true", help="validate pristine MD (baseline build)")
    parser.add_argument("--no-filter", action="store_true", help="keep every finding")
    parser.add_argument("--keep", action="store_true", help="leave the temporary worktree in place")
    args = parser.parse_args()

    ref = args.ref or MD_BASE_REF.read_text(encoding="utf-8").strip()
    md_root = Path(args.md)
    out_root = args.output_dir.resolve()
    # A stale sidecar from an earlier run would hide a validator crash in this one.
    shutil.rmtree(out_root, ignore_errors=True)
    ws = args.workspace.resolve() if args.workspace else make_worktree(md_root, ref)
    try:
        if not args.no_overlay:
            overlay(ws)
        batches = BATCHES if args.batch == "all" else (args.batch,)
        for batch in batches:
            run_batch(ws, batch, out_root / batch)
        # Extras only cover owned files, which the filter always keeps, so a
        # baseline run has no use for them.
        failed_extras = []
        if "core" in batches and not args.no_overlay:
            failed_extras = run_core_extras(ws, out_root / "extras")
        if args.no_filter:
            issues, gating = [], False
        else:
            issues, gating = filter_results(out_root, ws, args.baseline_dir)
            print_summary(issues)
    finally:
        if not args.workspace:
            if args.keep:
                print(f"worktree kept at {ws}")
            else:
                remove_worktree(md_root, ws)

    crashed = crashed_validators(out_root, batches)
    if crashed:
        print(f"validators crashed or produced no result: {', '.join(crashed)}")
    if failed_extras:
        print(f"failed: {', '.join(failed_extras)}")
    sys.exit(1 if (crashed or failed_extras or gating) else 0)


if __name__ == "__main__":
    main()

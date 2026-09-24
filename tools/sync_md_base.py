"""Refresh the md-base branch from a Millennium Dawn checkout and merge it into main.

Usage: python tools/sync_md_base.py [--md D:/secondary-md] [--no-merge]
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Full MD commit the ENG files were last synced from; CI validates against it.
MD_BASE_REF = REPO / "tools" / "md_base_ref.txt"

# Every path this submod owns. A file at the same relative path overrides MD's copy.
ENG_PATHS = [
    "common/national_focus/05_united_kingdom.txt",
    "common/decisions/05_ENG_decisions.txt",
    "common/decisions/categories/united_kingdom_categories.txt",
    "common/ideas/05_united_kingdom.txt",
    "common/scripted_effects/99_ENG_scripted_effects..txt",
    "common/scripted_effects/ENG_political_leaders.txt",
    "common/scripted_triggers/99_ENG_scripted_triggers.txt",
    "common/dynamic_modifiers/99_ENG_dynamic_modifiers.txt",
    "common/scripted_localisation/99_ENG_scripted_localisation.txt",
    "common/scripted_guis/99_ENG_scripted_guis.txt",
    "common/on_actions/99_ENG_on_actions.txt",
    "common/characters/ENG.txt",
    "common/focus_inlay_windows/eng_inner_circle_inlay_window.txt",
    "common/country_leader/ENG_traits.txt",
    "common/opinion_modifiers/ENG.txt",
    "common/ai_strategy/ENG.txt",
    "common/ai_strategy_plans/ENG_strategy_plans.txt",
    "common/bookmarks/blitzkrieg.txt",
    "events/05_united_kingdom.txt",
    "events/Influence.txt",
    "interface/ENG_British_guis.gui",
    "interface/MD_ENG_decisions.gfx",
    "gfx/interface/goals/united_kingdom",
    "history/countries/ENG - United Kingdom.txt",
    "localisation/english/MD_focus_ENG_l_english.yml",
]

# Submod-only files with no MD counterpart. Owned like ENG_PATHS, never synced.
ENG_SUBMOD_ONLY_PATHS = [
    "common/autonomous_states/99_ENG_autonomies.txt",
    "common/factions/templates/99_ENG_commonwealth.txt",
    "gfx/interface/scripted_gui/eng/ENG_scotland_integrated_gfx.dds",
    "gfx/interface/scripted_gui/eng/ENG_scotland_independent_gfx.dds",
    "gfx/interface/scripted_gui/eng/ENG_wales_integrated_gfx.dds",
    "gfx/interface/scripted_gui/eng/ENG_wales_independent_gfx.dds",
    "gfx/interface/scripted_gui/eng/ENG_north_ireland_integrated_gfx.dds",
    "gfx/interface/scripted_gui/eng/ENG_north_ireland_independent_gfx.dds",
]


def git(*args, cwd=REPO, capture=False):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else None


def copy_paths(md_root):
    for rel in ENG_PATHS:
        src = md_root / rel
        dst = REPO / rel
        if not src.exists():
            sys.exit(f"missing in MD checkout: {src}")
        if dst.is_dir():
            shutil.rmtree(dst)
        elif dst.exists():
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", default="D:/secondary-md", help="Millennium Dawn checkout")
    parser.add_argument("--no-merge", action="store_true", help="update md-base only")
    args = parser.parse_args()

    md_root = Path(args.md)
    if not (md_root / "descriptor.mod").exists():
        sys.exit(f"not an MD checkout: {md_root}")
    if git("status", "--porcelain", capture=True):
        sys.exit("working tree is dirty; commit or discard first")
    # CI checks out md_base_ref.txt from GitHub, so the synced files must match a pushed commit.
    if git("status", "--porcelain", "--", *ENG_PATHS, cwd=md_root, capture=True):
        sys.exit(f"ENG files have uncommitted changes in {md_root}")
    if not git("branch", "-r", "--contains", "HEAD", cwd=md_root, capture=True):
        sys.exit(f"HEAD of {md_root} is not on any remote branch; check out a pushed MD commit")

    md_hash = git("rev-parse", "--short", "HEAD", cwd=md_root, capture=True)
    md_full_hash = git("rev-parse", "HEAD", cwd=md_root, capture=True)
    start_branch = git("rev-parse", "--abbrev-ref", "HEAD", capture=True)

    git("checkout", "-q", "md-base")
    copy_paths(md_root)
    MD_BASE_REF.parent.mkdir(exist_ok=True)
    MD_BASE_REF.write_text(md_full_hash + "\n", encoding="utf-8", newline="")
    git("add", "-A", "--", *ENG_PATHS, MD_BASE_REF.relative_to(REPO).as_posix())
    if git("status", "--porcelain", capture=True):
        git("commit", "-q", "-m", f"Sync ENG files from MD {md_hash}")
        print(f"md-base updated to MD {md_hash}")
        changed = True
    else:
        print(f"md-base already matches MD {md_hash}")
        changed = False

    git("checkout", "-q", "main" if start_branch == "md-base" else start_branch)
    if changed and not args.no_merge:
        if subprocess.run(["git", "merge", "md-base"], cwd=REPO, check=False).returncode:
            sys.exit("merging md-base stopped on conflicts; resolve them, keeping md-base's tools/md_base_ref.txt")


if __name__ == "__main__":
    main()

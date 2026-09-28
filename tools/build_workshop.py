"""Stage a clean copy of the submod for Steam Workshop upload.

Copies only the owned game files, descriptor.mod and thumbnail.png into a sibling
folder and writes the launcher .mod file next to it. Upload that folder from the
Paradox launcher (Mod Tools > Upload Mod).

Usage: python tools/build_workshop.py [--out <folder>]
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_md_base import ENG_PATHS, ENG_SUBMOD_ONLY_PATHS, REPO

DEFAULT_OUT = REPO.parent / f"{REPO.name}-Workshop"
EXTRA_FILES = ["descriptor.mod", "thumbnail.png"]
MAX_THUMBNAIL_BYTES = 1024 * 1024


def descriptor_without_path(text):
    return "".join(line for line in text.splitlines(keepends=True) if not line.lstrip().startswith("path"))


def check_out(out):
    """Refuse any folder whose deletion would take real work with it."""
    if out == REPO or REPO in out.parents or out in REPO.parents:
        sys.exit(f"refusing to build in or above the repo: {out}")
    if (out / ".git").exists():
        sys.exit(f"refusing to replace a git checkout: {out}")
    if out.exists() and any(out.iterdir()) and not (out / "descriptor.mod").is_file():
        sys.exit(f"refusing to replace {out}: it is not an earlier Workshop build")


def remote_file_id_line(out):
    """The launcher writes remote_file_id after the first upload; later builds must keep it."""
    descriptor = out / "descriptor.mod"
    if descriptor.is_file():
        for line in descriptor.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("remote_file_id"):
                return line.strip() + "\n"
    return ""


def build(out):
    out = out.resolve()
    check_out(out)
    thumbnail = REPO / "thumbnail.png"
    if thumbnail.stat().st_size > MAX_THUMBNAIL_BYTES:
        sys.exit("thumbnail.png is over 1 MB; Steam rejects it")

    remote_file_id = remote_file_id_line(out)
    if out.exists():
        shutil.rmtree(out)
    for rel in ENG_PATHS + ENG_SUBMOD_ONLY_PATHS + EXTRA_FILES:
        src = REPO / rel
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    descriptor = descriptor_without_path((REPO / "descriptor.mod").read_text(encoding="utf-8"))
    descriptor = descriptor.rstrip("\n") + "\n" + remote_file_id
    (out / "descriptor.mod").write_text(descriptor, encoding="utf-8", newline="")
    launcher = descriptor.rstrip("\n") + f'\npath="{out.as_posix()}"\n'
    (out.parent / f"{out.name}.mod").write_text(launcher, encoding="utf-8", newline="")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="staging folder")
    args = parser.parse_args()
    out = build(args.out)
    print(f"staged {out}")


if __name__ == "__main__":
    main()

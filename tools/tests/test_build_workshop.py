import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_workshop as b


def test_descriptor_without_path_drops_only_path_line():
    text = 'version="1.0.0"\nname="UK"\npath="mod/UK"\nsupported_version="1.19.*"\n'
    assert b.descriptor_without_path(text) == 'version="1.0.0"\nname="UK"\nsupported_version="1.19.*"\n'


def test_build_refuses_repo_folder():
    with pytest.raises(SystemExit):
        b.build(b.REPO / "staging")


def test_build_stages_only_owned_files(tmp_path):
    if (b.REPO / "thumbnail.png").stat().st_size > b.MAX_THUMBNAIL_BYTES:
        pytest.skip("thumbnail too large to stage")
    out = b.build(tmp_path / "Workshop")
    assert (out / "descriptor.mod").exists()
    assert (out / "common/national_focus/05_united_kingdom.txt").exists()
    assert not (out / "tools").exists()
    assert not (out / ".claude").exists()
    assert "path=" not in (out / "descriptor.mod").read_text(encoding="utf-8")
    launcher = (tmp_path / "Workshop.mod").read_text(encoding="utf-8")
    assert f'path="{out.as_posix()}"' in launcher

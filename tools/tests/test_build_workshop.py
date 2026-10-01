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


def test_build_refuses_folder_above_the_repo():
    with pytest.raises(SystemExit):
        b.build(b.REPO.parent)


def test_build_refuses_non_workshop_folder(tmp_path):
    (tmp_path / "notes.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(SystemExit):
        b.build(tmp_path)
    assert (tmp_path / "notes.txt").exists()


def test_build_refuses_git_checkout(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "descriptor.mod").write_text('name="x"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        b.build(tmp_path)


def test_build_keeps_remote_file_id(tmp_path):
    if (b.REPO / "thumbnail.png").stat().st_size > b.MAX_THUMBNAIL_BYTES:
        pytest.skip("thumbnail too large to stage")
    out = tmp_path / "Workshop"
    out.mkdir()
    (out / "descriptor.mod").write_text('name="UK"\nremote_file_id="123456"\n', encoding="utf-8")
    b.build(out)
    assert 'remote_file_id="123456"' in (out / "descriptor.mod").read_text(encoding="utf-8")
    assert 'remote_file_id="123456"' in (tmp_path / "Workshop.mod").read_text(encoding="utf-8")

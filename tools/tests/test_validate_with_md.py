import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_with_md as v


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_is_owned_matches_owned_files_and_directories():
    assert v.is_owned("events/05_united_kingdom.txt")
    assert v.is_owned("D:\\md\\events\\05_united_kingdom.txt")
    assert v.is_owned("gfx/interface/goals/united_kingdom/foo.dds")
    assert not v.is_owned("events/05_germany.txt")
    assert not v.is_owned("")


def test_filter_sidecar_without_baseline_keeps_only_owned(tmp_path):
    sidecar = tmp_path / "validation-events.json"
    write_json(sidecar, [
        {"file": "events/05_united_kingdom.txt", "severity": "error"},
        {"file": "events/05_germany.txt", "severity": "error"},
    ])
    kept = v.filter_sidecar(sidecar, None, tmp_path)
    assert [i["file"] for i in kept] == ["events/05_united_kingdom.txt"]
    assert json.loads(sidecar.read_text(encoding="utf-8")) == kept


def manifest(status, strict=True):
    return {"results": [{"name": "events", "status": status, "strict": strict, "returncode": 1}]}


def test_filter_results_passes_when_only_unowned_errors(tmp_path):
    write_json(tmp_path / "core" / "validation-events.json", [{"file": "events/05_germany.txt", "severity": "error"}])
    write_json(tmp_path / "core" / "batch-manifest.json", manifest("findings"))
    issues, gating = v.filter_results(tmp_path, tmp_path, None)
    assert issues == []
    assert not gating
    entry = json.loads((tmp_path / "core" / "batch-manifest.json").read_text(encoding="utf-8"))["results"][0]
    assert entry["status"] == "ok"
    assert entry["returncode"] == 0


def test_filter_results_gates_on_owned_error(tmp_path):
    write_json(tmp_path / "core" / "validation-events.json", [{"file": "events/05_united_kingdom.txt", "severity": "error"}])
    write_json(tmp_path / "core" / "batch-manifest.json", manifest("findings"))
    _, gating = v.filter_results(tmp_path, tmp_path, None)
    assert gating


def test_filter_results_ignores_owned_error_from_non_strict_validator(tmp_path):
    write_json(tmp_path / "core" / "validation-events.json", [{"file": "events/05_united_kingdom.txt", "severity": "error"}])
    write_json(tmp_path / "core" / "batch-manifest.json", manifest("findings", strict=False))
    _, gating = v.filter_results(tmp_path, tmp_path, None)
    assert not gating


def test_filter_results_keeps_crash_status(tmp_path):
    write_json(tmp_path / "core" / "validation-events.json", [])
    write_json(tmp_path / "core" / "batch-manifest.json", manifest("crash"))
    v.filter_results(tmp_path, tmp_path, None)
    assert v.crashed_validators(tmp_path, ["core"]) == ["events"]


def test_crashed_validators_reports_missing_manifest(tmp_path):
    assert v.crashed_validators(tmp_path, ["core"]) == ["core (no manifest)"]

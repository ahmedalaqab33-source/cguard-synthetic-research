import pytest
from test_workflow import change, ready
from test_workflow import packet as packet

from cguard_research import workflow as w
from cguard_research.artifacts import (
    RESOURCES, GuardError, audit_events, file_hash, read_json, state, write_json)
from cguard_research.contracts import Plan

def test_release_record_tampering_is_detected(tmp_path):
    run = ready(tmp_path, human=True)
    w.execute(run)
    w.release(run, "TEST REVIEWER", "Only a test fixture attestation", human=True)
    record = read_json(run / "release.json")
    record["approval"]["reviewer"] = "Different person"
    write_json(run / "release.json", record)
    with pytest.raises(GuardError, match="Release"):
        w.verify(run)

def test_manifest_tampering_is_detected(tmp_path):
    run = ready(tmp_path)
    record = read_json(run / "manifest.json")
    record["dataset_id"] = "forged-dataset"
    write_json(run / "manifest.json", record)
    with pytest.raises(GuardError, match="manifest changed"):
        w.execute(run)

def test_runtime_change_invalidates_approval(tmp_path, monkeypatch):
    run = ready(tmp_path)
    original = w.environment()
    monkeypatch.setattr(w, "environment", lambda: {**original, "python": "0.0.0"})
    with pytest.raises(GuardError, match="Environment changed"):
        w.execute(run)
    assert state(run) == "VALIDATION_FAILED"

def test_code_snapshot_tampering_is_detected(tmp_path):
    run = ready(tmp_path)
    (run / "code/tools.py").write_text("# replaced")
    with pytest.raises(GuardError, match="code snapshot"):
        w.execute(run)

def test_denied_execution_is_audited(tmp_path):
    run = w.prepare(tmp_path / "run")
    with pytest.raises(GuardError):
        w.execute(run)
    assert audit_events(run)[-1]["action"] == "transition_denied"

def test_input_source_preserved_and_snapshot_independent(tmp_path, packet):
    initial = (packet / "cohort.csv").read_bytes()
    run = ready(tmp_path, packet)
    change(packet, "age_years", "99")
    # Approval names the stored input bytes, not a mutable external source path.
    assert (run / "inputs/cohort.csv").read_bytes() == initial
    assert w.execute(run)["groups"]["A"]["continuous"]["age_years"]["mean"] == 40

def test_skill_resources_have_required_contract_fields():
    paths = sorted((RESOURCES / "skills").glob("*.md"))
    assert len(paths) == 4
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for field in ["Purpose", "Scope", "Assumptions", "Rules", "Prohibited behavior",
                      "Validation requirements", "Tests", "References"]:
            assert "## " + field in text, (path.name, field)

def test_two_fresh_runs_reproduce_same_results(tmp_path):
    first = ready(tmp_path)
    w.execute(first)
    second = w.prepare(tmp_path / "second")
    w.approve(second, "TEST ACTOR", "Independent fresh simulation run", simulation=True)
    w.execute(second)
    assert file_hash(first / "results.json") == file_hash(second / "results.json")

def test_valid_external_plan_still_requires_approval(tmp_path):
    run = w.prepare(tmp_path / "run")
    proposal = tmp_path / "proposal.json"
    write_json(proposal, Plan(continuous=["age_years"]).model_dump())
    w.propose(run, proposal)
    with pytest.raises(GuardError):
        w.execute(run)
    w.approve(run, "TEST ACTOR", "Review of restricted synthetic plan", simulation=True)
    result = w.execute(run)
    assert list(result["groups"]["A"]["continuous"]) == ["age_years"]
    assert w.verify(run)["status"] == "PASS"

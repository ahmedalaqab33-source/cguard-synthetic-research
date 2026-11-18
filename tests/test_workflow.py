import csv
import io
import shutil

import pytest
from pydantic import ValidationError

from cguard_research import workflow as w
from cguard_research.artifacts import (
    RESOURCES, GuardError, audit_events, file_hash, read_json, state, write_json)
from cguard_research.cli import main
from cguard_research.contracts import Plan
from cguard_research.intake import inspect
from cguard_research.validators import validate

@pytest.fixture
def packet(tmp_path):
    target = tmp_path / "packet"
    target.mkdir()
    for name in w.INPUTS:
        shutil.copyfile(RESOURCES / name, target / name)
    return target

def change(packet, column, value, row=0):
    path = packet / "cohort.csv"
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    fields = list(rows[0])
    rows[row][column] = value
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def ready(tmp_path, packet=None, human=False):
    run = tmp_path / "run"
    w.prepare(run, packet)
    w.approve(run, "TEST ACTOR", "Automated test fixture; not actual human review",
              human=human, simulation=not human)
    return run

def test_golden_results_and_replay(tmp_path):
    run = ready(tmp_path)
    result = w.execute(run)
    assert result["total_n"] == 8
    a = result["groups"]["A"]
    assert a["continuous"]["age_years"] == {
        "n": 3, "missing": 1, "mean": 40.0, "sd": 20.0, "median": 40.0, "q1": 30.0, "q3": 50.0}
    assert a["outcome"] == {"events": 2, "observed": 3, "missing": 1, "proportion": 2 / 3}
    assert result["groups"]["B"]["outcome"]["proportion"] == 1 / 3
    assert w.verify(run)["status"] == "PASS"
    w.replay(run, tmp_path / "replay")
    assert file_hash(run / "results.json") == file_hash(tmp_path / "replay/replayed_results.json")
    assert state(run) == "REVIEW_PENDING"
    assert "SIMULATION" in (run / "report.md").read_text(encoding="utf-8")
    assert [e for e in audit_events(run) if e["action"] == "tool_started"]

def test_missing_approval_blocks_execution(tmp_path):
    run = w.prepare(tmp_path / "run")
    with pytest.raises(GuardError, match="State"):
        w.execute(run)
    assert not (run / "results.json").exists()

def test_no_attestation_blocks_approval(tmp_path):
    run = w.prepare(tmp_path / "run")
    with pytest.raises(GuardError, match="attestation"):
        w.approve(run, "Tester", "Reviewed synthetic fixture")

@pytest.mark.parametrize("artifact", ["inputs/cohort.csv", "plan.json", "qc.json"])
def test_changed_approved_artifact_is_rejected(tmp_path, artifact):
    run = ready(tmp_path)
    path = run / artifact
    if artifact.endswith(".csv"):
        path.write_text(path.read_text().replace("20,60", "21,60"))
    else:
        data = read_json(path)
        if artifact == "plan.json":
            data["rationale"] = "Changed after approval without permission"
        else:
            data["rows"] = 9
        write_json(path, data)
    with pytest.raises(GuardError, match="changed|Stale"):
        w.execute(run)
    assert state(run) == "VALIDATION_FAILED"
    assert not (run / "report.md").exists()

@pytest.mark.parametrize("column,value,rule", [
    ("age_years", "-1", "DQ_BOUND"), ("weight_kg", "NaN", "DQ_TYPE"),
    ("lab_value", "inf", "DQ_TYPE"), ("age_years", "unknown", "DQ_TYPE"),
    ("outcome", "2", "DQ_OUTCOME"), ("outcome", ".5", "DQ_TYPE"),
    ("group", "C", "DQ_GROUP"), ("participant_id", "Real Name", "DQ_ID"),
    ("index_day", "", "DQ_REQUIRED_TIME"), ("lab_day", "1", "LEAK_POST_INDEX"),
])
def test_invalid_input_rejection(tmp_path, packet, column, value, rule):
    change(packet, column, value)
    run = w.prepare(tmp_path / "run", packet)
    qc = read_json(run / "qc.json")
    assert rule in {f["rule"] for f in qc["findings"]}
    assert state(run) == "INPUT_REJECTED"
    with pytest.raises(GuardError):
        w.approve(run, "Tester", "Should never be accepted", simulation=True)

def test_duplicate_rows_are_detected_and_never_dropped(tmp_path, packet):
    path = packet / "cohort.csv"
    path.write_text(path.read_text() + path.read_text().splitlines()[1] + "\n")
    original = path.read_bytes()
    run = w.prepare(tmp_path / "run", packet)
    qc = read_json(run / "qc.json")
    assert qc["rows"] == 9 and qc["exact_duplicate_rows"] == 1 and qc["duplicate_ids"] == 1
    assert path.read_bytes() == original
    assert state(run) == "INPUT_REJECTED"

@pytest.mark.parametrize("header", ["participant_id,group,age_years,age_years", "patient_name,group"])
def test_bad_header_rejected(tmp_path, packet, header):
    path = packet / "cohort.csv"
    path.write_text(header + "\na,b,c,d\n")
    with pytest.raises(GuardError, match="header"):
        w.prepare(tmp_path / "run", packet)
    assert state(tmp_path / "run") == "INPUT_REJECTED"

def test_units_cannot_be_silently_changed(tmp_path, packet):
    data = read_json(packet / "dictionary.json")
    data["variables"]["weight_kg"]["units"] = "lb"
    write_json(packet / "dictionary.json", data)
    with pytest.raises(GuardError, match="units"):
        w.prepare(tmp_path / "run", packet)

def test_outlier_is_warning_not_deletion(packet):
    change(packet, "lab_value", "999")
    qc = inspect(packet)
    assert not qc["blocked"]
    assert "DQ_OUTLIER" in {f["rule"] for f in qc["findings"]}
    assert qc["rows"] == 8

def test_all_missing_and_singleton_are_explicit(tmp_path, packet):
    for row in range(4):
        change(packet, "lab_value", "", row)
        change(packet, "outcome", "", row)
        if row > 0:
            change(packet, "age_years", "", row)
    run = ready(tmp_path, packet)
    a = w.execute(run)["groups"]["A"]
    assert a["continuous"]["lab_value"]["mean"] is None
    assert a["continuous"]["age_years"]["sd"] is None
    assert a["outcome"]["observed"] == 0 and a["outcome"]["proportion"] is None

@pytest.mark.parametrize("mutate", [
    lambda x: x["groups"]["A"]["outcome"].update(observed=4),
    lambda x: x["groups"]["A"]["outcome"].update(proportion=.5),
    lambda x: x.update(total_n=9),
    lambda x: x["groups"]["A"]["continuous"]["age_years"].update(mean=41.0),
    lambda x: x["groups"]["A"].update(members=["SYN-999"]),
    lambda x: x["groups"]["A"]["continuous"].update(fake_variable={}),
    lambda x: x.update(interpretation="Group A treatment prevents disease."),
])
def test_independent_validator_rejects_plausible_corruption(tmp_path, monkeypatch, mutate):
    original = w.tools.summarize
    def corrupt(*args):
        result = original(*args)
        mutate(result)
        return result
    monkeypatch.setattr(w.tools, "summarize", corrupt)
    run = ready(tmp_path)
    with pytest.raises(GuardError, match="Validation"):
        w.execute(run)
    assert state(run) == "VALIDATION_FAILED"
    assert not (run / "report.md").exists()
    assert read_json(run / "validation_failure.json")["status"] == "FAIL"

def test_validator_crash_fails_closed(tmp_path, monkeypatch):
    run = ready(tmp_path)
    def crash(*args):
        raise RuntimeError("Independent check crashed")
    monkeypatch.setattr(w.validators, "validate", crash)
    with pytest.raises(RuntimeError):
        w.execute(run)
    assert state(run) == "VALIDATION_FAILED"
    assert not (run / "report.md").exists()

@pytest.mark.parametrize("artifact", w.OUTPUTS)
def test_tampered_report_or_result_blocks_release(tmp_path, artifact):
    run = ready(tmp_path, human=True)
    w.execute(run)
    path = run / artifact
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(GuardError, match="Output changed"):
        w.release(run, "TEST REVIEWER", "Test review attestation only", human=True)
    assert not (run / "release.json").exists()

def test_simulated_approval_can_never_release(tmp_path):
    run = ready(tmp_path)
    w.execute(run)
    with pytest.raises(GuardError, match="human"):
        w.release(run, "Tester", "Attempt to release simulation", human=True)

def test_two_human_attestations_release_in_test_fixture(tmp_path):
    run = ready(tmp_path, human=True)
    w.execute(run)
    with pytest.raises(GuardError):
        w.release(run, "TEST REVIEWER", "Test fixture only", human=False)
    w.release(run, "TEST REVIEWER", "Test fixture only", human=True)
    assert state(run) == "RELEASED"
    assert read_json(run / "release.json")["status"] == "RELEASED"
    assert w.verify(run)["status"] == "PASS"

@pytest.mark.parametrize("updates", [
    {"continuous": ["creatinine"]}, {"continuous": ["age_years", "age_years"]},
    {"missing_policy": "mean_imputation"}, {"population": "drop_outliers"},
    {"code": "print('untrusted')"}, {"interpretation": "causal"},
])
def test_unsupported_proposals_rejected(tmp_path, updates):
    run = w.prepare(tmp_path / "run")
    proposal = Plan().model_dump()
    proposal.update(updates)
    path = tmp_path / "proposal.json"
    write_json(path, proposal)
    with pytest.raises(ValidationError):
        w.propose(run, path)
    assert state(run) == "PLAN_PENDING"
    assert audit_events(run)[-1]["action"] == "proposal_rejected"

def test_audit_and_state_tampering_are_detected(tmp_path):
    run = ready(tmp_path)
    write_json(run / "state.json", {"state": "RELEASED"})
    with pytest.raises(GuardError, match="disagree"):
        w.execute(run)

def test_audit_chain_corruption(tmp_path):
    run = ready(tmp_path)
    path = run / "audit.jsonl"
    path.write_text(path.read_text().replace("TEST ACTOR", "FAKE ACTOR"))
    with pytest.raises(GuardError, match="Audit"):
        w.execute(run)

def test_approval_record_cannot_be_replaced(tmp_path):
    run = ready(tmp_path)
    approval = read_json(run / "plan_approval.json")
    approval["attestation"] = "human"
    write_json(run / "plan_approval.json", approval)
    with pytest.raises(GuardError, match="audit"):
        w.execute(run)

def test_row_permutation_preserves_results(tmp_path, packet):
    original = w.tools.summarize(packet, Plan())
    path = packet / "cohort.csv"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], *reversed(lines[1:])]) + "\n")
    permuted = w.tools.summarize(packet, Plan())
    assert permuted == original
    validate(packet, Plan(), permuted)

def test_lock_and_existing_run_prevent_overwrite(tmp_path):
    run = w.prepare(tmp_path / "run")
    with pytest.raises(FileExistsError):
        w.prepare(run)
    (run / ".lock").write_text("interrupted")
    with pytest.raises(GuardError, match="locked"):
        w.approve(run, "Tester", "No overwrite allowed", simulation=True)

def test_cli_demo_is_not_human_approval(tmp_path, capsys):
    assert main(["demo", str(tmp_path / "demo")]) == 0
    assert "SIMULATION" in capsys.readouterr().out
    assert read_json(tmp_path / "demo/demo_notice.json")["human_review"] is False

def test_nonfinite_and_duplicate_json_are_rejected(tmp_path):
    from cguard_research.artifacts import read_json
    path = tmp_path / "bad.json"
    path.write_text('{"x": 1, "x": 2}')
    with pytest.raises(GuardError, match="Duplicate"):
        read_json(path)
    path.write_text('{"x": NaN}')
    with pytest.raises(GuardError, match="finite"):
        read_json(path)

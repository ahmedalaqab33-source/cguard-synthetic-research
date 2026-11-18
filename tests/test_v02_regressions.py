"""Regressions for defects reproduced during the 0.1.0 audit."""

import pytest
from pydantic import ValidationError
from test_workflow import change, ready
from test_workflow import packet as packet

from cguard_research import workflow as w
from cguard_research.artifacts import (
    GuardError, RunLock, audit_events, canonical, digest, read_json,
    state, transition, write_json)
from cguard_research.cli import main
from cguard_research.contracts import Approval, Plan
from cguard_research.intake import inspect


@pytest.mark.parametrize("column,value", [
    ("outcome", "1.0000000000000000001"),
    ("index_day", "0.00000000000000000001"),
    ("lab_day", "-1.000000000000000001"),
    ("weight_kg", "1_00"),
    ("age_years", " 30"),
    ("age_years", "٣٠"),
    ("lab_value", "1e-9999"),
    ("lab_value", "9" * 65),
    ("age_years", "17.99999999999999999999"),
])
def test_numeric_grammar_and_exact_integer_boundaries(packet, column, value):
    change(packet, column, value)
    assert inspect(packet)["blocked"]


def test_changed_data_during_execution_never_produces_report(tmp_path, monkeypatch):
    run = ready(tmp_path)
    original = w.tools.summarize
    def mutate_before_computation(packet, plan):
        path = packet / "cohort.csv"
        path.write_text(path.read_text().replace("20,60,10", "30,60,10"))
        return original(packet, plan)
    monkeypatch.setattr(w.tools, "summarize", mutate_before_computation)
    with pytest.raises(GuardError, match="Input snapshot changed"):
        w.execute(run)
    assert state(run) == "VALIDATION_FAILED"
    assert not (run / "report.md").exists()
    assert not (run / "report.html").exists()


def test_changed_data_during_replay_has_no_success_artifact(tmp_path, monkeypatch):
    run = ready(tmp_path)
    w.execute(run)
    original = w.tools.summarize
    def mutate_after_computation(packet, plan):
        result = original(packet, plan)
        path = packet / "cohort.csv"
        path.write_text(path.read_text().replace("20,60,10", "30,60,10"))
        return result
    monkeypatch.setattr(w.tools, "summarize", mutate_after_computation)
    destination = tmp_path / "replay"
    with pytest.raises(GuardError):
        w.replay(run, destination)
    assert not (destination / "replay.json").exists()
    assert audit_events(run)[-1]["action"] == "replay_failed"


def test_verify_respects_mutation_lock(tmp_path):
    run = ready(tmp_path)
    w.execute(run)
    with RunLock(run):
        with pytest.raises(GuardError, match="locked"):
            w.verify(run)


def test_arbitrary_state_jump_is_rejected(tmp_path):
    run = w.prepare(tmp_path / "run")
    with pytest.raises(GuardError, match="Illegal state"):
        transition(run, "RELEASED")
    assert state(run) == "PLAN_PENDING"


def test_illegal_but_rehashed_history_is_rejected(tmp_path):
    run = w.prepare(tmp_path / "run")
    events = audit_events(run)
    event = {
        "sequence": len(events), "previous": events[-1]["hash"],
        "timestamp": events[-1]["timestamp"], "action": "state_transition",
        "details": {"state": "RELEASED"}}
    event["hash"] = digest(event)
    with (run / "audit.jsonl").open("ab") as stream:
        stream.write(canonical(event) + b"\n")
    with pytest.raises(GuardError, match="Illegal state"):
        audit_events(run)


@pytest.mark.parametrize("text", ['{"value":1e999}', '{"value":-1e999}', '{"value":NaN}'])
def test_json_exponent_overflow_is_rejected(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text)
    with pytest.raises(GuardError, match="finite"):
        read_json(path)


def test_truncated_audit_record_is_rejected(tmp_path):
    run = ready(tmp_path)
    path = run / "audit.jsonl"
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(GuardError, match="truncated"):
        w.execute(run)


@pytest.mark.parametrize("field,value", [("seed", False), ("schema_version", True), ("seed", 0.0)])
def test_plan_literals_are_not_coerced(field, value):
    with pytest.raises(ValidationError):
        Plan(**{field: value})


@pytest.mark.parametrize("field,value", [("reviewer", "  x  "), ("reason", "          "),
                                       ("reason", "long reason\nwith injection")])
def test_approval_text_is_meaningful(field, value):
    fields = dict(scope="plan", reviewer="Test operator", reason="A meaningful test reason",
                  attestation="simulation", binding="a" * 64, timestamp="2026-09-19T00:00:00+00:00")
    fields[field] = value
    with pytest.raises(ValidationError):
        Approval(**fields)


def test_warning_requires_exact_acknowledgement(tmp_path, packet):
    change(packet, "lab_value", "999")
    run = w.prepare(tmp_path / "run", packet)
    warnings = w.review(run)["warnings_requiring_acknowledgement"]
    assert warnings
    with pytest.raises(GuardError, match="warning"):
        w.approve(run, "TEST ACTOR", "Review without acknowledgement", simulation=True)
    with pytest.raises(GuardError, match="warning"):
        w.approve(run, "TEST ACTOR", "Wrong acknowledgement supplied", simulation=True,
                  acknowledgements=["made-up-id"])
    ids = [f["id"] for f in warnings]
    record = w.approve(run, "TEST ACTOR", "Reviewed every retained synthetic outlier",
                       simulation=True, acknowledgements=ids)
    assert sorted(record.warning_acknowledgements) == sorted(ids)
    w.execute(run)


def test_zero_mad_deviation_is_flagged_without_removal(packet):
    for row in range(8):
        change(packet, "lab_value", "10" if row < 7 else "20", row)
    qc = inspect(packet)
    assert qc["rows"] == 8 and not qc["blocked"]
    assert "DQ_ZERO_MAD_DEVIATION" in {f["rule"] for f in qc["findings"]}


def test_rejected_qc_returns_nonzero_cli_exit(tmp_path, packet):
    change(packet, "outcome", "2")
    assert main(["prepare", str(tmp_path / "run"), "--packet", str(packet)]) == 2


def test_cancellation_retains_evidence_and_blocks_execution(tmp_path):
    run = ready(tmp_path)
    original = (run / "inputs/cohort.csv").read_bytes()
    w.cancel(run, "Researcher withdrew this proposed analysis")
    assert state(run) == "CANCELLED"
    assert (run / "inputs/cohort.csv").read_bytes() == original
    with pytest.raises(GuardError):
        w.execute(run)


def test_released_run_cannot_be_cancelled_retroactively(tmp_path):
    run = ready(tmp_path, human=True)
    w.execute(run)
    w.release(run, "TEST ACTOR", "Automated test; no actual human review", human=True)
    with pytest.raises(GuardError):
        w.cancel(run, "Attempt to erase released status")
    assert state(run) == "RELEASED"


def test_html_is_verified_and_has_no_external_dependencies(tmp_path):
    from html.parser import HTMLParser
    class Evidence(HTMLParser):
        def __init__(self):
            super().__init__()
            self.pointers = []
            self.scripts = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if "data-evidence" in attrs:
                self.pointers.append(attrs["data-evidence"])
            if tag == "script":
                self.scripts.append(attrs)
    run = ready(tmp_path)
    result = w.execute(run)
    parser = Evidence()
    text = (run / "report.html").read_text(encoding="utf-8")
    parser.feed(text)
    assert not parser.scripts and "https://" not in text
    assert set(parser.pointers) == {c["pointer"] for c in read_json(run / "claims.json")}
    for pointer in parser.pointers:
        value = result
        for key in pointer.strip("/").split("/"):
            value = value[key]
    assert w.verify(run)["status"] == "PASS"


def test_linked_artifact_rejected_when_os_supports_symlinks(tmp_path):
    from cguard_research.artifacts import bounded_bytes
    target, link = tmp_path / "target", tmp_path / "link"
    target.write_bytes(b"test")
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Host account cannot create symlinks")
    with pytest.raises(GuardError, match="Linked"):
        bounded_bytes(link)


def test_malformed_csv_is_a_controlled_rejection(tmp_path, packet):
    path = packet / "cohort.csv"
    header = path.read_text().splitlines()[0]
    path.write_text(header + '\n"SYN-001,A,30,70,10,1,0,0\n')
    assert main(["prepare", str(tmp_path / "run"), "--packet", str(packet)]) == 2


def test_modified_readable_qc_blocks_approval(tmp_path):
    run = w.prepare(tmp_path / "run")
    (run / "qc.md").write_text("Everything approved", encoding="utf-8")
    with pytest.raises(GuardError, match="QC review artifact changed"):
        w.approve(run, "TEST ACTOR", "Synthetic approval for regression test", simulation=True)
    assert state(run) == "PLAN_PENDING"


def test_status_rejects_state_cache_disagreement(tmp_path):
    run = w.prepare(tmp_path / "run")
    write_json(run / "state.json", {"state": "RELEASED"})
    assert main(["status", str(run)]) == 2


@pytest.mark.parametrize("seed", range(12))
def test_varied_synthetic_cohorts_match_independent_oracle(packet, seed):
    import csv
    import random
    from cguard_research import tools, validators
    rng = random.Random(seed)
    path = packet / "cohort.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        fields = csv.DictReader(stream).fieldnames
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index in range(1 + seed * 3):
            writer.writerow({
                "participant_id": f"SYN-{index + 1:03d}", "group": rng.choice(["A", "B"]),
                "age_years": rng.choice(["", str(rng.randint(18, 90))]),
                "weight_kg": rng.choice(["", f"{rng.uniform(50, 100):.3f}"]),
                "lab_value": rng.choice(["", f"{rng.uniform(1, 100):.3f}"]),
                "outcome": rng.choice(["", "0", "1"]), "index_day": "0", "lab_day": "-1"})
    assert not inspect(packet)["blocked"]
    assert validators.validate(packet, Plan(), tools.summarize(packet, Plan()))["status"] == "PASS"

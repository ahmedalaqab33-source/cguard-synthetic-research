"""Approval and release controller. Trusted local operator; no LLM write capability."""
import shutil
from pathlib import Path

from . import intake, reporting, tools, validators
from .artifacts import (PACKAGE, RESOURCES, GuardError, RunLock, audit_events, code_files,
                        code_hash, digest, environment, event, file_hash, now,
                        read_json, write_json, write_bytes, bounded_bytes, safe_path,
                        state, transition, check_state as _check_state)
from .contracts import Approval, Plan

INPUTS = ["cohort.csv", "dictionary.json", "protocol.json"]
OUTPUTS = ["results.json", "validation.json", "claims.json", "report.md", "report.html"]


def check_state(run, allowed):
    try:
        _check_state(run, allowed)
    except GuardError:
        # Only append if the existing chain itself remains trustworthy.
        audit_events(run)
        event(run, "transition_denied", allowed=sorted(allowed))
        raise


def binding(run):
    run = Path(run)
    return digest({
        "inputs": {name: file_hash(run / "inputs" / name) for name in INPUTS},
        "plan": read_json(run / "plan.json"), "qc": read_json(run / "qc.json"),
        "code": code_hash(), "environment": environment()})


def integrity(run):
    run = Path(run)
    audit_events(run)
    manifest = read_json(run / "manifest.json")
    anchors = [e for e in audit_events(run) if e["action"] == "manifest_recorded"]
    if not anchors or anchors[-1]["details"]["hash"] != file_hash(run / "manifest.json"):
        raise GuardError("Input manifest changed")
    for name, expected in manifest["inputs"].items():
        if name not in INPUTS or file_hash(run / "inputs" / name) != expected:
            raise GuardError("Input snapshot changed: " + name)
    if set(manifest["inputs"]) != set(INPUTS):
        raise GuardError("Incomplete input manifest")
    if manifest["code_hash"] != code_hash():
        raise GuardError("Code or skill version changed; create a new run")
    if manifest["environment"] != environment():
        raise GuardError("Environment changed; exact replay requires recorded environment")
    if (run / "qc.json").exists():
        expected_qc = reporting.quality_report(read_json(run / "qc.json"))
        if bounded_bytes(run / "qc.md").decode("utf-8") != expected_qc:
            raise GuardError("QC review artifact changed")
    snapshot = {p.relative_to(run / "code").as_posix(): file_hash(p)
                for p in (run / "code").rglob("*") if p.is_file()}
    if digest(snapshot) != manifest["code_hash"]:
        raise GuardError("Archived code snapshot changed")
    return manifest


def _approve_record(run, scope, reviewer, reason, attestation, value, acknowledgements=None):
    record = Approval(scope=scope, reviewer=reviewer, reason=reason, attestation=attestation,
                      binding=value, timestamp=now(), warning_acknowledgements=acknowledgements or [])
    write_json(run / (scope + "_approval.json"), record.model_dump())
    event(run, "approval_recorded", **record.model_dump())
    return record


def _approval(run):
    path = run / "plan_approval.json"
    if not path.exists():
        raise GuardError("Missing plan approval")
    record = Approval.model_validate(read_json(path))
    if record.scope != "plan" or record.binding != binding(run):
        raise GuardError("Stale approval: data, plan, QC, code or environment changed")
    entries = [e["details"] for e in audit_events(run) if e["action"] == "approval_recorded"
               and e["details"].get("scope") == "plan"]
    if not entries or entries[-1] != record.model_dump():
        raise GuardError("Approval is not recorded in audit")
    return record


def prepare(run, packet=None):
    run = safe_path(run)
    run.mkdir(parents=True, exist_ok=False)
    packet = Path(packet) if packet else RESOURCES
    with RunLock(run):
        transition(run, "RECEIVED")
        try:
            target = run / "inputs"
            target.mkdir()
            for name in INPUTS:
                source = packet / name
                write_bytes(target / name, bounded_bytes(source))
            # Auditable snapshot of the executed package, including skill policy resources.
            for source in code_files():
                destination = run / "code" / source.relative_to(PACKAGE)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            write_json(run / "manifest.json", {
                "schema_version": 1, "created_utc": now(),
                "dataset_id": "synthetic-cohort-v1", "source_kind": "synthetic_declared",
                "inputs": {name: file_hash(target / name) for name in INPUTS},
                "code_hash": code_hash(), "environment": environment(),
                "seed": 0, "source_policy": "Only synthetic data; declaration is not proof of anonymity"})
            event(run, "manifest_recorded", hash=file_hash(run / "manifest.json"))
            qc = intake.inspect(target)
            write_json(run / "qc.json", qc)
            write_bytes(run / "qc.md", reporting.quality_report(qc).encode("utf-8"))
            event(run, "tool_completed", tool="intake.inspect", inputs=INPUTS, output="qc.json")
            if qc["blocked"]:
                transition(run, "INPUT_REJECTED")
                return run
            write_json(run / "plan.json", Plan().model_dump())
            event(run, "plan_proposed", provider="deterministic_template", output="plan.json")
            transition(run, "PLAN_PENDING")
            return run
        except Exception as exc:
            event(run, "input_failure", error_type=type(exc).__name__, message=str(exc)[:500])
            transition(run, "INPUT_REJECTED")
            raise


def propose(run, proposal):
    run = Path(run)
    with RunLock(run):
        check_state(run, {"PLAN_PENDING"})
        integrity(run)
        try:
            candidate = Plan.model_validate(read_json(proposal))
            write_json(run / "plan.json", candidate.model_dump())
            event(run, "plan_proposed", provider="external_structured_proposal",
                  proposal_hash=file_hash(proposal), output="plan.json")
        except Exception as exc:
            event(run, "proposal_rejected", error_type=type(exc).__name__)
            raise


def approve(run, reviewer, reason, human=False, simulation=False, acknowledgements=None):
    run = Path(run)
    with RunLock(run):
        check_state(run, {"PLAN_PENDING"})
        integrity(run)
        Plan.model_validate(read_json(run / "plan.json"))
        qc = intake.inspect(run / "inputs")
        if qc["blocked"] or qc != read_json(run / "qc.json"):
            raise GuardError("QC does not match validated inputs")
        if type(human) is not bool or type(simulation) is not bool or human == simulation:
            event(run, "approval_denied", reason="Missing or contradictory attestation")
            raise GuardError("Choose explicit human attestation or simulation approval")
        warning_ids = sorted(f["id"] for f in qc["findings"] if f["severity"] == "WARNING")
        if sorted(acknowledgements or []) != warning_ids:
            event(run, "approval_denied", reason="Every warning must be explicitly acknowledged",
                  required=warning_ids)
            raise GuardError("Acknowledge each QC warning ID before approval: " + ", ".join(warning_ids))
        record = _approve_record(run, "plan", reviewer, reason,
                                 "human" if human else "simulation", binding(run), warning_ids)
        transition(run, "PLAN_APPROVED")
        return record


def execute(run):
    run = Path(run)
    with RunLock(run):
        check_state(run, {"PLAN_APPROVED"})
        try:
            integrity(run)
            approval = _approval(run)
            plan = Plan.model_validate(read_json(run / "plan.json"))
            if intake.inspect(run / "inputs")["blocked"]:
                raise GuardError("Input checks now fail")
            transition(run, "EXECUTING")
            event(run, "tool_started", tool="summarize", arguments=plan.model_dump())
            result = tools.summarize(run / "inputs", plan)
            write_json(run / "results.json", result)
            event(run, "tool_completed", tool="summarize", output="results.json",
                  output_hash=file_hash(run / "results.json"))
            validation = validators.validate(run / "inputs", plan, result)
            # Recheck the exact approved snapshot AFTER both implementations run.
            # A producer/verifier agreeing on concurrently changed data is not enough.
            integrity(run)
            _approval(run)
            write_json(run / "validation.json", validation)
            event(run, "validation_completed", **validation)
            report, claims = reporting.render(result, approval.binding, approval.attestation == "simulation")
            write_bytes(run / "report.md", report.encode("utf-8"))
            write_bytes(run / "report.html", reporting.html_report(
                result, approval.binding, approval.attestation == "simulation").encode("utf-8"))
            write_json(run / "claims.json", claims)
            write_json(run / "output_manifest.json", {name: file_hash(run / name) for name in OUTPUTS})
            event(run, "report_created", output="report.md", status="draft",
                  manifest_hash=file_hash(run / "output_manifest.json"))
            transition(run, "REVIEW_PENDING")
            return result
        except Exception as exc:
            write_json(run / "validation_failure.json", {
                "status": "FAIL", "error_type": type(exc).__name__, "reason": str(exc)[:500]})
            event(run, "execution_rejected", error_type=type(exc).__name__, message=str(exc)[:500])
            transition(run, "VALIDATION_FAILED")
            raise


def _verify(run):
    run = Path(run)
    _check_state(run, {"REVIEW_PENDING", "RELEASED"})
    integrity(run)
    approval = _approval(run)
    plan = Plan.model_validate(read_json(run / "plan.json"))
    manifest = read_json(run / "output_manifest.json")
    if set(manifest) != set(OUTPUTS):
        raise GuardError("Incomplete output manifest")
    for name, expected in manifest.items():
        if file_hash(run / name) != expected:
            raise GuardError("Output changed: " + name)
    entries = [e for e in audit_events(run) if e["action"] == "report_created"]
    if not entries or entries[-1]["details"]["manifest_hash"] != file_hash(run / "output_manifest.json"):
        raise GuardError("Output manifest changed")
    result = read_json(run / "results.json")
    validation = validators.validate(run / "inputs", plan, result)
    if read_json(run / "validation.json") != validation:
        raise GuardError("Validation artifact mismatch")
    report, claims = reporting.render(result, approval.binding, approval.attestation == "simulation")
    if (run / "report.md").read_text(encoding="utf-8") != report or read_json(run / "claims.json") != claims:
        raise GuardError("Report/claim evidence mismatch")
    expected_html = reporting.html_report(result, approval.binding, approval.attestation == "simulation")
    if bounded_bytes(run / "report.html").decode("utf-8") != expected_html:
        raise GuardError("HTML report evidence mismatch")
    if state(run) == "RELEASED":
        release_record = Approval.model_validate(read_json(run / "release_approval.json"))
        expected_binding = digest({"plan_approval": approval.model_dump(), "outputs": manifest})
        entries = [e["details"] for e in audit_events(run) if e["action"] == "approval_recorded"
                   and e["details"].get("scope") == "release"]
        if (approval.attestation != "human" or release_record.attestation != "human"
                or release_record.scope != "release" or release_record.binding != expected_binding
                or not entries or entries[-1] != release_record.model_dump()):
            raise GuardError("Release approval mismatch")
        release_artifact = read_json(run / "release.json")
        if release_artifact != {"status": "RELEASED", "approval": release_record.model_dump(),
                                "report": "report.md",
                                "note": "Approval attestation; not clinical certification"}:
            raise GuardError("Release artifact mismatch")
    return validation


def verify(run):
    run = Path(run)
    with RunLock(run):
        return _verify(run)


def release(run, reviewer, reason, human=False):
    run = Path(run)
    with RunLock(run):
        check_state(run, {"REVIEW_PENDING"})
        _verify(run)
        approval = _approval(run)
        if human is not True or approval.attestation != "human":
            event(run, "release_denied", reason="Human attestations required")
            raise GuardError("Release requires human plan approval and human release attestation")
        value = digest({"plan_approval": approval.model_dump(),
                        "outputs": read_json(run / "output_manifest.json")})
        record = _approve_record(run, "release", reviewer, reason, "human", value)
        write_json(run / "release.json", {"status": "RELEASED", "approval": record.model_dump(),
                   "report": "report.md", "note": "Approval attestation; not clinical certification"})
        transition(run, "RELEASED")
        return record


def _replay(run, destination):
    run, destination = Path(run), Path(destination)
    _verify(run)
    destination = safe_path(destination)
    # A replay must never create output inside input, code or another evidence directory.
    if destination.is_relative_to(run.absolute()) and destination.parent != run.absolute():
        raise GuardError("Replay destination cannot be nested in protected run artifacts")
    destination.mkdir(parents=True, exist_ok=False)
    plan = Plan.model_validate(read_json(run / "plan.json"))
    result = tools.summarize(run / "inputs", plan)
    validators.validate(run / "inputs", plan, result)
    validators.compare(result, read_json(run / "results.json"))
    integrity(run)
    _approval(run)
    write_json(destination / "replayed_results.json", result)
    write_json(destination / "replay.json", {
        "status": "PASS", "source_result_hash": file_hash(run / "results.json"),
        "replayed_result_hash": file_hash(destination / "replayed_results.json"),
        "environment": environment(), "code_hash": code_hash(), "timestamp": now(),
        "approval": "Reexecution of exactly the recorded approved plan; no new analysis"})
    return result


def replay(run, destination):
    run = Path(run).absolute()
    with RunLock(run):
        event(run, "replay_started", tool="summarize", approved_plan_hash=digest(read_json(run / "plan.json")))
        try:
            result = _replay(run, destination)
            event(run, "replay_completed", result_hash=digest(result))
            return result
        except Exception as exc:
            event(run, "replay_failed", error_type=type(exc).__name__)
            raise


def review(run):
    run = Path(run)
    with RunLock(run):
        _check_state(run, {"PLAN_PENDING", "PLAN_APPROVED", "REVIEW_PENDING", "RELEASED"})
        integrity(run)
        qc = intake.inspect(run / "inputs")
        if qc != read_json(run / "qc.json"):
            raise GuardError("QC does not match inputs")
        return {"state": state(run), "binding": binding(run), "plan": read_json(run / "plan.json"),
                "warnings_requiring_acknowledgement": [f for f in qc["findings"] if f["severity"] == "WARNING"],
                "review_checklist": ["Synthetic origin", "Protocol and units", "Missing outcome denominator",
                                     "All QC warnings", "Descriptive scope; no causal conclusions"],
                "human_attestation_is_not_authentication": True}


def cancel(run, reason):
    run = Path(run)
    if not isinstance(reason, str) or len(reason.strip()) < 10:
        raise GuardError("Cancellation requires a meaningful reason")
    with RunLock(run):
        check_state(run, {"PLAN_PENDING", "PLAN_APPROVED", "REVIEW_PENDING"})
        event(run, "cancelled_by_operator", reason=reason.strip())
        transition(run, "CANCELLED")


def status_report(run):
    from .artifacts import TRANSITIONS
    run = Path(run)
    with RunLock(run):
        _check_state(run, set(TRANSITIONS) - {None})
        return {"state": state(run), "check": "audit and state agree; use verify for result integrity"}

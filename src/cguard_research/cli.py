"""Local human-operated CLI. External planners may submit JSON, not commands."""
import argparse
import json
from pathlib import Path
from . import workflow
from .artifacts import GuardError, state, write_json
from .contracts import Plan
from . import __version__

def parser():
    root = argparse.ArgumentParser(description="Synthetic research prototype; not patient-care software")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Snapshot inputs, inspect QC and propose a fixed plan")
    prepare.add_argument("run", type=Path)
    prepare.add_argument("--packet", type=Path)
    propose = commands.add_parser("propose", help="Validate an external structured JSON proposal")
    propose.add_argument("run", type=Path)
    propose.add_argument("proposal", type=Path)
    approve = commands.add_parser("approve", help="Record a human or explicitly simulated plan approval")
    approve.add_argument("run", type=Path)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--reason", required=True)
    approve.add_argument("--ack-warning", action="append", default=[], help="QC warning ID; repeat for each")
    attest = approve.add_mutually_exclusive_group(required=True)
    attest.add_argument("--attest-human", action="store_true")
    attest.add_argument("--simulation", action="store_true")
    for name in ["execute", "verify", "status", "review"]:
        item = commands.add_parser(name)
        item.add_argument("run", type=Path)
    cancel = commands.add_parser("cancel", help="Stop a pending run and retain all evidence")
    cancel.add_argument("run", type=Path)
    cancel.add_argument("--reason", required=True)
    release = commands.add_parser("release", help="Attest human review of the exact validated report")
    release.add_argument("run", type=Path)
    release.add_argument("--reviewer", required=True)
    release.add_argument("--reason", required=True)
    release.add_argument("--attest-human", action="store_true", required=True)
    replay = commands.add_parser("replay")
    replay.add_argument("run", type=Path)
    replay.add_argument("destination", type=Path)
    demo = commands.add_parser("demo", help="Simulated approvals only; release remains forbidden")
    demo.add_argument("run", type=Path)
    commands.add_parser("plan-schema")
    commands.add_parser("doctor", help="Print runtime versions and source fingerprint without secrets")
    return root

def main(argv=None):
    args = parser().parse_args(argv)
    try:
        match args.command:
            case "prepare":
                workflow.prepare(args.run, args.packet)
                print(state(args.run))
                if state(args.run) == "INPUT_REJECTED":
                    return 2
            case "propose":
                workflow.propose(args.run, args.proposal)
                print("Proposal validated; human approval still required")
            case "approve":
                workflow.approve(args.run, args.reviewer, args.reason,
                                 human=args.attest_human, simulation=args.simulation,
                                 acknowledgements=args.ack_warning)
                print("PLAN_APPROVED")
            case "execute":
                workflow.execute(args.run)
                print("REVIEW_PENDING")
            case "verify":
                print(json.dumps(workflow.verify(args.run), indent=2))
            case "release":
                workflow.release(args.run, args.reviewer, args.reason, human=args.attest_human)
                print("RELEASED; approval recorded in release.json")
            case "status":
                print(json.dumps(workflow.status_report(args.run), indent=2))
            case "doctor":
                from .artifacts import code_hash, environment
                print(json.dumps({"version": __version__, "environment": environment(),
                                  "source_hash": code_hash(), "live_llm": False}, indent=2))
            case "review":
                print(json.dumps(workflow.review(args.run), indent=2))
            case "cancel":
                workflow.cancel(args.run, args.reason)
                print("CANCELLED; all artifacts retained")
            case "replay":
                workflow.replay(args.run, args.destination)
                print("Replay PASS")
            case "plan-schema":
                print(json.dumps(Plan.model_json_schema(), indent=2))
            case "demo":
                workflow.prepare(args.run)
                workflow.approve(args.run, "SIMULATION", "Synthetic software test, not human review",
                                 simulation=True)
                workflow.execute(args.run)
                workflow.verify(args.run)
                workflow.replay(args.run, args.run / "replay")
                write_json(args.run / "demo_notice.json", {
                    "human_review": False, "release_permitted": False,
                    "status": "Software demonstration only; not benchmark evidence"})
                print("Demo verified and replayed. SIMULATION; release forbidden.")
        return 0
    except (GuardError, ValueError, OSError, KeyError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())

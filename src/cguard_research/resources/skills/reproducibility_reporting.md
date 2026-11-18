# reproducibility_reporting

Version: 1.0.0
Review status: engineering prototype; domain review required before scope expansion.

## Purpose
Bind approval to evidence and preserve a reproducible research record.

## Scope
Synthetic-cohort-v1 only. No clinical care, dosing, prediction or causal inference.

## Assumptions
Trusted local operator; no authenticated service or external audit anchor.

## Rules
Rule IDs: REP_APPROVAL_BINDING, REP_EVIDENCE_LINK, REP_REPLAY, REP_HUMAN_RELEASE

Archive exact inputs/source, record runtime versions and all transitions, require approval before execution, independently validate and replay, and map report numbers to results.json pointers. Require a separate human release attestation.

## Prohibited behavior
Never call simulated approval human review, describe a hash chain as tamper-proof, suppress rejected runs or claim clinical validation from fixture tests.

## Validation requirements
The controller must enforce applicable rules; prompt agreement is not a validator. Reject ERROR conditions, preserve WARNING findings for human review, and record unsupported checks as NOT_APPLICABLE or NOT_EVALUATED.

## Tests
tests/test_workflow.py: test_changed_approved_artifact_is_rejected, test_tampered_report_or_result_blocks_release, test_simulated_approval_can_never_release, test_golden_results_and_replay

## References
https://github.com/AIML-SIG/Agentic-workflows/blob/5bd31238f0b658c18baf07a5fdeedb77a32b4075/tools/pharmbench/README.md

Access/review date: 2026-09-17. No clinical guideline is claimed. Scenario bounds are specified in resources/dictionary.json.


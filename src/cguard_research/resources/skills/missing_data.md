# missing_data

Version: 1.0.0
Review status: engineering prototype; domain review required before scope expansion.

## Purpose
Preserve missingness and make every denominator explicit.

## Scope
Synthetic-cohort-v1 only. No clinical care, dosing, prediction or causal inference.

## Assumptions
Blank cells represent unknown values. Other tokens must parse or be rejected.

## Rules
Rule IDs: MD_OBSERVED_DENOMINATOR, MD_NO_IMPUTATION

Use observed values per variable; record n and missing. Use observed outcomes as the outcome denominator. Zero observed values produce null, not zero; SD needs at least two observations.

## Prohibited behavior
Never classify a missing outcome as no event, infer MCAR/MAR from the fixture, or impute.

## Validation requirements
The controller must enforce applicable rules; prompt agreement is not a validator. Reject ERROR conditions, preserve WARNING findings for human review, and record unsupported checks as NOT_APPLICABLE or NOT_EVALUATED.

## Tests
tests/test_workflow.py: test_golden_results_and_replay, test_all_missing_and_singleton_are_explicit, test_independent_validator_rejects_plausible_corruption

## References
Internal synthetic protocol v1; these rules define a descriptive estimand, not a population-level missing-data solution.

Access/review date: 2026-09-17. No clinical guideline is claimed. Scenario bounds are specified in resources/dictionary.json.


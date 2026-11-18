# statistical_integrity

Version: 1.0.0
Review status: engineering prototype; domain review required before scope expansion.

## Purpose
Limit v0 to verified descriptive statistics.

## Scope
Synthetic-cohort-v1 only. No clinical care, dosing, prediction or causal inference.

## Assumptions
No inferential model is fitted. The protocol fixes the population and variables.

## Rules
Rule IDs: STAT_ALLOWED_METHODS, STAT_INDEPENDENT_CHECK, STAT_NO_CAUSAL_CLAIMS

Use sample SD with n-1 and linear quantiles. Validate exact counts/cohorts and every numerical result using the separate CSV/Decimal oracle. Fail closed on validator error.

## Prohibited behavior
Never fabricate variables or results, run arbitrary code, select tests, estimate treatment effects or interpret associations causally.

## Validation requirements
The controller must enforce applicable rules; prompt agreement is not a validator. Reject ERROR conditions, preserve WARNING findings for human review, and record unsupported checks as NOT_APPLICABLE or NOT_EVALUATED.

## Tests
tests/test_workflow.py: test_unsupported_proposals_rejected, test_independent_validator_rejects_plausible_corruption, test_validator_crash_fails_closed

## References
https://pmc.ncbi.nlm.nih.gov/articles/PMC6492164/

Access/review date: 2026-09-17. No clinical guideline is claimed. Scenario bounds are specified in resources/dictionary.json.


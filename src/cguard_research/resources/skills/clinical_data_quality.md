# clinical_data_quality

Version: 1.1.0
Review status: engineering prototype; domain review required before scope expansion.

## Purpose
Inspect the supported synthetic cohort without changing observations.

## Scope
Synthetic-cohort-v1 only. No clinical care, dosing, prediction or causal inference.

## Assumptions
One record per synthetic participant; reviewed units and time origin.

## Rules
Rule IDs: DQ_ID, DQ_GROUP, DQ_TYPE, DQ_BOUND, DQ_OUTCOME, DQ_REQUIRED_TIME, DQ_DUPLICATE_ID, DQ_OUTLIER, LEAK_POST_INDEX

Reject ambiguous headers, invalid encodings/types, impossible scenario values and duplicate IDs. Baseline lab_day must be no later than index_day. Flag robust outliers for review, including DQ_ZERO_MAD_DEVIATION when the median absolute deviation is zero but values differ. Every warning must be acknowledged by its stable finding ID before approval.

Parse bounded ASCII numeric tokens with exact Decimal checks before conversion. Integer fields must be exactly integral. Tokens are limited to 64 characters, 15 coefficient digits and nonzero adjusted exponents from -12 to 12. These are engineering limits for this synthetic protocol, not clinical reference ranges. Do not silently round, trim, normalize or underflow unsupported values.

## Prohibited behavior
Never silently delete duplicates, infer units or normalize an unexpected schema.

## Validation requirements
The controller must enforce applicable rules; prompt agreement is not a validator. Reject ERROR conditions, preserve WARNING findings for human review, and record unsupported checks as NOT_APPLICABLE or NOT_EVALUATED.

## Tests
tests/test_workflow.py: test_invalid_input_rejection, test_duplicate_rows_are_detected_and_never_dropped, test_bad_header_rejected, test_units_cannot_be_silently_changed, test_outlier_is_warning_not_deletion

## References
https://github.com/ahmedalaqab33-source/clinical-data-analysis-pipeline/blob/9b162f5d202527bb02256b5a659c35073e48e9a9/documentation/methodology.md

Access/review date: 2026-09-17. No clinical guideline is claimed. Scenario bounds are specified in resources/dictionary.json.

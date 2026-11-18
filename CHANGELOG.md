# Version 0.2.0 — 19 September 2026

This release fixes two defects reproduced against v0.1: fractional integer tokens could round into accepted values, and input changes during computation could pass an initial approval check. Exact Decimal checks now precede conversion; execute and replay recheck approval binding after computation.

- Reject non-ASCII numeric forms, whitespace, underscores, nonfinite JSON, underflow and excessive precision. Numeric tokens allow at most 64 characters and 15 coefficient digits; nonzero adjusted exponent must lie in [-12, 12]. These are synthetic-protocol engineering limits.
- Validate legal audit transitions and strict event structure; reject incomplete log records.
- Use bounded artifact reads and atomic durable replacement; reject linked/reparse paths.
- Require every QC warning ID to be acknowledged; flag differing values when median absolute deviation is zero.
- Add review, cancel, doctor and integrity-aware status commands. QC rejection returns a nonzero CLI exit.
- Add readable QC and a responsive, script-free HTML report with numerical evidence pointers.
- Add fault-injection, malformed-input, state, review and varied-cohort regression tests.

Compatibility: source/skill changes invalidate old bindings by design. Create a fresh v0.2 run and approval. Preserved v0.1 examples require the v0.1 wheel. Reports remain research demonstrations on invented data; no live model, comparative agent benchmark or clinical validation is claimed.

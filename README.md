# Approval-bound synthetic research workflow

Existing ClinicalGuard Research Prototype 0.2.0, authored and MIT-licensed by Ahmed Alaqab.
The provisional Python package is cguard_research (CLI: cguard); it is unrelated to the
existing PyPI project named clinicalguard. No PyPI publication occurs in this release.

## Purpose and distinction

This experimental software controls a synthetic descriptive-analysis run through intake,
QC, typed plan proposals, explicit operator attestations, predefined pandas calculations,
independent CSV/Decimal verification, evidence-linked reporting, integrity checks and replay.
Its state controller, artifact bindings and fault/tamper regressions are a separate
implementation from the existing clinical-data-analysis-pipeline CSV utility, which is an
architectural reference. It is not a module uploaded from that repository.

No live LLM adapter, clinical decision, prediction model or causal estimation is implemented.
Approval flags are local attestations, not authenticated identity, ethics approval or
institutional authorization. A trusted local user can rewrite an entire directory; the audit
chain is not an external trust anchor or OS sandbox. See docs/threat-model.md.

## Requirements and installation

The preserved package requires CPython >=3.12,<3.13, pandas 2.3.3 and pydantic 2.12.5.
The original pinned requirements.lock includes developer tools. In a separate environment:

```text
python -m pip install -r requirements.lock
python -m pip install --no-build-isolation --no-deps .
python -B -m pytest -p no:cacheprovider tests
```

No dependency installation was performed in this release check; an existing Python 3.12.10
environment and its already present packages were used. See docs/VERIFICATION.md for results.

## Reproduction and inputs/outputs

```text
cguard doctor
cguard demo ../new-synthetic-demo
cguard verify ../new-synthetic-demo
cguard replay ../new-synthetic-demo ../new-synthetic-replay
```

Use new external output directories. The bundled protocol and dictionary explicitly define
eight invented SYN-* rows, scenario bounds and synthetic groups with no treatment meaning.
Only predefined descriptive methods are allowed; missing outcomes remain missing. QC
rejects invalid headers/types and post-index baseline fields. The demo uses SIMULATION
approval and cannot satisfy the human release gate. No real human approval is asserted
by automated tests, even when a negative test exercises attestation handling.

Outputs include inputs/source snapshots, QC, plan/state/audit records, numerical results,
independent validation, report.html/report.md and manifests. New output remains local;
no historical generated examples, review decisions, build products or old Git objects are
distributed. Source and resources are preserved byte-for-byte with provenance hashes.

For manual synthetic review, use cguard prepare and cguard review; only an actual operator
may provide human attestations after examining the artifacts. This release does not run
those commands on a real dataset or claim a clinical or institutional sign-off.

## Evidence, data and attribution

Unit tests cover arithmetic, malformed input, timing, dependency/approval bindings, audit
transitions, output tampering, replay, warnings and failure handling. They do not prove
clinical validity, study appropriateness, privacy of arbitrary substituted data, authenticated
approvals or real-world deployment readiness. Synthetic markers can be spoofed and are not
a privacy guarantee. No clinical records, trained models or scientific results are included.

MIT license and existing attribution are retained. docs/provenance.md lists architectural
references, including the existing CSV workflow; it states that no AGPL PMxAgent source was
copied. No upstream code or dependencies are vendored here. Use CITATION.cff with the exact
commit; no DOI or peer-reviewed result is claimed. Maintenance/contact: GitHub Issues.

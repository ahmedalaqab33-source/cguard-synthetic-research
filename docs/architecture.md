# Architecture and implemented boundaries

The controller, not the planner, owns transitions:
RECEIVED → INPUT_REJECTED or PLAN_PENDING → PLAN_APPROVED → EXECUTING → VALIDATION_FAILED or REVIEW_PENDING → RELEASED.

Input QC is non-mutating and can run before approval. Analysis and report generation require approved inputs. Independent numerical validation must pass before a draft is written. Human release requires a human-attested plan approval; a simulation approval cannot be promoted during release.

Plan binding includes input byte hashes, the entire structured plan, QC report, source/skill fingerprint and Python/runtime dependency versions. A change invalidates approval. Input and output manifests are anchored in the chained audit. Every run archives the executed package and reviewed resource files.

The optional external proposal boundary is JSON conforming to Plan. There is no network client, arbitrary code, shell execution, dynamic package installation, or LLM-provided statistical result in the execution path. The v0 planner is a deterministic template. It deliberately establishes a non-LLM reference for a later agentic experiment.

Independent validation uses a separate CSV reader and Decimal arithmetic. The pandas producer is never imported by the oracle. Counts, group membership, missingness, means, sample SDs, medians, linearly interpolated quartiles and outcome proportions are checked. Replaying the producer is a separate reproducibility check.

The report is rendered from validated fields. Each displayed result has an explicit results.json pointer, and claims.json records its unrounded value. Verification regenerates the report and compares exact content. This avoids trying to certify arbitrary clinical prose with a keyword filter.

The supported schema fixes the scientific scope. Changes to its protocol, units or population require development and review, not a runtime model decision. Explicit scenario bounds are software test specifications and have no authority for patient care.

No multi-agent framework, MCP server, R statistical engine, database or web UI is needed for this slice. Authentication, capability-separated services and an OS sandbox are future work before an autonomous external agent or sensitive data could be considered.

A lock prevents concurrent controller mutations. A crashed process leaves .lock; do not blindly delete it and continue. Inspect the audit and source, retain the failed directory, and prepare a new run. In-process exceptions preserve a failure artifact. Power-loss recovery and distributed transactional storage are not claimed.


## Version 0.2 controls

The legal state graph is checked when reading the audit, including terminal CANCELLED from PLAN_PENDING, PLAN_APPROVED or REVIEW_PENDING. The audit transition is committed before updating the state cache. Interrupted updates fail closed on disagreement; no automatic crash repair is offered.

Execute and replay recheck the approved input/source/environment binding after computation and validation, before successful report/replay artifacts. Review, verify, status, replay and mutating commands use the same per-run lock. This addresses cooperating-process concurrency; it is not an OS sandbox against an arbitrary writer.

QC findings have stable IDs. All warning IDs must be explicitly acknowledged. Readable qc.md must regenerate exactly from qc.json before approval. Both HTML and Markdown reports are regenerated during verification and included in the output manifest. The HTML has no scripts or external resources.

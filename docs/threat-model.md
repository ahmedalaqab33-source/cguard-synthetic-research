# Threat model

Supported user: a trusted local researcher running code on synthetic data. The adversarial surface tested here consists of malformed input, unsupported proposals, stale approval, changed artifacts and execution/validation failures.

An external planner may supply only JSON. It must not receive credentials, a shell or filesystem write access to run/controller storage. The application does not spawn external agents and does not itself install an OS security boundary.

Implemented controls: fixed filenames/schema/protocol; file and row limits; strict proposal fields; no dynamic evaluation; source/input/environment approval binding; controller state checks; independent oracle; output manifest; audit hash chain; human-attestation release; per-run lock; exclusive new directories.

Not implemented: identity authentication, digital signatures, externally anchored logs, protection against malicious administrators, process resource isolation, network egress enforcement, robust de-identification, or fully transactional crash recovery. A human flag is not proof that a human actually reviewed the work. An agent with host-level access could forge both flags and files.

Numeric outputs may still have common conceptual errors. A domain reviewer must confirm the question, population, units and missingness assumptions. The application is not clinical decision-making software and is not validated for identifiable patient data.

Logs are limited to synthetic identifiers and structured decisions; no chain-of-thought or API keys are needed. Do not submit real records disguised with synthetic IDs. The acceptance checks cannot certify anonymity.


Version 0.2 adds strict finite JSON, audit shape/transition validation, bounded reads, rejection of symbolic links and Windows reparse points along artifact paths, and unpredictable exclusive temporary files with fsync plus atomic replacement. These reduce accidental redirection and partial-write hazards. Path checks and final binding checks do not make filesystem operations immune to hostile race conditions. Local access remains a trust assumption. Windows symbolic-link integration coverage was unavailable on the validation host; see verification.md.

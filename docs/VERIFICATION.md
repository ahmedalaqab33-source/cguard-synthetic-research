# Local release verification

104 regression tests passed; 1 host symlink-creation test skipped because this account cannot create symlinks. The CLI simulation demo verified and replayed; the separate verifier returned PASS at rtol 1e-10 and atol 1e-12. Python 3.12.10, existing pandas 2.3.3, pydantic 2.12.5 and pytest 9.1.1. No human approval or real clinical run was performed.

Only staged code and invented inputs were executed. No dependency installation, clinical dataset read, model training or remote CI dispatch occurred. Staged file hashes were unchanged by execution. These are software checks, not scientific or clinical validation. No clean-install or independent-human replication is claimed.

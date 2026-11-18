# Security and responsible use

Synthetic data only. Never commit real patient data, credentials or secrets. See docs/threat-model.md for the actual trust boundary.

Do not treat a human-attestation flag, chained JSON log or dataset hash as authenticated identity, de-identification or regulatory compliance. Do not grant an autonomous external agent write access to the controller or approval storage.

Report reproducible defects with synthetic examples and exact versions. For a sensitive security finding, contact the repository owner privately after a public hosting location is established; do not post identifiable data in an issue.


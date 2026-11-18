# Provenance, attribution and scope

This implementation was created for Ahmed Alaqab following the Phase 0 inspection on 17 September 2026. The existing repositories were not modified.

Architectural references:
- [User's CSV workflow](https://github.com/ahmedalaqab33-source/clinical-data-analysis-pipeline/blob/9b162f5d202527bb02256b5a659c35073e48e9a9/main.py): preserve observations and reject ambiguous headers.
- [Modus task library](https://github.com/AIML-SIG/Agentic-workflows/blob/5bd31238f0b658c18baf07a5fdeedb77a32b4075/tools/modus/ai_docs/task_library.json): externalized domain rules, explicit artifacts and review.
- [Modus escalation prompt](https://github.com/AIML-SIG/Agentic-workflows/blob/5bd31238f0b658c18baf07a5fdeedb77a32b4075/tools/modus/ai_docs/escalation_review_prompt.md): reason for keeping mandatory human approval outside automated review.
- [PMbench](https://github.com/AIML-SIG/Agentic-workflows/blob/5bd31238f0b658c18baf07a5fdeedb77a32b4075/tools/pharmbench/README.md): structured synthetic scenarios and independent scoring.
- [PMxAgent](https://github.com/peterbloomingdale/PMxAgent/blob/4811423042e03fa69194bfcaa9429a5b7a23f9c4/server.py): expose predefined statistical tools rather than generating arithmetic in language. PMxAgent is AGPL-3.0-only; no PMxAgent source was copied or integrated.
- [Klose sandbox](https://github.com/marianklose/llm-agentic-workflow-sandbox/blob/ffb92198c9f21f46834bf7169c0ec586b724043b/README.md): separation of provider, state, schema and nodes.

No private MFB2018 code/data, precision-dosing study data, clinical guidelines or published patient-level datasets are included. This package uses newly written implementation code and wholly invented cohort rows. Its bounds are scenario constraints, not borrowed clinical guidance.

The exact requested Practical Foundations session material was not located in Phase 0; no claim to have implemented uninspected session-specific guidance is made.

The name is provisional and not reserved. The existing [clinicalguard PyPI project](https://pypi.org/project/clinicalguard/) is unrelated. A public name search/review must precede publication. No "first ever" or clinical superiority claim is made.


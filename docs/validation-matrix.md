# Validation matrix

| Requirement | Implemented check | Test evidence |
|---|---|---|
| Schema/type/unit integrity | Exact headers, finite numeric parsing, reviewed dictionary | bad headers, invalid values, changed units |
| Missingness | Blank is missing; count and percent with row denominator | golden fixture, all-missing fields, singleton |
| Duplicate integrity | Duplicate participant ID blocks; exact rows counted and retained | duplicate test checks source bytes unchanged |
| Potential leakage | lab_day > index_day blocks baseline lab use | post-index measurement fixture |
| Outliers | Median-absolute-deviation ratio >5 warns without removal | outlier warning and retained row count |
| Method constraints | Typed plan rejects unknown fields/variables, causal claims, exclusions, imputation | proposal parametrization |
| Human oversight | Explicit attestation and scoped binding; simulation cannot release | missing, stale, changed approval and simulation tests |
| Correct computation | Separate Decimal oracle, fixed tolerance, exact counts/cohort | golden and seven fault-injection cases |
| Failure handling | Validator crash prevents report generation | crash test |
| Report provenance | Values/pointers, manifest, regeneration comparison | report/result/claim/validation tamper tests |
| Audit integrity | Previous hash, event sequence and state agreement | audit/state corruption tests |
| Reproducibility | Archived inputs/code, versions, replay comparison | exact result-byte hash comparison |
| Non-overwrite/concurrency | New-directory requirement and lock | existing run and lock tests |

Numerical tolerances are rtol=1e-10 and atol=1e-12. Counts/membership and missing/non-estimable values must match exactly. Means and quantiles are descriptive sample summaries; sample SD uses n−1. Quantiles use linear interpolation at (n−1)p. Outcomes use observed eligible participants as denominator.

Train/test leakage is NOT_APPLICABLE because no prediction model or split is used. Causal conclusions and treatment recommendations are outside the available report template. No claim is made to detect all clinical or methodological errors.

Passing the suite is engineering evidence on defined fixtures. It does not estimate population error rates, prove clinical utility or demonstrate superiority to any LLM.


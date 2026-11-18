"""Allowlisted deterministic computations. No code generation or dynamic evaluation."""
import pandas as pd
from .artifacts import GuardError

NUMERIC = ["age_years", "weight_kg", "lab_value", "outcome", "index_day", "lab_day"]

def summarize(packet, plan):
    frame = pd.read_csv(packet / "cohort.csv", dtype=str, keep_default_na=False)
    for name in NUMERIC:
        frame[name] = pd.to_numeric(frame[name].replace("", None), errors="raise")
    groups = {}
    for label, part in frame.groupby("group", sort=True):
        size = len(part)
        continuous = {}
        for name in plan.continuous:
            observed = part[name].dropna()
            continuous[name] = {
                "n": len(observed), "missing": size - len(observed),
                "mean": float(observed.mean()) if len(observed) else None,
                "sd": float(observed.std(ddof=1)) if len(observed) > 1 else None,
                "median": float(observed.median()) if len(observed) else None,
                "q1": float(observed.quantile(.25, interpolation="linear")) if len(observed) else None,
                "q3": float(observed.quantile(.75, interpolation="linear")) if len(observed) else None}
        outcome = part[plan.outcome].dropna()
        denominator = len(outcome)
        groups[label] = {
            "n": size, "members": sorted(part["participant_id"].tolist()),
            "continuous": continuous,
            "outcome": {"events": int(outcome.sum()), "observed": denominator,
                        "missing": size - denominator,
                        "proportion": float(outcome.sum() / denominator) if denominator else None}}
    if not groups:
        raise GuardError("No groups")
    return {"schema_version": 1, "total_n": len(frame), "groups": groups,
            "interpretation": "Descriptive synthetic data only; no causal or clinical inference."}


"""Independent oracle: CSV + Decimal arithmetic; never imports the producer."""
import csv
from decimal import Decimal, localcontext
from .artifacts import GuardError

def reference(packet, plan):
    with (packet / "cohort.csv").open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream))
    groups = {}
    for label in sorted({r["group"] for r in records}):
        rows = [r for r in records if r["group"] == label]
        metrics = {}
        for name in plan.continuous:
            values = sorted(Decimal(r[name]) for r in rows if r[name] != "")
            n = len(values)
            def quantile(probability):
                if not n:
                    return None
                index = Decimal(n - 1) * Decimal(probability)
                low = int(index)
                high = min(low + 1, n - 1)
                return float(values[low] + (index - low) * (values[high] - values[low]))
            with localcontext() as context:
                context.prec = 40
                mean = sum(values) / n if n else None
                sd = (sum((x - mean) ** 2 for x in values) / (n - 1)).sqrt() if n > 1 else None
            metrics[name] = {
                "n": n, "missing": len(rows) - n,
                "mean": float(mean) if mean is not None else None,
                "sd": float(sd) if sd is not None else None,
                "median": quantile(".5"), "q1": quantile(".25"), "q3": quantile(".75")}
        known = [int(Decimal(r[plan.outcome])) for r in rows if r[plan.outcome] != ""]
        groups[label] = {
            "n": len(rows), "members": sorted(r["participant_id"] for r in rows),
            "continuous": metrics,
            "outcome": {"events": sum(known), "observed": len(known),
                        "missing": len(rows) - len(known),
                        "proportion": float(Decimal(sum(known)) / len(known)) if known else None}}
    return {"schema_version": 1, "total_n": len(records), "groups": groups,
            "interpretation": "Descriptive synthetic data only; no causal or clinical inference."}

def compare(actual, expected, path="$"):
    import math
    if type(expected) is dict:
        if type(actual) is not dict or set(actual) != set(expected):
            raise GuardError(f"Validation keys mismatch at {path}")
        for key in expected:
            compare(actual[key], expected[key], path + "." + key)
    elif type(expected) is list:
        if actual != expected:
            raise GuardError(f"Validation cohort mismatch at {path}")
    elif type(expected) is float:
        if type(actual) not in {int, float} or not math.isfinite(actual):
            raise GuardError(f"Validation non-finite/wrong type at {path}")
        if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12):
            raise GuardError(f"Validation numerical mismatch at {path}")
    elif type(actual) is not type(expected) or actual != expected:
        raise GuardError(f"Validation exact mismatch at {path}")

def validate(packet, plan, result):
    compare(result, reference(packet, plan))
    return {"status": "PASS", "oracle": "independent CSV + Decimal implementation",
            "scope": "all reported metrics and group membership",
            "rtol": 1e-10, "atol": 1e-12,
            "limits": "Shared protocol assumptions still require human methodological review"}


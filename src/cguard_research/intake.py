"""Non-mutating synthetic-only intake with explicit type, unit and timing rules."""
import csv
import io
import re
import statistics
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from .artifacts import GuardError, RESOURCES, bounded_bytes, digest, read_json

COLUMNS = ["participant_id", "group", "age_years", "weight_kg", "lab_value",
           "outcome", "index_day", "lab_day"]
NUMERIC = ["age_years", "weight_kg", "lab_value", "outcome", "index_day", "lab_day"]

def inspect(packet):
    packet = Path(packet)
    dictionary = read_json(packet / "dictionary.json")
    protocol = read_json(packet / "protocol.json")
    if dictionary != read_json(RESOURCES / "dictionary.json"):
        raise GuardError("Unsupported dictionary or units")
    if protocol != read_json(RESOURCES / "protocol.json"):
        raise GuardError("Unsupported protocol; only the bundled synthetic study is allowed")
    raw = bounded_bytes(packet / "cohort.csv")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
    if reader.fieldnames != COLUMNS:
        raise GuardError("CSV schema/header mismatch (including duplicate or unexpected columns)")
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise GuardError("Malformed CSV record") from exc
    if not rows or len(rows) > 10_000:
        raise GuardError("Dataset must have 1..10000 records")
    findings = []
    def flag(rule, severity, record=None, variable=None):
        finding = {"rule": rule, "severity": severity, "record": record, "variable": variable}
        finding["id"] = digest(finding)[:16]
        findings.append(finding)
    ids, parsed = [], []
    for number, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise GuardError("Malformed CSV row")
        ident = row["participant_id"]
        ids.append(ident)
        if not re.fullmatch(r"SYN-[0-9]{3,6}", ident):
            flag("DQ_ID", "ERROR", number, "participant_id")
        if row["group"] not in {"A", "B"}:
            flag("DQ_GROUP", "ERROR", number, "group")
        values = {}
        for name in NUMERIC:
            token = row[name]
            if token == "":
                values[name] = None
                if name in {"index_day", "lab_day"}:
                    flag("DQ_REQUIRED_TIME", "ERROR", number, name)
                continue
            try:
                if len(token) > 64 or not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", token):
                    raise ValueError()
                exact = Decimal(token)
                if not exact.is_finite():
                    raise ValueError()
                if name in {"outcome", "index_day", "lab_day"} and exact != exact.to_integral_value():
                    raise ValueError()
                if exact != 0 and (exact.adjusted() < -12 or exact.adjusted() > 12):
                    raise ValueError()
                if len(exact.as_tuple().digits) > 15:
                    raise ValueError()
                value = float(exact)
                values[name] = value
            except (ValueError, InvalidOperation):
                values[name] = None
                flag("DQ_TYPE", "ERROR", number, name)
                continue
            limits = dictionary["variables"][name].get("bounds")
            if limits and not Decimal(str(limits[0])) <= exact <= Decimal(str(limits[1])):
                flag("DQ_BOUND", "ERROR", number, name)
        if values["outcome"] not in {None, 0, 1}:
            flag("DQ_OUTCOME", "ERROR", number, "outcome")
        if values["lab_day"] is not None and values["index_day"] is not None:
            if values["lab_day"] > values["index_day"]:
                flag("LEAK_POST_INDEX", "ERROR", number, "lab_value")
        parsed.append(values)
    duplicate_ids = sum(count - 1 for count in Counter(ids).values() if count > 1)
    if duplicate_ids:
        flag("DQ_DUPLICATE_ID", "ERROR", variable="participant_id")
    exact_duplicates = len(rows) - len({tuple(row[name] for name in COLUMNS) for row in rows})
    for name in ["age_years", "weight_kg", "lab_value"]:
        vals = [v[name] for v in parsed if v[name] is not None]
        if len(vals) >= 4:
            med = statistics.median(vals)
            mad = statistics.median([abs(v - med) for v in vals])
            for number, record in enumerate(parsed, start=2):
                value = record[name]
                if value is not None and mad > 0 and abs(value - med) / mad > 5:
                    flag("DQ_OUTLIER", "WARNING", number, name)
                elif value is not None and mad == 0 and value != med:
                    flag("DQ_ZERO_MAD_DEVIATION", "WARNING", number, name)
    return {
        "schema_version": 1, "rows": len(rows),
        "missing": {name: sum(row[name] == "" for row in rows) for name in COLUMNS},
        "missing_percent": {name: 100 * sum(row[name] == "" for row in rows) / len(rows)
                            for name in COLUMNS},
        "exact_duplicate_rows": exact_duplicates, "duplicate_ids": duplicate_ids,
        "findings": findings, "blocked": any(f["severity"] == "ERROR" for f in findings),
        "prediction_leakage": {"status": "NOT_APPLICABLE", "reason": "No predictive model or split"},
        "timing_check": "baseline lab measurement must not occur after index_day",
        "privacy": "Synthetic declaration and restrictive schema; not a de-identification guarantee",
        "outlier_policy": "MAD ratio > 5 warns; zero MAD with a distinct value warns; no deletion",
        "numeric_policy": "ASCII decimal; <=64 characters; <=15 significant digits; nonzero magnitude >=1e-12"}

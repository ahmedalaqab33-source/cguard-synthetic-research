"""Canonical artifacts and detectable audit-chain corruption (not authentication)."""
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = Path(__file__).parent
RESOURCES = PACKAGE / "resources"
MAX_BYTES = 5_000_000
TRANSITIONS = {
    None: {"RECEIVED"},
    "RECEIVED": {"INPUT_REJECTED", "PLAN_PENDING"},
    "PLAN_PENDING": {"PLAN_APPROVED", "CANCELLED"},
    "PLAN_APPROVED": {"EXECUTING", "VALIDATION_FAILED", "CANCELLED"},
    "EXECUTING": {"REVIEW_PENDING", "VALIDATION_FAILED"},
    "REVIEW_PENDING": {"RELEASED", "CANCELLED"},
    "RELEASED": set(), "INPUT_REJECTED": set(),
    "VALIDATION_FAILED": set(), "CANCELLED": set(),
}

class GuardError(ValueError):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                      separators=(",", ":")).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def safe_path(path):
    path = Path(path).absolute()
    for part in [path, *path.parents]:
        try:
            metadata = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & 0x400:
            raise GuardError("Linked artifact paths are not supported")
    return path

def bounded_bytes(path):
    path = safe_path(path)
    if not path.is_file():
        raise GuardError("Artifact must be a regular file")
    if path.stat().st_size > MAX_BYTES:
        raise GuardError("Artifact exceeds size limit")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise GuardError("Artifact exceeds size limit")
    return data

def file_hash(path):
    return hashlib.sha256(bounded_bytes(path)).hexdigest()

def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise GuardError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    def finite(value):
        result = float(value)
        if not math.isfinite(result):
            raise GuardError("Non-finite JSON number")
        return result
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_float=finite,
                          parse_constant=lambda value: (_ for _ in ()).throw(GuardError("Non-finite JSON")))
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise GuardError("Malformed JSON artifact") from exc

def read_json(path):
    return strict_json(bounded_bytes(path))

def write_bytes(path, value):
    path = safe_path(path)
    if len(value) > MAX_BYTES:
        raise GuardError("Output exceeds size limit")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix="." + path.name + ".",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        safe_path(path)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

def write_json(path, value):
    write_bytes(path, canonical(value) + b"\n")

def environment():
    return {"python": platform.python_version(), "platform": platform.system(),
            "architecture": platform.machine(),
            "packages": {name: importlib.metadata.version(name) for name in (
                "pandas", "numpy", "pydantic", "pydantic-core", "annotated-types",
                "typing-extensions", "typing-inspection", "python-dateutil", "pytz", "tzdata", "six")},
            "locale_policy": "UTF-8 files; ASCII numbers; UTC timestamps"}

def code_files():
    return sorted(p for p in PACKAGE.rglob("*") if p.is_file() and
                  p.suffix in {".py", ".json", ".md", ".csv"} and "__pycache__" not in p.parts)

def code_hash():
    return digest({p.relative_to(PACKAGE).as_posix(): file_hash(p) for p in code_files()})

def audit_events(run):
    path = safe_path(Path(run) / "audit.jsonl")
    events, previous = [], "0" * 64
    previous_state = None
    if not path.exists():
        return events
    raw = bounded_bytes(path)
    if raw and not raw.endswith(b"\n"):
        raise GuardError("Audit has a truncated final record")
    for line in raw.splitlines():
        entry = strict_json(line)
        if type(entry) is not dict or set(entry) != {
            "sequence", "previous", "timestamp", "action", "details", "hash"
        }:
            raise GuardError("Audit record schema mismatch")
        if type(entry["sequence"]) is not int or type(entry["details"]) is not dict:
            raise GuardError("Audit record type mismatch")
        if not isinstance(entry["action"], str) or not isinstance(entry["timestamp"], str):
            raise GuardError("Audit action/timestamp type mismatch")
        try:
            stamp = datetime.fromisoformat(entry["timestamp"])
        except ValueError as exc:
            raise GuardError("Invalid audit timestamp") from exc
        if stamp.tzinfo is None:
            raise GuardError("Audit timestamp must include timezone")
        claimed = entry.pop("hash")
        if entry["sequence"] != len(events) or entry["previous"] != previous or digest(entry) != claimed:
            raise GuardError("Audit chain mismatch")
        if entry["action"] == "state_transition":
            next_state = entry["details"].get("state")
            if not isinstance(next_state, str) or next_state not in TRANSITIONS.get(previous_state, set()):
                raise GuardError("Illegal state transition in audit")
            previous_state = next_state
        entry["hash"] = claimed
        events.append(entry)
        previous = claimed
    return events

def event(run, action, **details):
    history = audit_events(run)
    record = {"sequence": len(history), "previous": history[-1]["hash"] if history else "0" * 64,
              "timestamp": now(), "action": action, "details": details}
    record["hash"] = digest(record)
    path = safe_path(Path(run) / "audit.jsonl")
    encoded = canonical(record) + b"\n"
    if (path.stat().st_size if path.exists() else 0) + len(encoded) > MAX_BYTES:
        raise GuardError("Audit exceeds size limit")
    with path.open("ab") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())

def state(run):
    return read_json(Path(run) / "state.json")["state"]

def transition(run, value):
    history = audit_events(run)
    states = [e["details"]["state"] for e in history if e["action"] == "state_transition"]
    previous = states[-1] if states else None
    if value not in TRANSITIONS.get(previous, set()):
        raise GuardError("Illegal state transition")
    event(run, "state_transition", state=value)
    write_json(Path(run) / "state.json", {"state": value})

def check_state(run, allowed):
    history = audit_events(run)
    current = state(run)
    transitions = [e["details"]["state"] for e in history if e["action"] == "state_transition"]
    if not transitions or current != transitions[-1]:
        raise GuardError("State and audit disagree")
    if current not in allowed:
        raise GuardError(f"State {current} does not allow this action")

class RunLock:
    """Mutation lock; crashes leave a lock for explicit operator recovery."""
    def __init__(self, run):
        self.path = safe_path(Path(run) / ".lock")
    def __enter__(self):
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise GuardError("Run is locked; inspect interrupted execution before recovery") from exc
        os.write(self.fd, str(os.getpid()).encode())
        return self
    def __exit__(self, *args):
        os.close(self.fd)
        self.path.unlink()

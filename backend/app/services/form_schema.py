"""Validation of form schemas (definitions) and of submitted answers against a schema.

Schemas are pure data: no code or expressions. Conditions are declarative
({"field": key, "op": eq|neq|in|not_empty, "value": ...}) evaluated within the same entry.

Answers shape:
  {"<section_id>": {field_key: value}}              non-repeatable section
  {"<section_id>": [{field_key: value}, ...]}       repeatable section (one dict per entry)
Photo fields hold a photo UUID string (photo) or a list of them (photos).
"""
import re
import uuid
from datetime import date, datetime, time
from typing import Any

FIELD_TYPES = {
    "text", "multiline_text", "integer", "decimal", "date", "time", "datetime",
    "dropdown", "radio", "checkbox", "multi_select", "phone", "email",
    "photo", "photos", "location", "readonly_text", "heading",
}
DISPLAY_ONLY = {"readonly_text", "heading"}
OPTION_TYPES = {"dropdown", "radio", "multi_select"}
OPTION_SOURCES = {"person_types"}  # managed lists whose options are injected at delivery/validation time
CONDITION_OPS = {"eq", "neq", "in", "not_empty"}
RULE_KEYS = {"min_length", "max_length", "min", "max", "pattern"}
MAX_SECTIONS, MAX_FIELDS, MAX_ENTRIES = 30, 100, 50
MAX_TEXT_DEFAULT = 5000
_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PHONE = re.compile(r"^\+?[0-9][0-9 \-()]{6,19}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SchemaError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def validate_schema(schema: Any) -> None:
    errs: list[str] = []
    if not isinstance(schema, dict):
        raise SchemaError(["schema must be an object"])
    for k in ("form_id", "title"):
        if not isinstance(schema.get(k), str) or not schema[k]:
            errs.append(f"{k} is required")
    if not isinstance(schema.get("version"), int) or schema["version"] < 1:
        errs.append("version must be a positive integer")
    sections = schema.get("sections")
    if not isinstance(sections, list) or not sections or len(sections) > MAX_SECTIONS:
        raise SchemaError(errs + [f"sections must be a list of 1..{MAX_SECTIONS}"])
    seen_sections: set[str] = set()
    for si, sec in enumerate(sections):
        p = f"sections[{si}]"
        if not isinstance(sec, dict) or not _ID.match(str(sec.get("id", ""))):
            errs.append(f"{p}.id invalid")
            continue
        if sec["id"] in seen_sections:
            errs.append(f"{p}.id duplicate")
        seen_sections.add(sec["id"])
        if sec.get("repeatable"):
            lo, hi = sec.get("min_items", 0), sec.get("max_items", MAX_ENTRIES)
            if not (isinstance(lo, int) and isinstance(hi, int) and 0 <= lo <= hi <= MAX_ENTRIES):
                errs.append(f"{p} min_items/max_items invalid")
        fields = sec.get("fields")
        if not isinstance(fields, list) or not fields or len(fields) > MAX_FIELDS:
            errs.append(f"{p}.fields must be a list of 1..{MAX_FIELDS}")
            continue
        keys: set[str] = set()
        for fi, f in enumerate(fields):
            _validate_field(f, f"{p}.fields[{fi}]", keys, errs)
    if errs:
        raise SchemaError(errs)


def _validate_field(f: Any, p: str, keys: set[str], errs: list[str]) -> None:
    if not isinstance(f, dict):
        errs.append(f"{p} must be an object")
        return
    key = f.get("key")
    if not isinstance(key, str) or not _ID.match(key):
        errs.append(f"{p}.key invalid")
        return
    if key in keys:
        errs.append(f"{p}.key duplicate")
    keys.add(key)
    if f.get("type") not in FIELD_TYPES:
        errs.append(f"{p}.type unsupported: {f.get('type')!r}")
        return
    if not isinstance(f.get("label"), str):
        errs.append(f"{p}.label required")
    source = f.get("options_source")
    if source is not None and (source not in OPTION_SOURCES or f["type"] != "dropdown"):
        errs.append(f"{p}.options_source must be one of {sorted(OPTION_SOURCES)} on a dropdown")
    if f.get("allow_other") not in (None, True, False):
        errs.append(f"{p}.allow_other must be true/false")
    if f["type"] in OPTION_TYPES and source is None:
        opts = f.get("options")
        if not isinstance(opts, list) or not opts or not all(
            isinstance(o, dict) and isinstance(o.get("value"), str) and isinstance(o.get("label"), str)
            for o in opts
        ):
            errs.append(f"{p}.options must be a non-empty list of {{value,label}}")
    rules = f.get("validation", {})
    if not isinstance(rules, dict) or set(rules) - RULE_KEYS:
        errs.append(f"{p}.validation has unsupported rules")
    elif "pattern" in rules:
        try:
            if len(rules["pattern"]) > 200:
                raise ValueError
            re.compile(rules["pattern"])
        except (re.error, ValueError, TypeError):
            errs.append(f"{p}.validation.pattern invalid")
    cond = f.get("visible_if")
    if cond is not None and not (
        isinstance(cond, dict)
        and cond.get("op") in CONDITION_OPS
        and isinstance(cond.get("field"), str)
        and set(cond) <= {"field", "op", "value"}
    ):
        errs.append(f"{p}.visible_if malformed")


def _empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _cond_true(cond: dict | None, entry: dict) -> bool:
    if not cond:
        return True
    v = entry.get(cond["field"])
    op = cond["op"]
    if op == "eq":
        return v == cond.get("value")
    if op == "neq":
        return v != cond.get("value")
    if op == "in":
        return v in (cond.get("value") or [])
    return not _empty(v)


def collect_photo_refs(schema: dict, answers: dict) -> list[dict]:
    """Photo references in answers: [{photo_id, section, group_key, field}] (after validation)."""
    refs = []
    for sec in schema["sections"]:
        data = answers.get(sec["id"])
        entries = data if sec.get("repeatable") else [data]
        for idx, entry in enumerate(entries or []):
            entry = entry or {}
            for f in sec["fields"]:
                if f["type"] in ("photo", "photos") and not _empty(entry.get(f["key"])):
                    ids = entry[f["key"]] if f["type"] == "photos" else [entry[f["key"]]]
                    for pid in ids:
                        refs.append(
                            {"photo_id": pid, "section": sec["id"], "group_key": f"{sec['id']}:{idx}",
                             "field": f["key"]}
                        )
    return refs


def validate_answers(schema: dict, answers: Any) -> list[dict]:
    """Returns [{field_id, path, message}] — empty when valid."""
    errors: list[dict] = []
    if not isinstance(answers, dict):
        return [{"field_id": None, "path": "", "message": "answers must be an object"}]
    known = {s["id"] for s in schema["sections"]}
    for extra in set(answers) - known:
        errors.append({"field_id": extra, "path": extra, "message": "unknown section"})
    for sec in schema["sections"]:
        sid = sec["id"]
        data = answers.get(sid)
        if sec.get("repeatable"):
            lo, hi = sec.get("min_items", 0), sec.get("max_items", MAX_ENTRIES)
            entries = data if data is not None else []
            if not isinstance(entries, list):
                errors.append({"field_id": sid, "path": sid, "message": "must be a list"})
                continue
            if not lo <= len(entries) <= hi:
                errors.append({"field_id": sid, "path": sid, "message": f"entries must be {lo}..{hi}"})
        else:
            entries = [data if data is not None else {}]
        for idx, entry in enumerate(entries):
            base = f"{sid}[{idx}]" if sec.get("repeatable") else sid
            if not isinstance(entry, dict):
                errors.append({"field_id": sid, "path": base, "message": "must be an object"})
                continue
            fkeys = {f["key"] for f in sec["fields"]}
            for extra in set(entry) - fkeys:
                errors.append({"field_id": extra, "path": f"{base}.{extra}", "message": "unknown field"})
            for f in sec["fields"]:
                if f["type"] in DISPLAY_ONLY or not _cond_true(f.get("visible_if"), entry):
                    continue
                msg = _check_value(f, entry.get(f["key"]))
                if msg:
                    errors.append({"field_id": f["key"], "path": f"{base}.{f['key']}", "message": msg})
    return errors


def _check_value(f: dict, v: Any) -> str | None:
    t = f["type"]
    if _empty(v):
        return "required" if f.get("required") else None
    rules = f.get("validation", {})
    try:
        if t in ("text", "multiline_text", "phone", "email"):
            if not isinstance(v, str):
                return "must be text"
            if len(v) > rules.get("max_length", MAX_TEXT_DEFAULT):
                return "too long"
            if len(v) < rules.get("min_length", 0):
                return "too short"
            if t == "phone" and not _PHONE.match(v):
                return "invalid phone number"
            if t == "email" and not _EMAIL.match(v):
                return "invalid email"
            if "pattern" in rules and not re.fullmatch(rules["pattern"], v):
                return "invalid format"
        elif t in ("integer", "decimal"):
            if isinstance(v, bool) or not isinstance(v, (int, float) if t == "decimal" else int):
                return "must be a number"
            if "min" in rules and v < rules["min"]:
                return f"must be >= {rules['min']}"
            if "max" in rules and v > rules["max"]:
                return f"must be <= {rules['max']}"
        elif t == "date":
            date.fromisoformat(v)
        elif t == "time":
            time.fromisoformat(v)
        elif t == "datetime":
            datetime.fromisoformat(v)
        elif t in ("dropdown", "radio"):
            if f.get("allow_other") and isinstance(v, str) and v.startswith("other:"):
                text = v[6:].strip()  # a custom value typed by the agent: "other:<text>"
                if not text or len(text) > 100:
                    return "enter the other type (1-100 characters)"
            elif v not in {o["value"] for o in f.get("options", [])}:
                return "not a valid option"
        elif t == "multi_select":
            if not isinstance(v, list) or not set(v) <= {o["value"] for o in f["options"]}:
                return "not a valid option"
        elif t == "checkbox":
            if not isinstance(v, bool):
                return "must be true/false"
        elif t == "photo":
            uuid.UUID(v)
        elif t == "photos":
            if not isinstance(v, list):
                return "must be a list"
            for x in v:
                uuid.UUID(x)
            if len(set(v)) != len(v):
                return "same photo listed twice"
            # For photo lists, validation.min / validation.max are photo COUNTS.
            if "max" in rules and len(v) > rules["max"]:
                return f"at most {rules['max']} photos"
            if "min" in rules and len(v) < rules["min"]:
                return f"at least {rules['min']} photos"
        elif t == "location":
            if not (isinstance(v, dict) and -90 <= v.get("latitude", 999) <= 90
                    and -180 <= v.get("longitude", 999) <= 180):
                return "invalid location"
    except (ValueError, TypeError, AttributeError):
        return "invalid value"
    return None


def overlay_dynamic_options(schema: dict, options: dict[str, list[dict]], *, required: bool | None = None,
                            allow_other: bool | None = None) -> dict:
    """Returns a copy of `schema` where every field with an `options_source` gets its current options
    ([{value, label}]) and, if given, the company's required / allow_other settings. The stored version is never
    modified: versions are immutable, the option lists are managed data."""
    out = {**schema, "sections": []}
    for sec in schema["sections"]:
        fields = []
        for f in sec["fields"]:
            src = f.get("options_source")
            if src:
                f = {**f, "options": list(options.get(src, []))}
                if required is not None:
                    f["required"] = required
                if allow_other is not None:
                    f["allow_other"] = allow_other
            fields.append(f)
        out["sections"].append({**sec, "fields": fields})
    return out


def dynamic_entries(schema: dict, answers: dict) -> list[tuple[str, str, str]]:
    """(path, source, value) for every answered field that uses a managed option list, e.g.
    ("meeting_details[1].contact_category", "person_types", "<uuid>")."""
    found = []
    for sec in schema["sections"]:
        data = answers.get(sec["id"])
        entries = data if sec.get("repeatable") else [data]
        for idx, entry in enumerate(entries or []):
            if not isinstance(entry, dict):
                continue
            base = f"{sec['id']}[{idx}]" if sec.get("repeatable") else sec["id"]
            for f in sec["fields"]:
                v = entry.get(f["key"])
                if f.get("options_source") and isinstance(v, str) and v:
                    found.append((f"{base}.{f['key']}", f["options_source"], v))
    return found

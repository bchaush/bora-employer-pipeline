"""Operator environment verifier for CAREER_OS_DOCUMENT_RENDERING_CAPABILITY_V1.

Governed by milestone_contracts/governance/career-os-document-rendering-capability-v1-contract.json
(PROVISIONING_INSTRUMENTS_V1, DEPENDENCY_LOCK_REVIEW_V1, APT_TRUST_MODEL_V1,
OPERATOR_BASE_INTERPRETER_V1, CONTENT_BINDING_V1 and OPERATOR ENVIRONMENT
EVIDENCE). It grants no authority: every mode only computes and prints a
machine-readable evidence record, and a mismatch exits non-zero.

Modes (exactly one per invocation):

  --plan-digest            PLAN_DIGEST, pre_provision_plan_digest,
                           lock_review_digest and IDENTITY_DIGEST_V1 of the
                           checkout's manifest and lock, plus the gate (2)
                           eligibility of the candidate (no host access).
  --review-wheels DIR      DEPENDENCY_LOCK_REVIEW_V1 pre-provision part from
                           the hash-pinned wheels in DIR (QUARANTINE or
                           BUILDER_DEV; METADATA and RECORD are read from the
                           archives, nothing is installed, imported or run).
  --capture-plan           read-only capture of the host-derived
                           PRE_PROVISION_PLAN values (interpreter identity,
                           pip identity, apt and dpkg configuration and the
                           E2_HELPER_CHAIN_V1 record). Reads only; executes
                           no helper.
  --apt-noninteractive-proof
                           APT_NONINTERACTIVE_PROOF_V1 on the pinned apt of the host
                           (root; --simulate, --download-only into a disposable
                           directory, control without --yes). Never runs
                           `apt-get update`, never installs, fails closed (STOP)
                           when the planned pins cannot be resolved.
  --process-creation-proof PROCESS_CREATION_PROOF_V1 on the manifest base
                           interpreter: the fixed vector list under the
                           enumeration hook and the real denying hook, plus the
                           disposable proof-prefix E1/E2 run.
  --post-evidence PLAN_DIGEST [--provisioning-evidence FILE]
                           deterministic PARTIAL POST_PROVISION_BINDING evidence
                           from the live installation (POST keys must still be
                           null); lists every field that remains and never
                           populates an empirical field.
  --operator               post-provision verification of the live operator
                           rendering environment (never run by tests or CI).

The module also exposes the pure check functions the hermetic tests call
and the two operator-side instruments the adapter requires
(live_verifier and isolation_prober).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_RELPATH = "docs/rendering/RENDERING_ENVIRONMENT_V1.json"
REQUIREMENTS_IN_RELPATH = "requirements.in"
REQUIREMENTS_LOCK_RELPATH = "requirements-lock.txt"
PROVISIONING_SCRIPT_RELPATH = "scripts/provision_document_rendering_env.sh"
VERIFIER_RELPATH = "scripts/verify_document_rendering_environment.py"
ADAPTER_RELPATH = "src/document_render_adapter.py"


def load_adapter():
    """The adapter module loaded by file path (no sys.path addition)."""
    name = "document_render_adapter"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / ADAPTER_RELPATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# CANONICAL JSON AND DIGESTS (DIGEST_SPEC_V1)
# =============================================================================

def canonical_json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def canonical_digest(value) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strict_json_loads(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key %r" % key)
            result[key] = value
        return result

    def constant(name):
        raise ValueError("non-finite number %s" % name)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def identity_digest(executable_sha256, installer_pip_package_path, installer_pip_package_tree_digest,
                    interpreter_path, interpreter_realpath, native_closure_digest, stdlib_path,
                    stdlib_tree_digest) -> str:
    """IDENTITY_DIGEST_V1."""
    return canonical_digest({
        "executable_sha256": executable_sha256,
        "installer_pip_package_path": installer_pip_package_path,
        "installer_pip_package_tree_digest": installer_pip_package_tree_digest,
        "interpreter_path": interpreter_path,
        "interpreter_realpath": interpreter_realpath,
        "native_closure_digest": native_closure_digest,
        "spec": "IDENTITY_DIGEST_V1",
        "stdlib_path": stdlib_path,
        "stdlib_tree_digest": stdlib_tree_digest,
    })


class Rejected(Exception):
    """A named fail-closed outcome: (status, reason, detail)."""

    def __init__(self, status: str, reason: str, detail=None, **evidence) -> None:
        super().__init__(status, reason, detail)
        self.status = status
        self.reason = reason
        self.detail = detail
        self.evidence = evidence

    def triple(self) -> tuple:
        return (self.status, self.reason, self.detail)


LOCK_REJECTED = "RENDER_DEPENDENCY_LOCK_REJECTED"
ENV_UNVERIFIED = "RENDER_ENVIRONMENT_UNVERIFIED"
APT_SOURCE_UNAPPROVED = "APT_SOURCE_UNAPPROVED"
APT_CONFIG_UNAPPROVED = "APT_CONFIG_UNAPPROVED"
APT_UPDATE_FAILED = "APT_UPDATE_FAILED"
APT_INSTALL_FAILED = "APT_INSTALL_FAILED"
APT_UNEXPECTED_CHANGE = "APT_UNEXPECTED_CHANGE"
BASE_INTERPRETER_MISMATCH = "BASE_INTERPRETER_MISMATCH"
PROVISIONING_ENV_VIOLATION = "PROVISIONING_ENV_VIOLATION"


# =============================================================================
# DEPENDENCY_MODEL_V1 AND DEPENDENCY_LOCK_REVIEW_V1
# =============================================================================

BASELINE_ENTRIES = (
    ("attrs", "26.1.0"),
    ("jsonschema", "4.26.0"),
    ("jsonschema-specifications", "2025.9.1"),
    ("referencing", "0.37.0"),
    ("rpds-py", "2026.6.3"),
)
DIRECT_DISTRIBUTIONS = ("pdfminer-six", "pypdf")
ARTIFACT_TARGET_IDS = ("HOSTED_CI", "OPERATOR")
ARTIFACT_TARGET_KEYS = ("abi_tag", "id", "implementation", "libc", "platform_sequence", "platform_tags",
                        "python_version", "tag_sequence")
ROLES = ("BASELINE", "DIRECT", "TRANSITIVE")
CAPABILITY_CLASSES = ("PDF_INSPECTION_DIRECT", "SUPPORT_LIBRARY", "IMAGE_LIBRARY", "CRYPTO_LIBRARY",
                      "BASELINE_LIBRARY", "FORBIDDEN_ENGINE")
RECORD_KEYS = ("capability_class", "license_declared", "name", "native_binaries", "required_by", "role", "version")
LICENSE_KEYS = ("License", "License-Classifiers", "License-Expression")
DENYLIST_SEED = (
    "pymupdf", "mupdf", "fitz", "pdfplumber", "pypdfium2", "wand", "pdfium-binaries", "pikepdf", "qpdf",
    "pdf2image", "python-poppler", "pdfrw", "pypdf2", "pypdf4", "reportlab", "borb", "weasyprint",
    "ghostscript", "pdfkit", "camelot-py", "pdfquery",
)
_COPYLEFT = re.compile(r"(?<![A-Za-z])(?:AGPL|GPL|SSPL|EUPL)(?![A-Za-z])|GNU (?:Affero )?General Public|"
                       r"Server Side Public", re.IGNORECASE)
_SPDX_TOKEN = re.compile(r"\(|\)|[A-Za-z0-9][A-Za-z0-9.+-]*")
_WHEEL_SHA = re.compile(r"[0-9a-f]{64}\Z")
_LOCK_LINE = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9A-Za-z][0-9A-Za-z.+!_-]*)((?: --hash=sha256:[0-9a-f]{64})+)\Z")


def normalize_name(name: str) -> str:
    """PEP 503 normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _lock_rejected(reason: str, detail=None, **evidence):
    raise Rejected(LOCK_REJECTED, reason, detail, **evidence)


def parse_lock(data: bytes) -> dict:
    """requirements-lock.txt -> {normalized name: (version, sorted hashes)}.
    Every non-comment line is one exact pin carrying one or more hashes;
    any option line, unhashed line or duplicate is CLOSURE_MISMATCH."""
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError:
        _lock_rejected("CLOSURE_MISMATCH", "LOCK_NOT_UTF8")
    entries = {}
    for number, line in enumerate(text.split("\n"), 1):
        if line.endswith("\r"):
            _lock_rejected("CLOSURE_MISMATCH", "LOCK_LINE_MALFORMED", line=number)
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("-"):
            _lock_rejected("CLOSURE_MISMATCH", "LOCK_OPTION_LINE", line=number)
        match = _LOCK_LINE.match(line)
        if not match:
            if "--hash=" not in line:
                _lock_rejected("CLOSURE_MISMATCH", "MEMBER_WITHOUT_HASH", line=number)
            _lock_rejected("CLOSURE_MISMATCH", "LOCK_LINE_MALFORMED", line=number)
        name = normalize_name(match.group(1))
        if name in entries:
            _lock_rejected("CLOSURE_MISMATCH", "DUPLICATE_MEMBER", name=name)
        hashes = re.findall(r"[0-9a-f]{64}", match.group(3))
        if len(set(hashes)) != len(hashes):
            _lock_rejected("HASH_SET_MISMATCH", "DUPLICATE_HASH", name=name)
        entries[name] = (match.group(2), sorted(hashes))
    return entries


# -- PEP 508 marker evaluation (closed subset used by the reviewed metadata) --

_MARKER_TOKEN = re.compile(r"\s*(\(|\)|and\b|or\b|not in\b|in\b|===|==|!=|<=|>=|<|>|~=|"
                           r"'[^']*'|\"[^\"]*\"|[A-Za-z_][A-Za-z0-9_.]*)")
MARKER_VARIABLES = ("extra", "implementation_name", "platform_python_implementation", "python_full_version",
                    "python_version", "sys_platform", "platform_system", "platform_machine", "os_name",
                    "implementation_version")
_VERSION_VARIABLES = ("python_full_version", "python_version", "implementation_version")


def _version_tuple(text: str) -> tuple:
    parts = []
    for item in text.split("."):
        if not item.isdigit():
            raise ValueError("unsupported version %r" % text)
        parts.append(int(item))
    return tuple(parts)


def _compare(left: str, op: str, right: str, versioned: bool) -> bool:
    if op in ("in", "not in"):
        return (left in right) if op == "in" else (left not in right)
    if versioned and op not in ("===",):
        a, b = _version_tuple(left), _version_tuple(right)
        width = max(len(a), len(b))
        a, b = a + (0,) * (width - len(a)), b + (0,) * (width - len(b))
        if op == "~=":
            raise ValueError("~= is not used by the reviewed metadata")
        return {"==": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    return {"==": left == right, "!=": left != right, "===": left == right}[op]


def evaluate_marker(marker: str, environment: dict) -> bool:
    """Evaluate a PEP 508 environment marker over ENVIRONMENT; an unknown
    variable or construct raises ValueError (fail closed)."""
    tokens = []
    position = 0
    while position < len(marker):
        if marker[position:].strip() == "":
            break
        match = _MARKER_TOKEN.match(marker, position)
        if not match:
            raise ValueError("unparseable marker %r" % marker)
        tokens.append(match.group(1))
        position = match.end()
    index = 0

    def value_of(token):
        if token[0] in "'\"":
            return token[1:-1], None
        if token not in MARKER_VARIABLES:
            raise ValueError("unknown marker variable %r" % token)
        if token not in environment:
            raise ValueError("marker variable %r not set" % token)
        return environment[token], token

    def atom():
        nonlocal index
        if tokens[index] == "(":
            index += 1
            result = disjunction()
            if tokens[index] != ")":
                raise ValueError("unbalanced marker")
            index += 1
            return result
        left, left_var = value_of(tokens[index])
        op = tokens[index + 1]
        right, right_var = value_of(tokens[index + 2])
        index += 3
        variable = left_var or right_var
        if variable == "extra":
            left, right = normalize_name(left), normalize_name(right)
        return _compare(left, op, right, variable in _VERSION_VARIABLES)

    def conjunction():
        nonlocal index
        result = atom()
        while index < len(tokens) and tokens[index] == "and":
            index += 1
            result = atom() and result
        return result

    def disjunction():
        nonlocal index
        result = conjunction()
        while index < len(tokens) and tokens[index] == "or":
            index += 1
            other = conjunction()
            result = result or other
        return result

    outcome = disjunction()
    if index != len(tokens):
        raise ValueError("trailing marker tokens in %r" % marker)
    return outcome


_REQUIREMENT = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*([^;]*?)\s*(?:;\s*(.*))?\Z")


def parse_requirement(text: str) -> tuple:
    """Requires-Dist -> (normalized name, extras tuple, marker or None)."""
    match = _REQUIREMENT.match(text)
    if not match:
        raise ValueError("unparseable requirement %r" % text)
    extras = tuple(sorted(normalize_name(item.strip()) for item in (match.group(2) or "[]")[1:-1].split(",")
                          if item.strip()))
    return normalize_name(match.group(1)), extras, (match.group(4) or None)


def target_marker_environment(target: dict) -> dict:
    version = target["python_version"]
    major_minor = ".".join(version.split(".")[:2])
    return {
        "python_full_version": version,
        "python_version": major_minor,
        "implementation_version": version,
        "implementation_name": target["implementation"],
        "platform_python_implementation": {"cpython": "CPython"}.get(target["implementation"],
                                                                    target["implementation"]),
        "sys_platform": "linux",
        "platform_system": "Linux",
        "platform_machine": "x86_64",
        "os_name": "posix",
        "extra": "",
    }


def compute_closure(requires: dict, roots, target: dict) -> tuple:
    """(names, edges) of the default no-extras closure of ROOTS over
    REQUIRES {normalized name: [Requires-Dist strings]} for TARGET. A
    requirement on a distribution absent from REQUIRES is
    ARTIFACT_SET_UNDETERMINED (its metadata was not reviewed)."""
    environment = target_marker_environment(target)
    names, edges, pending = set(), set(), list(roots)
    while pending:
        name = pending.pop()
        if name in names:
            continue
        if name not in requires:
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "METADATA_MISSING", name=name)
        names.add(name)
        for text in requires[name]:
            child, extras, marker = parse_requirement(text)
            if extras:
                _lock_rejected("ARTIFACT_SET_UNDETERMINED", "REQUIREMENT_EXTRAS", name=name)
            if marker is not None:
                try:
                    active = evaluate_marker(marker, environment)
                except (ValueError, IndexError, KeyError):
                    _lock_rejected("ARTIFACT_SET_UNDETERMINED", "MARKER", name=name)
                if not active:
                    continue
            edges.add((name, child))
            pending.append(child)
    return names, edges


# -- TAG_MODEL_V1 --------------------------------------------------------------

def parse_wheel_filename(filename: str) -> tuple:
    """(normalized name, version, expanded triples in field order)."""
    if not filename.endswith(".whl") or "/" in filename or "\\" in filename:
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "NOT_A_WHEEL", filename=filename)
    fields = filename[:-4].split("-")
    if len(fields) not in (5, 6) or not all(fields):
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "WHEEL_FILENAME", filename=filename)
    python_tags, abi_tags, platform_tags = (field.split(".") for field in fields[-3:])
    triples = [f"{p}-{a}-{t}" for p in python_tags for a in abi_tags for t in platform_tags]
    return normalize_name(fields[0]), fields[1], triples


def wheel_priority(filename: str, tag_sequence: list):
    """Smallest tag_sequence index among the wheel's triples, or None."""
    positions = {tag: index for index, tag in reversed(list(enumerate(tag_sequence)))}
    found = [positions[triple] for triple in parse_wheel_filename(filename)[2] if triple in positions]
    return min(found) if found else None


def choose_wheel(candidates: list, tag_sequence: list) -> str:
    """The CHOSEN wheel among CANDIDATES (filenames; sdists listed are never
    admitted)."""
    if not candidates:
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "NO_CANDIDATE_LISTING")
    ranked = []
    for filename in candidates:
        if not filename.endswith(".whl"):
            continue
        priority = wheel_priority(filename, tag_sequence)
        if priority is not None:
            ranked.append((priority, filename))
    if not ranked:
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "NO_COMPATIBLE_WHEEL")
    ranked.sort()
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "EQUAL_PRIORITY")
    return ranked[0][1]


def generate_tag_sequence(tags_module, python_version: str, abi_tag: str, platform_sequence: list) -> list:
    """TAG_SEQUENCE_GENERATOR_V1 with TAGS_MODULE = pip._vendor.packaging.tags."""
    major, minor = (int(item) for item in python_version.split(".")[:2])
    interpreter = "cp%d%d" % (major, minor)
    cpython_platforms = [item for item in platform_sequence if item != "any"]
    generated = list(tags_module.cpython_tags(python_version=(major, minor), abis=[abi_tag],
                                              platforms=list(cpython_platforms)))
    generated += list(tags_module.compatible_tags(python_version=(major, minor), interpreter=interpreter,
                                                  platforms=list(cpython_platforms)))
    return dedupe_tags(str(tag) for tag in generated)


def dedupe_tags(tags) -> list:
    seen, ordered = set(), []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    return ordered


def derive_target_fields(sys_tags, implementation_tag: str) -> dict:
    """TARGET_TAG_ALGORITHM_V1 from an iterable of tags (sys_tags())."""
    sequence = dedupe_tags(str(tag) for tag in sys_tags)
    platforms = dedupe_tags(tag.split("-", 2)[2] for tag in sequence)
    abi = next(tag.split("-")[1] for tag in sequence if tag.split("-")[0] == implementation_tag)
    return {"tag_sequence": sequence, "platform_sequence": platforms, "abi_tag": abi,
            "platform_tags": sorted(set(platforms))}


def hosted_target_compat_check(lock_names: dict, wheel_listing: dict, hosted_tag_sequence: list,
                               operator_closure=None, hosted_closure=None) -> dict:
    """HOSTED_TARGET_COMPAT_CHECK_V1 on wheel filenames: one chosen
    compatible wheel per member; a closure difference is TARGET_DIVERGENCE."""
    if operator_closure is not None and hosted_closure is not None and operator_closure != hosted_closure:
        _lock_rejected("TARGET_DIVERGENCE", "CLOSURE_DIFFERS")
    return {name: choose_wheel(wheel_listing.get(name, []), hosted_tag_sequence) for name in sorted(lock_names)}


# -- license and engine screening --------------------------------------------

def license_declared_from_metadata(metadata: dict):
    """license_declared: the verbatim License, License-Expression and
    license classifiers of the artifact's own METADATA, or null."""
    classifiers = sorted(item for item in metadata.get("Classifier", []) if item.startswith("License ::"))
    value = {
        "License": metadata.get("License"),
        "License-Expression": metadata.get("License-Expression"),
        "License-Classifiers": classifiers,
    }
    if value["License"] is None and value["License-Expression"] is None and not classifiers:
        return None
    return value


def license_problem(declared):
    """None when the declared terms raise no blocking condition, else the
    condition (UNKNOWN, NON_STANDARD or COPYLEFT)."""
    if declared is None:
        return "UNKNOWN"
    if not isinstance(declared, dict) or set(declared) != set(LICENSE_KEYS):
        return "NON_STANDARD"
    strings = [value for value in (declared["License"], declared["License-Expression"]) if value is not None]
    strings += list(declared["License-Classifiers"])
    if not strings or any(not isinstance(item, str) or not item.strip() for item in strings):
        return "UNKNOWN"
    if any(item.strip().upper() in ("UNKNOWN", "NONE", "N/A") for item in strings):
        return "UNKNOWN"
    if any(_COPYLEFT.search(item) for item in strings):
        return "COPYLEFT"
    expression = declared["License-Expression"]
    if expression is not None:
        tokens = _SPDX_TOKEN.findall(expression)
        if "".join(tokens) != re.sub(r"\s+", "", expression) or not tokens:
            return "NON_STANDARD"
    elif declared["License"] is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", declared["License"]):
        return "NON_STANDARD"
    return None


def screen_records(records: list, accepted_members=()) -> None:
    """Forbidden-engine, classification and license rules over the records."""
    for record in records:
        name = record["name"]
        if name in DENYLIST_SEED or record["capability_class"] == "FORBIDDEN_ENGINE":
            _lock_rejected("FORBIDDEN_ENGINE", None, name=name)
        if record["capability_class"] not in CAPABILITY_CLASSES:
            _lock_rejected("UNCLASSIFIED_MEMBER", None, name=name)
    for record in records:
        if record["role"] in ("DIRECT", "TRANSITIVE"):
            problem = license_problem(record["license_declared"])
            if problem is not None and record["name"] not in accepted_members:
                _lock_rejected("LICENSE_UNACCEPTED", problem, name=record["name"])


def lock_review_digest(records: list, artifact_targets: list, lock_artifacts: list) -> str:
    return canonical_digest({"spec": "LOCK_REVIEW_RECORD_V1", "records": records,
                             "artifact_targets": artifact_targets, "lock_artifacts": lock_artifacts})


def _check_record_shapes(records, artifact_targets, lock_artifacts) -> None:
    if not isinstance(records, list) or not isinstance(artifact_targets, list) or not isinstance(lock_artifacts, list):
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "REVIEW_SHAPE")
    if [record.get("name") for record in records] != sorted(record.get("name") for record in records):
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "RECORDS_UNSORTED")
    for record in records:
        if (
            not isinstance(record, dict)
            or tuple(sorted(record)) != RECORD_KEYS
            or record["role"] not in ROLES
            or type(record["native_binaries"]) is not int
            or record["native_binaries"] not in (0, 1)
            or record["required_by"] != sorted(record["required_by"])
        ):
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "RECORD_SHAPE", name=record.get("name"))
    if [target.get("id") for target in artifact_targets] != list(ARTIFACT_TARGET_IDS):
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "TARGET_SET")
    for target in artifact_targets:
        if tuple(sorted(target)) != ARTIFACT_TARGET_KEYS or any(target[key] is None for key in target):
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "TARGET_FIELDS", target=target.get("id"))
    keys = [(entry.get("name"), entry.get("target_id")) for entry in lock_artifacts]
    if keys != sorted(keys) or len(set(keys)) != len(keys):
        _lock_rejected("ARTIFACT_SET_UNDETERMINED", "LOCK_ARTIFACTS_ORDER")
    for entry in lock_artifacts:
        if tuple(sorted(entry)) != ("artifact_kind", "filename", "name", "sha256", "target_id", "version"):
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "LOCK_ARTIFACT_SHAPE", name=entry.get("name"))
        if entry["artifact_kind"] != "WHEEL" or not str(entry["filename"]).endswith(".whl"):
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "NOT_A_WHEEL", name=entry["name"])
        if not _WHEEL_SHA.match(str(entry["sha256"])):
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "HASH_UNDETERMINED", name=entry["name"])


def review_lock(manifest: dict, lock_bytes: bytes, requires=None, candidate_wheels=None,
                accepted_members=()) -> dict:
    """DEPENDENCY_LOCK_REVIEW_V1 over the manifest records, the lock bytes and,
    when given, the reviewed wheel metadata REQUIRES {name: [Requires-Dist]}
    and the index candidate listing {name: [filenames]}. Returns the review
    evidence; any rejection raises Rejected(RENDER_DEPENDENCY_LOCK_REJECTED)."""
    model = manifest.get("dependency_model")
    records = manifest.get("dependency_lock_review")
    targets = manifest.get("artifact_targets")
    artifacts = manifest.get("lock_artifacts")
    _check_record_shapes(records, targets, artifacts)
    if not isinstance(model, dict) or model.get("spec_id") != "DEPENDENCY_MODEL_V1":
        _lock_rejected("CLOSURE_MISMATCH", "DEPENDENCY_MODEL")
    if [tuple(item) for item in model.get("baseline_entries", [])] != list(BASELINE_ENTRIES):
        _lock_rejected("BASELINE_ENTRY_CHANGED", "MANIFEST_BASELINE")
    if model.get("direct_distributions") != list(DIRECT_DISTRIBUTIONS):
        _lock_rejected("CLOSURE_MISMATCH", "DIRECT_DISTRIBUTIONS")
    tooling = model.get("tooling_set")
    if not isinstance(tooling, list):
        _lock_rejected("CLOSURE_MISMATCH", "TOOLING_SET")
    lock = parse_lock(lock_bytes)
    by_name = {record["name"]: record for record in records}
    for name, version in BASELINE_ENTRIES:
        if name not in lock:
            _lock_rejected("CLOSURE_MISMATCH", "BASELINE_MISSING", name=name)
        if lock[name][0] != version:
            _lock_rejected("BASELINE_ENTRY_CHANGED", None, name=name)
    full_lock = set(by_name)
    if set(lock) != full_lock:
        _lock_rejected("CLOSURE_MISMATCH", "LOCK_NAMES", missing=sorted(full_lock - set(lock)),
                       undeclared=sorted(set(lock) - full_lock))
    for name, record in by_name.items():
        if lock[name][0] != record["version"]:
            _lock_rejected("CLOSURE_MISMATCH", "VERSION", name=name)
        expected_role = ("BASELINE" if name in dict(BASELINE_ENTRIES)
                         else "DIRECT" if name in DIRECT_DISTRIBUTIONS else "TRANSITIVE")
        if record["role"] != expected_role:
            _lock_rejected("CLOSURE_MISMATCH", "ROLE", name=name)
    if requires is not None:
        closures = {}
        for target in targets:
            rendering, rendering_edges = compute_closure(requires, DIRECT_DISTRIBUTIONS, target)
            baseline, baseline_edges = compute_closure(requires, ("jsonschema", "referencing"), target)
            if baseline != set(dict(BASELINE_ENTRIES)):
                _lock_rejected("CLOSURE_MISMATCH", "BASELINE_CLOSURE", target=target["id"])
            closures[target["id"]] = (rendering | baseline, rendering_edges | baseline_edges)
        reference = closures[ARTIFACT_TARGET_IDS[0]]
        for target_id, closure in closures.items():
            if closure != reference:
                _lock_rejected("TARGET_DIVERGENCE", None, target=target_id)
        names, edges = reference
        if names != full_lock:
            _lock_rejected("CLOSURE_MISMATCH", "RENDERING_CLOSURE", missing=sorted(names - full_lock),
                           undeclared=sorted(full_lock - names))
        for name, record in by_name.items():
            required_by = sorted({parent for parent, child in edges if child == name})
            if record["required_by"] != required_by:
                _lock_rejected("CLOSURE_MISMATCH", "REQUIRED_BY", name=name)
    target_map = {target["id"]: target for target in targets}
    for name, record in by_name.items():
        for target_id in ARTIFACT_TARGET_IDS:
            matching = [entry for entry in artifacts if entry["name"] == name and entry["target_id"] == target_id]
            if len(matching) != 1:
                _lock_rejected("ARTIFACT_SET_UNDETERMINED", "MISSING_TARGET_WHEEL", name=name, target=target_id)
            entry = matching[0]
            if entry["version"] != record["version"]:
                _lock_rejected("CLOSURE_MISMATCH", "ARTIFACT_VERSION", name=name)
            wheel_name, wheel_version, _ = parse_wheel_filename(entry["filename"])
            if wheel_name != name or wheel_version != record["version"]:
                _lock_rejected("ARTIFACT_SET_UNDETERMINED", "WHEEL_IDENTITY", name=name)
            sequence = target_map[target_id]["tag_sequence"]
            if wheel_priority(entry["filename"], sequence) is None:
                _lock_rejected("SELECTED_WHEEL_INCOMPATIBLE", None, name=name, target=target_id)
            if candidate_wheels is not None and choose_wheel(candidate_wheels.get(name, []), sequence) != entry["filename"]:
                _lock_rejected("SELECTION_NOT_PREFERRED", None, name=name, target=target_id)
        expected = sorted({entry["sha256"] for entry in artifacts if entry["name"] == name})
        if lock[name][1] != expected:
            _lock_rejected("HASH_SET_MISMATCH", None, name=name)
    extra_artifacts = {entry["name"] for entry in artifacts} - full_lock
    if extra_artifacts:
        _lock_rejected("HASH_SET_MISMATCH", "UNDECLARED_ARTIFACT", names=sorted(extra_artifacts))
    for item in tooling:
        if normalize_name(item.get("name", "")) in DENYLIST_SEED:
            _lock_rejected("FORBIDDEN_ENGINE", "TOOLING_SET", name=item.get("name"))
    screen_records(records, accepted_members)
    digest = lock_review_digest(records, targets, artifacts)
    if manifest.get("lock_review_digest") != digest:
        _lock_rejected("CLOSURE_MISMATCH", "LOCK_REVIEW_DIGEST", computed=digest)
    return {"result": "PASS", "lock_review_digest": digest, "full_lock": sorted(full_lock),
            "forbidden_engine_result": "NONE_PRESENT"}


def approved_installed_set(manifest: dict) -> set:
    pairs = {(record["name"], record["version"]) for record in manifest["dependency_lock_review"]}
    for item in manifest["dependency_model"]["tooling_set"]:
        pairs.add((normalize_name(item["name"]), item["version"]))
    return pairs


def installed_set_equality(installed, manifest: dict) -> None:
    """INSTALLED SET EQUALITY over (name, version) pairs of the operator
    prefix: RENDER_ENVIRONMENT_UNVERIFIED (DEPENDENCY_SET or
    FORBIDDEN_ENGINE_PRESENT)."""
    observed = {(normalize_name(name), version) for name, version in installed}
    if any(name in DENYLIST_SEED for name, _ in observed):
        raise Rejected(ENV_UNVERIFIED, "FORBIDDEN_ENGINE_PRESENT")
    expected = approved_installed_set(manifest)
    if observed != expected:
        raise Rejected(ENV_UNVERIFIED, "DEPENDENCY_SET", extra=sorted(observed - expected),
                       missing=sorted(expected - observed))


def wheel_review_record(path) -> dict:
    """METADATA, RECORD and native-binary facts of one wheel archive, read
    without extracting, installing, importing or executing anything."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        dist_infos = sorted({name.split("/", 1)[0] for name in names if name.split("/", 1)[0].endswith(".dist-info")})
        if len(dist_infos) != 1:
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "DIST_INFO", wheel=os.path.basename(path))
        metadata_text = archive.read(dist_infos[0] + "/METADATA").decode("utf-8")
        record_text = archive.read(dist_infos[0] + "/RECORD").decode("utf-8")
        native = 0
        for row in record_text.splitlines():
            member = row.rsplit(",", 2)[0] if row.count(",") >= 2 else row
            if member.endswith((".so", ".pyd", ".dylib", ".dll")) or ".so." in member:
                native = 1
            elif member in names and not member.endswith("/"):
                with archive.open(member) as handle:
                    if handle.read(4) == b"\x7fELF":
                        native = 1
    metadata = parse_metadata(metadata_text)
    return {"metadata": metadata, "native_binaries": native, "record_rows": len(record_text.splitlines())}


def parse_metadata(text: str) -> dict:
    """Core metadata headers (RFC 822 style, body ignored); repeated fields
    collected as lists for Requires-Dist and Classifier."""
    headers, multi = {}, {"Requires-Dist": [], "Classifier": []}
    current = None
    for line in text.split("\n"):
        if line == "":
            break
        if line[:1] in (" ", "\t") and current is not None:
            if current in multi:
                multi[current][-1] += "\n" + line
            else:
                headers[current] += "\n" + line
            continue
        key, _, value = line.partition(":")
        current = key.strip()
        value = value.strip()
        if current in multi:
            multi[current].append(value)
        else:
            headers[current] = value
    headers.update(multi)
    return headers


# =============================================================================
# APT_TRUST_MODEL_V1: SOURCE_EXPANSION_V1 / SOURCE_FIELDS_V1
# =============================================================================

DEB822_FIELDS = ("types", "uris", "suites", "components", "signed-by", "enabled", "architectures", "description",
                 "x-repolib-name")
ONE_LINE_OPTIONS = ("signed-by", "arch")
INSTALL_FLAGS = ("--yes", "--no-install-recommends", "--no-remove")


def _source_unapproved(detail, **evidence):
    raise Rejected(APT_SOURCE_UNAPPROVED, APT_SOURCE_UNAPPROVED, detail, **evidence)


def _keyring_path(value: str, origin: str) -> str:
    if not value.startswith("/") or any(ch.isspace() for ch in value) or "\n" in value:
        _source_unapproved("SIGNED_BY_NOT_KEYRING_PATH", origin=origin)
    return value


def parse_one_line_sources(text: str, origin: str) -> list:
    """Enabled one-line entries -> [{types, uris, suites, components, signed_by}]."""
    entries = []
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        options = {}
        match = re.match(r"(\S+)\s+\[([^\]]*)\]\s+(.*)\Z", line)
        if match:
            kind, option_text, rest = match.groups()
            for item in option_text.split():
                name, sep, value = item.partition("=")
                name = name.lower()
                if not sep or name not in ONE_LINE_OPTIONS or name in options:
                    _source_unapproved("OPTION", origin=origin, line=number, option=name)
                options[name] = value
        else:
            kind, _, rest = line.partition(" ")
        fields = rest.split()
        if len(fields) < 2:
            _source_unapproved("ONE_LINE_SHAPE", origin=origin, line=number)
        if kind not in ("deb", "deb-src"):
            _source_unapproved("TYPE", origin=origin, line=number)
        if "signed-by" not in options:
            _source_unapproved("SIGNED_BY_ABSENT", origin=origin, line=number)
        components = fields[2:] if not fields[1].endswith("/") else [""]
        entries.append({"types": [kind], "uris": [fields[0]], "suites": [fields[1]], "components": components,
                        "signed_by": _keyring_path(options["signed-by"], origin)})
    return entries


def parse_deb822_sources(text: str, origin: str) -> list:
    """Enabled deb822 stanzas -> entries, under SOURCE_FIELDS_V1."""
    stanzas, current, last = [], [], None
    for raw in text.split("\n") + [""]:
        if raw.strip() == "":
            if current:
                stanzas.append(current)
            current, last = [], None
            continue
        if raw.startswith("#"):
            continue
        if raw[:1] in (" ", "\t"):
            if last is None:
                _source_unapproved("DEB822_SHAPE", origin=origin)
            current[last][1].append(raw.strip())
            continue
        name, sep, value = raw.partition(":")
        if not sep or not name or name != name.strip():
            _source_unapproved("DEB822_SHAPE", origin=origin)
        current.append([name, [value.strip()]])
        last = len(current) - 1
    entries = []
    for stanza in stanzas:
        fields = {}
        for name, values in stanza:
            key = name.lower()
            if key not in DEB822_FIELDS:
                _source_unapproved("FIELD", origin=origin, field=name)
            if key in fields:
                _source_unapproved("DUPLICATE_FIELD", origin=origin, field=name)
            fields[key] = values
        enabled = " ".join(fields.get("enabled", ["yes"])).strip().lower()
        if enabled == "no":
            continue
        if enabled != "yes":
            _source_unapproved("ENABLED_VALUE", origin=origin)
        signed = fields.get("signed-by")
        if signed is None:
            _source_unapproved("SIGNED_BY_ABSENT", origin=origin)
        if len(signed) != 1 or len(signed[0].split()) != 1:
            _source_unapproved("SIGNED_BY_NOT_KEYRING_PATH", origin=origin)
        for required in ("types", "uris", "suites"):
            if required not in fields or not " ".join(fields[required]).split():
                _source_unapproved("DEB822_SHAPE", origin=origin, field=required)
        types = " ".join(fields["types"]).split()
        if any(item not in ("deb", "deb-src") for item in types):
            _source_unapproved("TYPE", origin=origin)
        suites = " ".join(fields["suites"]).split()
        components = " ".join(fields.get("components", [])).split()
        entries.append({"types": types, "uris": " ".join(fields["uris"]).split(), "suites": suites,
                        "components": components or [""], "signed_by": _keyring_path(signed[0], origin)})
    return entries


def expand_entries(entries: list, keyring_sha256) -> set:
    """SOURCE_EXPANSION_V1 tuples (type, uri, suite, component, keyring_path,
    keyring_sha256); KEYRING_SHA256(path) returns the file digest or None."""
    tuples = set()
    for entry in entries:
        digest = keyring_sha256(entry["signed_by"])
        for kind in entry["types"]:
            for uri in entry["uris"]:
                for suite in entry["suites"]:
                    for component in entry["components"]:
                        tuples.add((kind, uri, suite, component, entry["signed_by"], digest))
    return tuples


def approved_tuples(sources: list) -> set:
    tuples = set()
    for stanza in sources:
        signed = stanza["signed_by"]
        for uri in stanza["uris"]:
            for suite in stanza["suites"]:
                for component in stanza["components"]:
                    tuples.add((stanza["type"], uri, suite, component, signed["keyring_path"],
                                signed["keyring_sha256"]))
    return tuples


def sorted_tuples(tuples) -> list:
    return sorted((list(item) for item in tuples), key=canonical_json_bytes)


def check_sources(source_files: list, approved_sources: list, keyring_sha256) -> list:
    """SOURCE_FILES: [(path, kind 'one-line'|'deb822', text)] read from the
    natively resolved locations. Returns the sorted effective tuples."""
    entries = []
    for path, kind, text in source_files:
        entries += parse_one_line_sources(text, path) if kind == "one-line" else parse_deb822_sources(text, path)
    effective = expand_entries(entries, keyring_sha256)
    for item in effective:
        if item[5] is None:
            _source_unapproved("KEYRING_UNREADABLE", keyring=item[4])
    approved = approved_tuples(approved_sources)
    if effective != approved:
        _source_unapproved("SOURCE_SET", extra=sorted_tuples(effective - approved),
                           missing=sorted_tuples(approved - effective))
    return sorted_tuples(effective)


def source_files_from_listing(sourcelist_path: str, sourceparts_entries: list, read) -> list:
    """The source files apt reads: the main list (one-line) and the parts
    directory entries ending in .list (one-line) or .sources (deb822). An
    entry of any other name is ignored by apt and recorded only."""
    files = []
    text = read(sourcelist_path)
    if text is not None:
        files.append((sourcelist_path, "one-line", text))
    for path in sorted(sourceparts_entries):
        if path.endswith(".list"):
            files.append((path, "one-line", read(path)))
        elif path.endswith(".sources"):
            files.append((path, "deb822", read(path)))
    return files


# =============================================================================
# CONFIG_CHECK_V1 (APT_KEY_CASE_V1, BINARY_SCOPE_V1)
# =============================================================================

_DUMP_LINE = re.compile(r'(\S+) "(.*)";\Z')
_TRUE = ("1", "yes", "true", "with", "on", "enable")
_FALSE = ("0", "no", "false", "without", "off", "disable")


def _config_unapproved(detail, **evidence):
    raise Rejected(APT_CONFIG_UNAPPROVED, APT_CONFIG_UNAPPROVED, detail, **evidence)


def ascii_lower(text: str) -> str:
    return "".join(chr(ord(ch) + 32) if "A" <= ch <= "Z" else ch for ch in text)


def parse_config_dump(text: str) -> list:
    """`apt-config dump` -> [[key, value]] in dump order (list keys keep
    their `::` suffix)."""
    pairs = []
    for line in text.split("\n"):
        if line == "":
            continue
        match = _DUMP_LINE.match(line)
        if not match:
            _config_unapproved("DUMP_LINE_MALFORMED", line=line[:200])
        pairs.append([match.group(1), match.group(2)])
    return pairs


def canonical_subset(pairs: list) -> list:
    """The complete dump minus the closed inert allowlist (`Binary` and
    every key equal to or beginning with `CommandLine`), sorted by the
    lowercased key then value."""
    subset = []
    for key, value in pairs:
        lowered = ascii_lower(key)
        if lowered == "binary" or lowered.startswith("commandline"):
            continue
        subset.append([key, value])
    subset.sort(key=lambda pair: (ascii_lower(pair[0]), pair[1]))
    return subset


def effective_key(lowered: str) -> str:
    """BINARY_SCOPE_V1: drop one leading binary::<name>:: segment."""
    if lowered.startswith("binary::"):
        rest = lowered[len("binary::"):]
        name, sep, remainder = rest.partition("::")
        if name and sep:
            if remainder.startswith("binary::"):
                _config_unapproved("BINARY_SCOPE_NESTED", key=lowered)
            return remainder
    return lowered


def _is_true(value: str) -> bool:
    lowered = ascii_lower(value)
    return lowered not in _FALSE


def _is_false(value: str) -> bool:
    return ascii_lower(value) in _FALSE


def never_approvable(key: str, value: str):
    """The never_approvable reason for one lowercased key and its value, or None."""
    insecure_true = ("acquire::allowinsecurerepositories", "acquire::allowdowngradetoinsecurerepositories",
                     "acquire::allowweakrepositories", "apt::get::allowunauthenticated")
    if key in insecure_true and _is_true(value):
        return "INSECURE_MODE"
    if key == "acquire::check-valid-until" and not _is_true(value):
        return "CHECK_VALID_UNTIL"
    if re.fullmatch(r"acquire::[^:]+(::[^:]+)?::verify-(peer|host)", key) and not _is_true(value):
        return "VERIFY_PEER"
    if key in ("acquire::verify-peer", "acquire::verify-host") and not _is_true(value):
        return "VERIFY_PEER"
    if key.startswith("dpkg::options"):
        lowered_value = ascii_lower(value)
        if any(token in lowered_value for token in ("--force-", "--admindir", "--root", "--instdir")):
            return "DPKG_OPTIONS"
    if key == "apt::default-release" and value != "":
        return "DEFAULT_RELEASE"
    if key == "dir" and value != "/":
        return "DIR_RELOCATED"
    if key == "rootdir" and value != "/":
        return "ROOTDIR"
    if re.fullmatch(r"apt::hashes::[^:]+::(untrusted|weak)", key) and _is_true(value):
        return "HASHES"
    if key.startswith("apt::key::") and key.rsplit("::", 1)[-1] == "gpgvcommand" and value != "":
        return "GPGV_COMMAND"
    return None


def is_hook_key(key: str) -> bool:
    return any(token in key for token in ("invoke", "pre-install-pkgs", "post-invoke", "tools"))


def is_proxy_key(key: str) -> bool:
    return bool(re.fullmatch(r"acquire::(.+::)?(proxy|proxy-auto-detect)(::.*)?", key))


def check_config(pairs: list, approved: list, status_path=None) -> list:
    """CONFIG_CHECK_V1 over the dump pairs; returns the canonical subset.
    STATUS_PATH is the natively resolved Dir::State::status."""
    subset = canonical_subset(pairs)
    by_effective = {}
    for key, value in subset:
        lowered = ascii_lower(key)
        if lowered.endswith("::"):
            continue
        by_effective.setdefault(effective_key(lowered), set()).add(value)
    for name, values in sorted(by_effective.items()):
        if len(values) > 1:
            _config_unapproved("DUPLICATE_KEY", key=name)
    for key, value in subset:
        lowered = ascii_lower(key)
        for name in (lowered, effective_key(lowered)):
            reason = never_approvable(name.rstrip(":") if name.endswith("::") else name, value)
            if reason is not None:
                _config_unapproved("NEVER_APPROVABLE", key=key, rule=reason)
    if status_path is not None and status_path != "/var/lib/dpkg/status":
        _config_unapproved("NEVER_APPROVABLE", rule="STATUS_PATH")
    lowered_subset = [[ascii_lower(key), value] for key, value in subset]
    lowered_approved = sorted([[ascii_lower(key), value] for key, value in approved],
                              key=lambda pair: (pair[0], pair[1]))
    if lowered_subset != lowered_approved:
        _config_unapproved("CONFIG_MISMATCH")
    return subset


def parse_apt_config_shell(stdout: str, stderr: str, requested: list) -> dict:
    """APT_SHELL_PARSE_V1. REQUESTED: [(NAME, 'key/f'|'key/d'|'key')]."""
    if stderr != "":
        _config_unapproved("SHELL_OUTPUT_MALFORMED", why="STDERR")
    lines = _split_lines(stdout)
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) != len(requested):
        _config_unapproved("SHELL_OUTPUT_MALFORMED", why="LINE_COUNT")
    values = {}
    for line, (name, key) in zip(lines, requested):
        prefix = name + "='"
        if not line.startswith(prefix) or not line.endswith("'") or len(line) < len(prefix) + 1:
            _config_unapproved("SHELL_OUTPUT_MALFORMED", why="LINE", name=name)
        body = line[len(prefix):-1]
        if "\x00" in body:
            _config_unapproved("SHELL_OUTPUT_MALFORMED", why="NUL", name=name)
        if "'" in body.replace("'\\''", ""):
            _config_unapproved("SHELL_OUTPUT_MALFORMED", why="QUOTE", name=name)
        value = body.replace("'\\''", "'")
        if key.endswith(("/f", "/d")) and not value.startswith("/"):
            _config_unapproved("SHELL_OUTPUT_MALFORMED", why="NOT_ABSOLUTE", name=name)
        if key.endswith("/d") and value.endswith("/") and value != "/":
            value = value[:-1]
        values[name] = value
    return values


def check_preferences(preference_files: list, policy_output: str) -> None:
    """CONFIG_CHECK_V1 pins: every preferences file absent or without a
    stanza, and `apt-cache policy` listing no pinned package."""
    for path, text in preference_files:
        if text is None:
            continue
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                _config_unapproved("PIN", path=path)
    in_pinned = False
    for line in policy_output.split("\n"):
        if line.startswith("Pinned packages:"):
            in_pinned = True
            continue
        if in_pinned and line.strip():
            _config_unapproved("PIN", line=line.strip()[:200])
        match = re.match(r"\s*(-?\d+) ", line)
        if match and not in_pinned and int(match.group(1)) not in (100, 500, 1):
            _config_unapproved("PIN_PRIORITY", line=line.strip()[:200])


def check_update_output(returncode: int, output: str, approved_sources: list) -> list:
    """UPDATE_SEMANTICS_V1; returns the matching Hit:/Get: lines."""
    lines = output.split("\n")
    if returncode != 0 or any(line.startswith(("Err:", "E:", "W:")) for line in lines):
        raise Rejected(APT_UPDATE_FAILED, APT_UPDATE_FAILED, "UPDATE_ERROR")
    matched = []
    pairs = sorted({(uri, suite) for stanza in approved_sources for uri in stanza["uris"]
                    for suite in stanza["suites"]})
    for uri, suite in pairs:
        pattern = re.compile(r"(Hit|Get):\d+ " + re.escape(uri.rstrip("/")) + r"/? " + re.escape(suite) + r" InRelease\b")
        hits = [line for line in lines if pattern.match(line)]
        if not hits:
            raise Rejected(APT_UPDATE_FAILED, APT_UPDATE_FAILED, "INRELEASE_NOT_FETCHED", uri=uri, suite=suite)
        matched += hits
    return matched


def install_argv(apt_plan: dict) -> list:
    """APT_NONINTERACTIVE_V1 governed argv tail."""
    if apt_plan["install_flags"] != list(INSTALL_FLAGS):
        _config_unapproved("INSTALL_FLAGS")
    return (["/usr/bin/apt-get", "install"] + list(INSTALL_FLAGS)
            + ["%s=%s" % (item["name"], item["version"]) for item in apt_plan["packages"]])


def parse_dpkg_query_state(text: str) -> list:
    """`dpkg-query -W -f '${Package}\\t${Architecture}\\t${Version}\\t${Status}\\n'`."""
    rows = []
    for line in text.split("\n"):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) != 4:
            raise Rejected(APT_UNEXPECTED_CHANGE, APT_UNEXPECTED_CHANGE, "DPKG_QUERY_MALFORMED")
        rows.append(fields)
    rows.sort(key=lambda row: (row[0], row[1]))
    return rows


def apt_installed_delta(before: list, after: list, origins: dict, compare_versions) -> list:
    """The complete sorted change set between two dpkg states
    ([package, architecture, version, status]); COMPARE_VERSIONS(a, b) is
    the dpkg version ordering (negative, zero, positive)."""
    old = {(row[0], row[1]): row for row in before}
    new = {(row[0], row[1]): row for row in after}
    delta = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a is not None and b is not None and a[2] == b[2] and a[3] == b[3]:
            continue
        if a is None:
            change = "ADDED"
        elif b is None:
            change = "REMOVED"
        elif a[2] == b[2]:
            change = "STATUS_CHANGED"
        else:
            change = "UPGRADED" if compare_versions(b[2], a[2]) > 0 else "DOWNGRADED"
        delta.append({"package": key[0], "architecture": key[1], "change": change,
                      "version_before": a[2] if a else None, "version_after": b[2] if b else None,
                      "origin": origins.get(key) if change in ("ADDED", "UPGRADED") else None})
    return delta


def check_apt_delta(delta: list, after: list, apt_plan: dict, identity_critical: set, origin_allowed) -> None:
    """post_install_checks (a) to (d): identity-critical first, then pins,
    unexpected changes and origins."""
    for entry in delta:
        if entry["package"] in identity_critical:
            raise Rejected(ENV_UNVERIFIED, APT_UNEXPECTED_CHANGE, "IDENTITY_CRITICAL", package=entry["package"])
    state = {(row[0], row[1]): row for row in after}
    for item in apt_plan["packages"]:
        row = state.get((item["name"], item["architecture"]))
        if row is None or row[2] != item["version"] or row[3] != "install ok installed":
            raise Rejected(ENV_UNVERIFIED, "APT_PIN", None, package=item["name"])
    for entry in delta:
        if entry["change"] in ("DOWNGRADED", "REMOVED", "STATUS_CHANGED"):
            raise Rejected(ENV_UNVERIFIED, APT_UNEXPECTED_CHANGE, entry["change"], package=entry["package"])
        if entry["change"] == "ADDED" and state[(entry["package"], entry["architecture"])][3] != "install ok installed":
            raise Rejected(ENV_UNVERIFIED, APT_UNEXPECTED_CHANGE, "ADDED_STATUS", package=entry["package"])
        if entry["change"] in ("ADDED", "UPGRADED") and not origin_allowed(entry["origin"]):
            raise Rejected(ENV_UNVERIFIED, "APT_ORIGIN", None, package=entry["package"])


def parse_policy_origin(policy_text: str, version: str) -> list:
    """(uri, suite, component) origins of VERSION from `apt-cache policy <pkg>`."""
    origins, current = [], None
    for line in policy_text.split("\n"):
        match = re.match(r"\s{5}(\*\*\* )?(\S+) (-?\d+)\Z", line) or re.match(r" (\*\*\*| {3}) (\S+) (-?\d+)\Z", line)
        if match:
            current = match.group(2)
            continue
        origin = re.match(r"\s+-?\d+ (\S+) ([^/\s]+)/(\S+) \S+ Packages\Z", line)
        if origin and current == version:
            origins.append((origin.group(1), origin.group(2), origin.group(3)))
    return origins


# =============================================================================
# DPKG_CONFIG_CHECK_V1
# =============================================================================

DPKG_NEVER_APPROVABLE = ("pre-invoke", "post-invoke", "status-logger", "force-", "no-triggers", "admindir", "root",
                         "instdir", "no-act", "dry-run", "simulate")
# DPKG_OPTION_SYNTAX_V1: `name`, `name=value` or `name<spaces/tabs>value`; the form is
# decided by the first byte after the name. Quoted values are outside the admitted subset.
_DPKG_LINE = re.compile(rb"(-{0,2})([A-Za-z0-9_-]+)(?:=([^\n]*)|[ \t]+([^\n]*))?\Z")
_DPKG_SEPARATOR_VALUE_FORBIDDEN_START = (b"=", b" ", b"\t", b'"', b"'")
DPKG_FIXED_CONFIG = "/etc/dpkg/dpkg.cfg"
DPKG_CONFIG_DIR = "/etc/dpkg/dpkg.cfg.d"
POLICY_RC_D = "/usr/sbin/policy-rc.d"


def _dpkg_reason(reason, **evidence):
    raise Rejected(APT_CONFIG_UNAPPROVED, reason, None, **evidence)


def parse_dpkg_config(data: bytes, path: str = "") -> list:
    """The ordered normalized options of one dpkg configuration file."""
    if b"\x00" in data:
        _dpkg_reason("DPKG_CONFIG_MALFORMED", path=path, why="NUL")
    options = []
    for number, line in enumerate(bytes(data).split(b"\n"), 1):
        stripped = line.strip(b" \t")
        if not stripped or stripped.startswith(b"#"):
            continue
        match = _DPKG_LINE.match(line)
        if not match:
            _dpkg_reason("DPKG_CONFIG_MALFORMED", path=path, line=number)
        name = ascii_lower(match.group(2).decode("ascii"))
        value = match.group(3)
        if value is None and match.group(4) is not None:
            value = match.group(4).rstrip(b" \t")
            if not value or value.startswith(_DPKG_SEPARATOR_VALUE_FORBIDDEN_START):
                _dpkg_reason("DPKG_CONFIG_MALFORMED", path=path, line=number, why="SEPARATOR_VALUE")
        if value is not None:
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError:
                _dpkg_reason("DPKG_CONFIG_MALFORMED", path=path, line=number, why="VALUE_ENCODING")
        options.append([name, value])
    return options


def parse_diversions(data: bytes) -> list:
    lines = bytes(data).decode("utf-8", "surrogateescape").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) % 3:
        _dpkg_reason("DPKG_CONFIG_MALFORMED", path="/var/lib/dpkg/diversions")
    triples = [lines[index:index + 3] for index in range(0, len(lines), 3)]
    return sorted(triples, key=lambda item: item[0])


def parse_statoverride(data: bytes) -> list:
    rows = []
    for line in bytes(data).decode("utf-8", "surrogateescape").split("\n"):
        if line == "":
            continue
        fields = line.split(" ")
        if len(fields) != 4 or not all(fields):
            _dpkg_reason("DPKG_CONFIG_MALFORMED", path="/var/lib/dpkg/statoverride")
        rows.append(fields)
    return sorted(rows, key=lambda item: item[3])


def build_dpkg_record(fs, home: str, neutral: str) -> dict:
    """DPKG_CONFIG_RECORD_V1 discovery over FS (lstat, listdir, read_bytes)."""
    for path in (home.rstrip("/") + "/.dpkg.cfg", neutral.rstrip("/") + "/.dpkg.cfg"):
        if fs.lexists(path):
            _dpkg_reason("DPKG_CONFIG_FILE_SET", path=path, why="ABSENT_REQUIRED")
    candidates = [DPKG_FIXED_CONFIG] + [DPKG_CONFIG_DIR + "/" + name for name in fs.listdir(DPKG_CONFIG_DIR)]
    files = []
    for path in sorted(candidates):
        info = fs.lstat(path)
        if info is None:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            _dpkg_reason("DPKG_CONFIG_FILE_TYPE", path=path)
        data = fs.read_bytes(path)
        files.append({"path": path, "sha256": sha256_hex(data), "options": parse_dpkg_config(data, path)})
    diversions = fs.read_bytes("/var/lib/dpkg/diversions")
    statoverride = fs.read_bytes("/var/lib/dpkg/statoverride")
    policy = fs.read_bytes(POLICY_RC_D) if fs.lexists(POLICY_RC_D) else None
    return {
        "files": files,
        "diversions": parse_diversions(diversions or b""),
        "statoverride": parse_statoverride(statoverride or b""),
        "policy_rc_d": {"path": POLICY_RC_D, "sha256": sha256_hex(policy) if policy is not None else "ABSENT"},
    }


def check_dpkg_record(record: dict, approved: dict, other_checks_passed: bool = True) -> None:
    """DPKG_CONFIG_CHECK_V1 comparison with NO_DEBSIG_EXACT_ADMISSION_V1 order.
    OTHER_CHECKS_PASSED carries conditions (5) to (8)."""
    host_paths = [item["path"] for item in record["files"]]
    approved_paths = [item["path"] for item in approved["files"]]
    if host_paths != approved_paths:
        _dpkg_reason("DPKG_CONFIG_FILE_SET", extra=sorted(set(host_paths) - set(approved_paths)),
                     missing=sorted(set(approved_paths) - set(host_paths)))
    for item in record["files"]:
        for name, _ in item["options"]:
            if any(name == token or name.startswith(token) for token in DPKG_NEVER_APPROVABLE):
                _dpkg_reason("DPKG_CONFIG_NEVER_APPROVABLE", path=item["path"], option=name)
    approved_by_path = {item["path"]: item for item in approved["files"]}
    for item in record["files"]:
        expected = approved_by_path[item["path"]]
        for index, (name, value) in enumerate(item["options"]):
            if not name.startswith("no-debsig"):
                continue
            admitted = (
                name == "no-debsig"
                and value is None
                and item["sha256"] == expected["sha256"]
                and index < len(expected["options"])
                and expected["options"][index] == ["no-debsig", None]
            )
            if not admitted:
                _dpkg_reason("DPKG_CONFIG_NO_DEBSIG_UNAPPROVED", path=item["path"], position=index)
            if not other_checks_passed:
                _dpkg_reason("DPKG_CONFIG_NO_DEBSIG_UNAPPROVED", path=item["path"], why="ADMISSION_CHECKS")
    if record["files"] != approved["files"]:
        _dpkg_reason("DPKG_CONFIG_MISMATCH")
    if record["diversions"] != approved["diversions"]:
        _dpkg_reason("DPKG_DIVERSION")
    if record["statoverride"] != approved["statoverride"]:
        _dpkg_reason("DPKG_STATOVERRIDE")
    if record["policy_rc_d"] != approved["policy_rc_d"]:
        _dpkg_reason("DPKG_POLICY_RC")


def dpkg_recheck(before: dict, after: dict) -> None:
    """F0: files, digests and options unchanged (DPKG_CONFIG_CHANGED)."""
    if before["files"] != after["files"]:
        raise Rejected(APT_UNEXPECTED_CHANGE, APT_UNEXPECTED_CHANGE, "DPKG_CONFIG_CHANGED")


# =============================================================================
# TREE DIGESTS (TREE_DIGEST_V1 variants used by the identity)
# =============================================================================

_PRINTABLE_NAME = re.compile(r'[\x20-\x7e]*\Z')


def tree_records(root: str, kind: str) -> list:
    """TREE_DIGEST_V1 records of ROOT for KIND STDLIB (STDLIB_TREE rules) or
    PIP (every __pycache__ directory excluded), sorted by relative path."""
    records = []
    pending = [""]
    while pending:
        relative = pending.pop()
        directory = os.path.join(root, relative) if relative else root
        with os.scandir(directory) as iterator:
            children = list(iterator)
        if not children and relative:
            records.append(["D", relative])
        for child in children:
            child_rel = (relative + "/" if relative else "") + child.name
            mode = child.stat(follow_symlinks=False).st_mode
            if child.name == "__pycache__" and stat.S_ISDIR(mode):
                continue
            if kind == "STDLIB" and not relative and child.name in ("site-packages", "dist-packages"):
                continue
            if stat.S_ISLNK(mode):
                link = os.readlink(child.path)
                target = os.path.realpath(child.path)
                root_real = os.path.realpath(root)
                inside = target == root_real or target.startswith(root_real.rstrip("/") + "/")
                if inside:
                    records.append(["L", child_rel, link])
                elif kind == "STDLIB" and os.path.isfile(target):
                    records.append(["LT", child_rel, link, file_sha256(target)])
                else:
                    raise Rejected(BASE_INTERPRETER_MISMATCH, "TREE_LINK_OUTSIDE", child_rel)
            elif stat.S_ISDIR(mode):
                pending.append(child_rel)
            elif stat.S_ISREG(mode):
                records.append(["F", child_rel, 1 if mode & stat.S_IXUSR else 0, file_sha256(child.path)])
            else:
                raise Rejected(BASE_INTERPRETER_MISMATCH, "TREE_ENTRY_TYPE", child_rel)
    records.sort(key=lambda record: record[1].encode("utf-8", "surrogatepass"))
    return records


def tree_digest(root: str, kind: str) -> str:
    return canonical_digest(tree_records(root, kind))


def external_names_supported(records: list) -> bool:
    """TREE_DIGEST_EXTERNAL_V1 name restriction (printable ASCII, no quote, no backslash)."""
    for record in records:
        strings = [record[1]] + ([record[2]] if record[0] in ("L", "LT") else [])
        for text in strings:
            if not _PRINTABLE_NAME.match(text) or '"' in text or "\\" in text:
                return False
    return True


# =============================================================================
# NATIVE_CLOSURE_V1 (model over an injected filesystem view)
# =============================================================================

NATIVE_MAX_FILES = 512
NATIVE_MAX_DEPTH = 16
_FORBIDDEN_TOKENS = ("$LIB", "${LIB}", "$PLATFORM", "${PLATFORM}", "$HWCAP")
LOADER_INPUT_FIXED = ("/etc/ld.so.cache", "/etc/ld.so.conf")
LD_SO_CONF_DIR = "/etc/ld.so.conf.d"
LD_SO_PRELOAD = "/etc/ld.so.preload"


def _native(reason, detail=None, **evidence):
    raise Rejected(BASE_INTERPRETER_MISMATCH, reason, detail, **evidence)


def parse_loader_help(text: str) -> list:
    """SYSTEM_DIRS_V1 from `<loader> --help`."""
    lines = text.split("\n")
    try:
        start = lines.index("Shared library search path:")
    except ValueError:
        _native("NATIVE_UNRESOLVED", "LOADER_DIRS")
    block = []
    for line in lines[start + 1:]:
        if line.strip() == "":
            break
        block.append(line.strip())
    if not block or block[0] != "(libraries located via /etc/ld.so.cache)":
        _native("NATIVE_UNRESOLVED", "LOADER_DIRS")
    directories = []
    for line in block[1:]:
        match = re.fullmatch(r"(/\S*) \(system search path\)", line)
        if not match:
            _native("NATIVE_UNRESOLVED", "LOADER_DIRS")
        directories.append(match.group(1))
    if not directories:
        _native("NATIVE_UNRESOLVED", "LOADER_DIRS")
    return directories


def parse_ldconfig_cache(text: str) -> list:
    """`ldconfig -p` -> [(soname, flags, path)]."""
    entries = []
    for line in text.split("\n")[1:]:
        match = re.fullmatch(r"\s+(\S+) \(([^)]*)\) => (\S+)", line)
        if match:
            entries.append(match.groups())
    return entries


def cache_flags_match(flags: str, elf_class: str, machine: str) -> bool:
    parts = [item.strip() for item in flags.split(",")]
    if not parts or parts[0] != "libc6":
        return False
    has_x8664 = "x86-64" in parts
    if elf_class == "ELF64" and machine == "Advanced Micro Devices X86-64":
        return has_x8664
    if elf_class == "ELF32" and machine == "Intel 80386":
        return not has_x8664 and "x32" not in parts
    return False


def parse_readelf(dynamic_text: str, header_text: str, program_text: str) -> dict:
    """The fields of one ELF file from `readelf -d`, `readelf -h` and `readelf -l`."""
    info = {"class": None, "machine": None, "needed": [], "rpath": None, "runpath": None, "interp": None}
    for line in header_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Class:"):
            info["class"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Machine:"):
            info["machine"] = stripped.split(":", 1)[1].strip()
    for line in dynamic_text.split("\n"):
        match = re.search(r"\((NEEDED|RPATH|RUNPATH)\)\s+[^\[]*\[(.*)\]\s*\Z", line)
        if not match:
            continue
        tag, value = match.groups()
        if tag == "NEEDED":
            info["needed"].append(value)
        elif tag == "RPATH":
            if info["rpath"] is not None:
                _native("NATIVE_UNRESOLVED", "DUPLICATE_RPATH")
            info["rpath"] = value.split(":")
        else:
            if info["runpath"] is not None:
                _native("NATIVE_UNRESOLVED", "DUPLICATE_RUNPATH")
            info["runpath"] = value.split(":")
    for line in program_text.split("\n"):
        match = re.search(r"\[Requesting program interpreter: (\S+)\]", line)
        if match:
            info["interp"] = match.group(1)
    return info


def _expand_origin(entries, loaded_path: str) -> list:
    base = loaded_path.rsplit("/", 1)[0] or "/"
    return [item.replace("${ORIGIN}", base).replace("$ORIGIN", base) for item in entries]


def compute_native_closure(roots: list, fs) -> dict:
    """NATIVE_CLOSURE_V1 for ROOTS (absolute loaded paths of root ELF files;
    the first root is the interpreter) over FS, which provides lexists,
    islink, readlink, realpath, isfile, sha256, elf(path) (parse_readelf
    dict), ldconfig() (parse_ldconfig_cache list), loader_help() text,
    listdir(path) and has_symlink_component(path)."""
    if fs.lexists(LD_SO_PRELOAD):
        _native("LOADER_PRELOAD")
    interpreter_info = fs.elf(roots[0])
    loader_path = interpreter_info["interp"]
    if loader_path is None or not loader_path.startswith("/"):
        _native("NATIVE_UNRESOLVED", "PT_INTERP")
    system_dirs = parse_loader_help(fs.loader_help())
    cache = fs.ldconfig()
    files, links, absent = {}, set(), set()

    def record_chain(path):
        current = path
        hops = 0
        while fs.islink(current):
            target = fs.readlink(current)
            links.add((current, target))
            current = target if target.startswith("/") else os.path.normpath(
                (current.rsplit("/", 1)[0] or "/") + "/" + target).replace("\\", "/")
            hops += 1
            if hops > 40:
                _native("NATIVE_UNRESOLVED", "LINK_LOOP")
        return fs.realpath(path)

    loader_real = record_chain(loader_path)
    files[loader_real] = fs.sha256(loader_real)
    loader = [loader_real, files[loader_real]]

    queue = []
    for root in sorted(set(roots)):
        queue.append((root, (), 0))
    visited = {}
    edges = {}
    while queue:
        queue.sort(key=lambda item: (item[2], fs.realpath(item[0])))
        loaded, chain, depth = queue.pop(0)
        real = fs.realpath(loaded)
        if real in visited:
            continue
        if depth > NATIVE_MAX_DEPTH:
            _native("NATIVE_CLOSURE_LIMIT", "DEPTH")
        info = fs.elf(real)
        visited[real] = info
        files[real] = fs.sha256(real)
        if len(files) > NATIVE_MAX_FILES:
            _native("NATIVE_CLOSURE_LIMIT", "FILES")
        for item in (info["rpath"] or []) + (info["runpath"] or []) + info["needed"]:
            if any(token in item for token in _FORBIDDEN_TOKENS):
                _native("NATIVE_UNRESOLVED", "FORBIDDEN_TOKEN", object=real)
        carries_origin = any("$ORIGIN" in item or "${ORIGIN}" in item
                             for item in (info["rpath"] or []) + (info["runpath"] or []))
        if carries_origin and (loaded != real or fs.has_symlink_component(loaded)):
            _native("NATIVE_UNRESOLVED", "ORIGIN_VIA_SYMLINK", object=loaded)
        node = (loaded, info)
        for soname in info["needed"]:
            if "/" in soname:
                _native("NATIVE_UNRESOLVED", "SONAME_SLASH", soname=soname)
            candidates = []
            if info["runpath"] is None:
                for carrier_loaded, carrier in (node,) + chain:
                    if carrier["runpath"] is None and carrier["rpath"]:
                        candidates += [d.rstrip("/") + "/" + soname
                                       for d in _expand_origin(carrier["rpath"], carrier_loaded)]
            else:
                for carrier_loaded, carrier in chain:
                    if carrier["runpath"] is None and carrier["rpath"]:
                        candidates += [d.rstrip("/") + "/" + soname
                                       for d in _expand_origin(carrier["rpath"], carrier_loaded)]
            if info["runpath"]:
                candidates += [d.rstrip("/") + "/" + soname for d in _expand_origin(info["runpath"], loaded)]
            matching = [entry for entry in cache
                        if entry[0] == soname and cache_flags_match(entry[1], info["class"], info["machine"])]
            if len(matching) > 1:
                _native("NATIVE_UNRESOLVED", "CACHE_AMBIGUOUS", soname=soname)
            if matching:
                if "/glibc-hwcaps/" in matching[0][2]:
                    _native("NATIVE_UNRESOLVED", "GLIBC_HWCAPS", soname=soname)
                candidates.append(matching[0][2])
            candidates += [d.rstrip("/") + "/" + soname for d in system_dirs]
            winner = None
            preceding = []
            for candidate in candidates:
                if fs.lexists(candidate):
                    winner = candidate
                    break
                preceding.append(candidate)
            if winner is None or not fs.isfile(fs.realpath(winner)):
                _native("NATIVE_UNRESOLVED", "SONAME", soname=soname, requester=real)
            absent.update(preceding)
            edges.setdefault(real, set()).add(record_chain(winner))
            queue.append((winner, (node,) + chain, depth + 1))
    interpreter_closure, pending = set(), [fs.realpath(roots[0])]
    while pending:
        current = pending.pop()
        if current in interpreter_closure:
            continue
        interpreter_closure.add(current)
        pending.extend(edges.get(current, ()))
    for real in sorted(interpreter_closure):
        if visited[real]["rpath"]:
            _native("NATIVE_UNRESOLVED", "MAIN_PROGRAM_RPATH", object=real)
    loader_inputs = []
    for path in list(LOADER_INPUT_FIXED) + [LD_SO_CONF_DIR + "/" + name for name in fs.listdir(LD_SO_CONF_DIR)]:
        if fs.lexists(path) and fs.isfile(path):
            loader_inputs.append([path, fs.sha256(path)])
    absent.add(LD_SO_PRELOAD)
    closure = {
        "files": sorted(([path, digest] for path, digest in files.items()), key=lambda item: item[0].encode()),
        "links": sorted([list(item) for item in links], key=lambda item: (item[0].encode(), item[1].encode())),
        "absent": sorted(absent, key=lambda item: item.encode()),
        "loader_inputs": sorted(loader_inputs, key=lambda item: item[0].encode()),
        "loader": loader,
        "system_dirs": system_dirs,
    }
    return closure


def native_closure_digest(closure: dict) -> str:
    return canonical_digest({"spec": "NATIVE_CLOSURE_V1", "closure": closure})


# =============================================================================
# POST_APT_LD_SO_CACHE_V1 (the only native-closure difference admitted after the apt phase)
# =============================================================================

POST_APT_LD_SO_CACHE_SPEC = "POST_APT_LD_SO_CACHE_V1"
LD_SO_CACHE_PATH = "/etc/ld.so.cache"
POST_APT_RECHECK_LABELS = ("STEP4", "STEP6")
CLOSURE_MEMBER_CLASSES = ("files", "links", "loader_inputs", "absent")


def closure_member_counts(closure: dict) -> dict:
    return {name: len(closure[name]) for name in CLOSURE_MEMBER_CLASSES}


def libc_bin_trigger_record(dpkg_state: list, apt_install_output: str):
    """Condition (12): the record `Processing triggers for libc-bin (<installed version>) ...` in the captured output
    of the approved apt-get install, for the single installed libc-bin version of the post-apt dpkg state
    ([package, architecture, version, status] rows); None when it cannot be established."""
    installed = [row[2] for row in dpkg_state if row[0] == "libc-bin" and row[3] == "install ok installed"]
    if len(installed) != 1:
        return None
    want = "Processing triggers for libc-bin (%s) ..." % installed[0]
    found = [line for line in (apt_install_output or "").split("\n") if line == want]
    return found[-1] if found else None


def _closure_difference(pre: dict, post: dict) -> list:
    """Every difference between two NATIVE_CLOSURE_V1 objects other than the SHA-256 of /etc/ld.so.cache, as
    (member_class, detail) pairs; an empty list means the objects are identical in every non-cache member."""
    differences = []
    if sorted(pre) != sorted(post):
        differences.append(("FIELDS", "closure field set"))
    for name in ("files", "links", "absent", "system_dirs", "loader"):
        if pre.get(name) != post.get(name):
            differences.append((name.upper(), name))
    pre_inputs = {path: digest for path, digest in pre.get("loader_inputs", [])}
    post_inputs = {path: digest for path, digest in post.get("loader_inputs", [])}
    if sorted(pre_inputs) != sorted(post_inputs):
        differences.append(("LOADER_INPUT", "path set"))
    for path in sorted(set(pre_inputs) & set(post_inputs)):
        if path != LD_SO_CACHE_PATH and pre_inputs[path] != post_inputs[path]:
            differences.append(("LOADER_INPUT", path))
    return differences


def post_apt_ld_so_cache_admission(label: str, pre_closure: dict, post_closure: dict, *, identity: dict,
                                   approved_identity_digest: str, apt_delta: list, identity_critical: set,
                                   apt_plan_checks_passed: bool, libc_bin_trigger,
                                   accepted_cache_sha256=None) -> dict:
    """POST_APT_LD_SO_CACHE_V1. Admits a native-closure difference after the apt phase ONLY when the complete
    difference between POST_CLOSURE and the PRE_APT PRE_CLOSURE is the SHA-256 of /etc/ld.so.cache and every
    condition holds; returns the POST_APT_LD_SO_CACHE_RECORD. IDENTITY is the live identity member dict (every
    IDENTITY_DIGEST_V1 member except native_closure_digest). Anything else is BASE_INTERPRETER_MISMATCH reason
    NATIVE_CLOSURE (no origin, package or generated-file exception exists)."""
    def refuse(detail, **evidence):
        raise Rejected(BASE_INTERPRETER_MISMATCH, "NATIVE_CLOSURE", "%s:%s" % (label, detail), **evidence)

    if label not in POST_APT_RECHECK_LABELS:
        refuse("LABEL")
    for entry in apt_delta:
        if entry["package"] in identity_critical:
            raise Rejected(ENV_UNVERIFIED, APT_UNEXPECTED_CHANGE, "IDENTITY_CRITICAL", package=entry["package"])
    if apt_plan_checks_passed is not True:
        refuse("APT_TRANSACTION")
    if not libc_bin_trigger:
        refuse("LIBC_BIN_TRIGGER")
    pre_cache = dict((path, digest) for path, digest in pre_closure["loader_inputs"]).get(LD_SO_CACHE_PATH)
    post_cache = dict((path, digest) for path, digest in post_closure["loader_inputs"]).get(LD_SO_CACHE_PATH)
    if pre_cache is None or post_cache is None:
        refuse("CACHE_MEMBER")
    if pre_cache == post_cache:
        refuse("NO_CACHE_DIFFERENCE")
    other = _closure_difference(pre_closure, post_closure)
    if other:
        refuse(other[0][0], differences=other)
    if label == "STEP6" and post_cache != accepted_cache_sha256:
        refuse("CACHE_CHANGED_AFTER_STEP4")
    pre_digest = native_closure_digest(pre_closure)
    post_digest = native_closure_digest(post_closure)
    compared = identity_digest(native_closure_digest=pre_digest, **identity)
    if compared != approved_identity_digest:
        raise Rejected(BASE_INTERPRETER_MISMATCH, "IDENTITY_DIGEST", label)
    return {
        "spec": POST_APT_LD_SO_CACHE_SPEC,
        "label": label,
        "pre_apt_native_closure_digest": pre_digest,
        "post_apt_native_closure_digest": post_digest,
        "approved_identity_digest_compared_with_pre_apt_native_closure_digest": compared,
        "post_apt_live_identity_digest": identity_digest(native_closure_digest=post_digest, **identity),
        "old_ld_so_cache_sha256": pre_cache,
        "new_ld_so_cache_sha256": post_cache,
        "pre_apt_members": closure_member_counts(pre_closure),
        "post_apt_members": closure_member_counts(post_closure),
        "other_members_differing": 0,
        "libc_bin_trigger": libc_bin_trigger,
    }


POST_APT_RECORD_KEYS = (
    "label", "spec", "pre_apt_native_closure_digest", "post_apt_native_closure_digest", "post_apt_live_identity_digest",
    "approved_identity_digest_compared_with_pre_apt_native_closure_digest", "old_ld_so_cache_sha256",
    "new_ld_so_cache_sha256", "pre_apt_members", "post_apt_members", "other_members_differing",
    "apt_transaction_plan_digest", "libc_bin_trigger",
)


def parse_post_apt_ld_so_cache_records(by_key: dict, manifest_native_closure_digest: str, approved_plan_digest: str):
    """The POST_APT_LD_SO_CACHE_RECORD lines of a provisioning evidence (one record per admitted recheck, STEP4 and
    STEP6), checked against the plan: the PRE_APT closure digest is the manifest value, the cache old/new hashes are
    distinct SHA-256 values, no other member differs, the plan digest is the approved one and STEP6 repeats STEP4
    exactly. Returns [] when the evidence has no record (no admitted case); fails closed on any inconsistency."""
    lines = by_key.get("post_apt_ld_so_cache_record") or []
    if not lines:
        return []

    def refuse(detail):
        raise Rejected(ENV_UNVERIFIED, "POST_APT_LD_SO_CACHE_RECORD", detail)

    records, current = [], None
    for line in lines:
        if line.startswith("label="):
            current = {}
            records.append(current)
        if current is None:
            refuse("ORDER")
        if line.startswith("apt_transaction_plan_digest="):
            head = line.split(" ", 1)
            current["apt_transaction_plan_digest"] = head[0].partition("=")[2]
            current["apt_install_argv_sha256"] = head[1].partition("=")[2] if len(head) == 2 else ""
            continue
        if line.startswith("label="):
            parts = dict(item.partition("=")[::2] for item in line.split(" "))
            current["label"], current["spec"] = parts.get("label"), parts.get("spec")
            continue
        key, _, value = line.partition("=")
        if key in current:
            refuse("DUPLICATE:" + key)
        current[key] = value
    if [record.get("label") for record in records] not in (["STEP4"], ["STEP4", "STEP6"]):
        refuse("LABELS")
    for record in records:
        missing = [key for key in POST_APT_RECORD_KEYS + ("apt_install_argv_sha256",) if key not in record]
        if missing:
            refuse("MISSING:" + ",".join(missing))
        if record["spec"] != POST_APT_LD_SO_CACHE_SPEC or record["other_members_differing"] != "0":
            refuse("SPEC")
        for key in ("pre_apt_native_closure_digest", "post_apt_native_closure_digest", "post_apt_live_identity_digest",
                    "old_ld_so_cache_sha256", "new_ld_so_cache_sha256", "apt_install_argv_sha256"):
            if re.fullmatch(r"[0-9a-f]{64}", record[key]) is None:
                refuse("DIGEST:" + key)
        if (record["pre_apt_native_closure_digest"] != manifest_native_closure_digest
                or record["old_ld_so_cache_sha256"] == record["new_ld_so_cache_sha256"]
                or record["pre_apt_native_closure_digest"] == record["post_apt_native_closure_digest"]
                or record["apt_transaction_plan_digest"] != approved_plan_digest
                or not record["libc_bin_trigger"].startswith("Processing triggers for libc-bin (")):
            refuse("CONSISTENCY:" + record["label"])
    if len(records) == 2 and {k: v for k, v in records[0].items() if k != "label"} != {
            k: v for k, v in records[1].items() if k != "label"}:
        refuse("STEP6_DIFFERS_FROM_STEP4")
    return records


class RealFilesystem:
    """The host view for NATIVE_CLOSURE_V1 and the startup-path checks
    (verifier capture and operator modes only; readelf and ldconfig are
    run as child processes, which the verifier is permitted to do)."""

    def __init__(self, loader_help_text=None, ldconfig_text=None, runner=None):
        import subprocess

        self._subprocess = subprocess
        self._loader_help = loader_help_text
        self._ldconfig = ldconfig_text
        self._elf_cache = {}

    def _run(self, argv):
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"}
        return self._subprocess.run(argv, capture_output=True, text=True, env=env, check=True).stdout

    def lexists(self, path):
        return os.path.lexists(path)

    def islink(self, path):
        return os.path.islink(path)

    def readlink(self, path):
        return os.readlink(path)

    def realpath(self, path):
        return os.path.realpath(path)

    def isfile(self, path):
        return os.path.isfile(path)

    def isdir(self, path):
        return os.path.isdir(path)

    def sha256(self, path):
        return file_sha256(path)

    def listdir(self, path):
        try:
            return sorted(os.listdir(path))
        except FileNotFoundError:
            return []

    def has_symlink_component(self, path):
        current = "/"
        for part in path.strip("/").split("/")[:-1]:
            current = os.path.join(current, part)
            if os.path.islink(current):
                return True
        return False

    def elf(self, path):
        if path not in self._elf_cache:
            self._elf_cache[path] = parse_readelf(self._run(["/usr/bin/readelf", "-d", path]),
                                                  self._run(["/usr/bin/readelf", "-h", path]),
                                                  self._run(["/usr/bin/readelf", "-l", path]))
        return self._elf_cache[path]

    def ldconfig(self):
        if self._ldconfig is None:
            self._ldconfig = self._run(["/sbin/ldconfig", "-p"])
        return parse_ldconfig_cache(self._ldconfig)

    def loader_help(self):
        if self._loader_help is None:
            raise Rejected(BASE_INTERPRETER_MISMATCH, "NATIVE_UNRESOLVED", "LOADER_DIRS")
        return self._loader_help


def is_elf_file(path: str) -> bool:
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return False
        with open(path, "rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


def elf_files_under(root: str, exclude_pycache: bool = True, stdlib: bool = False) -> list:
    found = []
    for directory, dirnames, filenames in os.walk(root):
        relative = os.path.relpath(directory, root)
        if stdlib and relative == ".":
            dirnames[:] = [name for name in dirnames if name not in ("site-packages", "dist-packages")]
        if exclude_pycache:
            dirnames[:] = [name for name in dirnames if name != "__pycache__"]
        for name in filenames:
            path = os.path.join(directory, name)
            if is_elf_file(path):
                found.append(path)
    return sorted(found)


# =============================================================================
# SYS_PATH_VALIDATION_V1 rule (1) and STARTUP_PATH_INPUTS_V1 (rule 6)
# =============================================================================

def _within(path: str, root: str) -> bool:
    root = root.rstrip("/")
    return path == root or path.startswith(root + "/")


def check_sys_path_rule1(entries: list, stdlib_root: str, fs, prefix_lib=None) -> None:
    """Rule (1) with non-interpreter facts: every entry that is not an
    existing directory inside the STDLIB_TREE root must not exist, and no
    python*.zip exists beside the stdlib directory (or in PREFIX_LIB)."""
    root_real = fs.realpath(stdlib_root)
    for entry in entries:
        if fs.lexists(entry):
            if not fs.isdir(entry) or not _within(fs.realpath(entry), root_real):
                _native("SYS_PATH_UNBOUND", None, entry=entry)
    parents = [stdlib_root.rstrip("/").rsplit("/", 1)[0] or "/"]
    if prefix_lib is not None:
        parents.append(prefix_lib)
    for parent in parents:
        for name in fs.listdir(parent):
            if name.startswith("python") and name.endswith(".zip"):
                _native("SYS_PATH_UNBOUND", None, entry=parent.rstrip("/") + "/" + name)


def startup_path_candidates(launch_path: str, real_path: str, fs) -> list:
    """STARTUP_PATH_INPUTS_V1 candidate set for one launch form."""
    candidates = []
    for directory in dict.fromkeys([launch_path.rsplit("/", 1)[0] or "/", real_path.rsplit("/", 1)[0] or "/"]):
        parent = directory.rsplit("/", 1)[0] or "/"
        candidates += [directory.rstrip("/") + "/pyvenv.cfg", parent.rstrip("/") + "/pyvenv.cfg",
                       directory.rstrip("/") + "/pybuilddir.txt"]
        candidates += [directory.rstrip("/") + "/" + name for name in fs.listdir(directory) if name.endswith("._pth")]
    ancestor = real_path.rsplit("/", 1)[0] or "/"
    while True:
        candidates.append(ancestor.rstrip("/") + "/Modules/Setup.local")
        if ancestor == "/":
            break
        ancestor = ancestor.rsplit("/", 1)[0] or "/"
    return list(dict.fromkeys(candidates))


def check_startup_path_inputs(launch_path: str, real_path: str, fs, permitted=None) -> list:
    """Rule (6): returns the ABSENT candidates; an existing candidate other
    than PERMITTED (<prefix>/pyvenv.cfg for the prefix form) is
    SYS_PATH_UNBOUND detail STARTUP_PATH_INPUT. No interpreter runs."""
    absent = []
    for candidate in startup_path_candidates(launch_path, real_path, fs):
        if fs.lexists(candidate):
            if candidate != permitted:
                _native("SYS_PATH_UNBOUND", "STARTUP_PATH_INPUT", candidate=candidate)
        else:
            absent.append(candidate)
    return absent


# =============================================================================
# FILESET_RECONCILIATION_V1 and RECORD row classes
# =============================================================================

STARTUP_HOOK_NAMES = ("sitecustomize.py", "usercustomize.py")


def record_row_class(row_path: str, site_packages: str, prefix: str) -> str:
    """IN_SITE (resolves under site-packages), OUT_SCRIPT (resolves under
    <prefix>/bin) or OTHER, for one RECORD path relative to site-packages."""
    resolved = os.path.normpath(os.path.join(site_packages, row_path)).replace("\\", "/")
    if _within(resolved, site_packages.rstrip("/")):
        return "IN_SITE"
    if _within(resolved, prefix.rstrip("/") + "/bin"):
        return "OUT_SCRIPT"
    return "OTHER"


def reconcile_fileset(site_files: list, records: dict, site_packages: str, prefix: str) -> None:
    """Every file of site-packages is listed by exactly one approved RECORD;
    no startup hook, .pth, bytecode or unlisted importable entry exists;
    every RECORD row is IN_SITE or OUT_SCRIPT. SITE_FILES are relative
    paths; RECORDS maps distribution name to its row paths."""
    owner = {}
    for name, rows in sorted(records.items()):
        for row in rows:
            row_class = record_row_class(row, site_packages, prefix)
            if row_class == "OTHER":
                raise Rejected(ENV_UNVERIFIED, "UNBOUND_CODE", "RECORD_ROW_OUTSIDE", distribution=name, row=row)
            if row.endswith(".pyc") or "__pycache__/" in row:
                raise Rejected(ENV_UNVERIFIED, "UNBOUND_CODE", "BYTECODE_ROW", distribution=name, row=row)
            if row_class == "IN_SITE":
                if row in owner:
                    raise Rejected(ENV_UNVERIFIED, "UNBOUND_CODE", "SHARED_ROW", row=row)
                owner[row] = name
    for relative in sorted(site_files):
        base = relative.rsplit("/", 1)[-1]
        if base in STARTUP_HOOK_NAMES or (relative.count("/") == 0 and base.endswith(".pth")):
            raise Rejected(ENV_UNVERIFIED, "STARTUP_HOOK", None, path=relative)
        if base.endswith(".pyc") or "/__pycache__/" in "/" + relative:
            raise Rejected(ENV_UNVERIFIED, "UNBOUND_CODE", "BYTECODE", path=relative)
        if relative not in owner:
            raise Rejected(ENV_UNVERIFIED, "UNBOUND_CODE", "UNLISTED", path=relative)
    missing = sorted(set(owner) - set(site_files))
    if missing:
        raise Rejected(ENV_UNVERIFIED, "UNBOUND_CODE", "RECORD_FILE_MISSING", path=missing[0])


# =============================================================================
# PROCESS_CREATION_DENY_V1 (hook source shared with the proof)
# =============================================================================

DENIED_EVENT_SET = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork",
                    "os.forkpty", "pty.spawn", "_posixsubprocess.fork_exec")
PROCESS_CREATION_PROOF_VECTORS = (
    "subprocess.run", "subprocess.Popen", "os.popen", "os.system", "os.posix_spawn", "os.posix_spawnp",
    "os.spawnv", "os.spawnlp", "os.execv", "os.fork", "os.forkpty", "pty.spawn",
    "multiprocessing.util.spawnv_passfds", "_posixsubprocess.fork_exec", "swallowed os.fork",
)


def extract_embedded(script_text: str, name: str) -> str:
    """The embedded Python block NAME of the provisioning script (between
    `: <<'NAME'` style markers written as #BEGIN NAME / #END NAME lines)."""
    begin, end = "#BEGIN " + name + "\n", "#END " + name + "\n"
    text = script_text.replace("\r\n", "\n")
    start = text.index(begin) + len(begin)
    return text[start:text.index(end, start)]


class _ForkExecCaptured(Exception):
    pass


def capture_fork_exec_args(marker: str) -> tuple:
    """The exact positional arguments this interpreter's subprocess module
    passes to _posixsubprocess.fork_exec, captured without creating a
    process (the call is intercepted before the fork)."""
    import subprocess

    captured = {}
    original = subprocess._fork_exec

    def intercept(*args):
        captured["args"] = args
        raise _ForkExecCaptured()

    subprocess._fork_exec = intercept
    try:
        subprocess.Popen(["/bin/sh", "-c", "echo x > %s" % marker], close_fds=True, cwd="/")
    except _ForkExecCaptured:
        pass
    finally:
        subprocess._fork_exec = original
    return captured["args"]


def vector_code(vector: str, marker: str, fork_exec_args=None) -> str:
    """Code whose only effect, if a process is created, is MARKER."""
    command = "['/bin/sh','-c','echo x > %s']" % marker
    shell = "'echo x > %s'" % marker
    return {
        "subprocess.run": "import subprocess\nsubprocess.run(%s)" % command,
        "subprocess.Popen": "import subprocess\nsubprocess.Popen(%s).wait()" % command,
        "os.popen": "import os\nos.popen(%s).read()" % shell,
        "os.system": "import os\nos.system(%s)" % shell,
        "os.posix_spawn": "import os\nos.waitpid(os.posix_spawn('/bin/sh',%s,{}),0)" % command,
        "os.posix_spawnp": "import os\nos.waitpid(os.posix_spawnp('sh',%s,dict(PATH='/bin:/usr/bin')),0)" % command,
        "os.spawnv": "import os\nos.spawnv(os.P_WAIT,'/bin/sh',%s)" % command,
        "os.spawnlp": "import os\nos.spawnlp(os.P_WAIT,'sh','sh','-c',%s)" % shell,
        "os.execv": "import os\nos.execv('/bin/sh',%s)" % command,
        "os.fork": "import os\npid=os.fork()\nif pid==0:\n    open(%r,'w').close()\n    os._exit(0)\nos.waitpid(pid,0)" % marker,
        "os.forkpty": "import os\npid,fd=os.forkpty()\nif pid==0:\n    open(%r,'w').close()\n    os._exit(0)\nos.waitpid(pid,0)" % marker,
        "pty.spawn": "import pty\npty.spawn(%s)" % command,
        "multiprocessing.util.spawnv_passfds": (
            "import multiprocessing.util as u\nimport os\n"
            "os.waitpid(u.spawnv_passfds(b'/bin/sh',[b'/bin/sh',b'-c',b'echo x > %s'],()),0)" % marker
        ),
        "_posixsubprocess.fork_exec": (
            "import _posixsubprocess, os\n"
            "args=list(%r)\n"
            "args[12],args[13]=os.pipe()\n"
            "args[3]=(args[13],)\n"
            "pid=_posixsubprocess.fork_exec(*args)\n"
            "os.waitpid(pid,0)" % (tuple(fork_exec_args) if fork_exec_args is not None else (),)
        ),
        "swallowed os.fork": (
            "import os\ntry:\n    pid=os.fork()\n    if pid==0:\n        open(%r,'w').close()\n        os._exit(0)\n"
            "    os.waitpid(pid,0)\nexcept BaseException:\n    pass" % marker
        ),
    }[vector]


# =============================================================================
# LOADED-OBJECT COMPARISON (/proc/self/maps)
# =============================================================================

def mapped_objects(maps_text: str) -> set:
    """Realpaths of file-backed mappings in a /proc/<pid>/maps text."""
    paths = set()
    for line in maps_text.split("\n"):
        fields = line.split(None, 5)
        if len(fields) == 6 and fields[5].startswith("/"):
            path = fields[5]
            if path.endswith(" (deleted)"):
                path = path[: -len(" (deleted)")]
            paths.add(path)
    return paths


def check_loaded_objects(maps_text: str, bound_files: set, allowed_extra=()) -> None:
    """Every mapped shared object must be a content-bound FILE member."""
    for path in sorted(mapped_objects(maps_text)):
        if path in bound_files or path in allowed_extra:
            continue
        if ".so" in path.rsplit("/", 1)[-1] or path.endswith(".so"):
            raise Rejected(ENV_UNVERIFIED, "LOADED_OBJECT_UNBOUND", None, path=path)


# =============================================================================
# IN-SANDBOX PROBE (stdlib only; the one entry point that may use socket)
# =============================================================================

PROBE_SANDBOX_PATH = "/probe/verify_document_rendering_environment.py"
PROBE_CONNECT_TARGETS = {"AF_INET": ("192.0.2.1", 443), "AF_INET6": ("2001:db8::1", 443)}


def run_probe(spec: dict) -> dict:
    """Inside the sandbox: interface set, routes, literal-IP connects, the
    loopback control, canary absence, write denial and empty HOME/TMPDIR.
    Returns the structured result; ok is true only when every proof holds."""
    import errno
    import socket

    result = {"spec": "SANDBOX_PROBE_V1", "failures": []}

    def failure(name, **detail):
        result["failures"].append(dict(detail, check=name))

    try:
        with open("/proc/net/dev", encoding="ascii") as handle:
            names = sorted(line.split(":", 1)[0].strip() for line in handle.read().splitlines()[2:] if ":" in line)
    except OSError as exc:
        names = None
        failure("INTERFACES", errno=exc.errno)
    result["interfaces"] = names
    if names is not None and not set(names) <= {"lo"}:
        failure("INTERFACES", names=names)
    try:
        with open("/proc/net/route", encoding="ascii") as handle:
            routes = [line.split() for line in handle.read().splitlines()[1:] if line.strip()]
    except OSError:
        routes = []
    if any(route[0] != "lo" or route[1] == "00000000" for route in routes):
        failure("ROUTES", count=len(routes))
    for family_name, target in PROBE_CONNECT_TARGETS.items():
        family = getattr(socket, family_name)
        allowed = set(spec["expected_errnos"][family_name])
        observed = None
        try:
            sock = socket.socket(family, socket.SOCK_STREAM)
        except OSError as exc:
            observed = errno.errorcode.get(exc.errno, str(exc.errno))
        else:
            try:
                sock.settimeout(5)
                sock.connect(target)
                observed = "CONNECTED"
            except socket.timeout:
                observed = "ETIMEDOUT"
            except OSError as exc:
                observed = errno.errorcode.get(exc.errno, str(exc.errno))
            finally:
                sock.close()
        result.setdefault("connects", {})[family_name] = observed
        if observed not in allowed:
            failure("CONNECT", family=family_name, observed=observed)
    try:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.create_connection(listener.getsockname(), timeout=5)
        client.close()
        listener.close()
        result["control"] = "CONNECTED"
    except OSError as exc:
        result["control"] = errno.errorcode.get(exc.errno, str(exc.errno))
        failure("CONTROL")
    for path in spec["canaries"]:
        if os.path.lexists(path):
            failure("CANARY_VISIBLE", path=path)
    for path in (spec["home"], spec["tmpdir"]):
        try:
            if os.listdir(path):
                failure("NOT_EMPTY", path=path)
        except OSError as exc:
            failure("NOT_EMPTY", path=path, errno=exc.errno)
    for directory in ["/"] + list(spec["read_only_paths"]):
        target = os.path.join(directory if os.path.isdir(directory) else os.path.dirname(directory), ".probe_write")
        try:
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            if exc.errno not in (errno.EROFS, errno.EACCES):
                failure("WRITE_DENIAL", path=directory, errno=exc.errno)
        else:
            os.close(descriptor)
            failure("WRITE_DENIAL", path=directory, created=1)
    result["ok"] = not result["failures"]
    return result


def probe_argv_segments(profile_argv: list, verifier_host_path: str, interpreter: str, spec: dict) -> list:
    """The probe launch: the shared argv with the single permitted delta
    (the read-only bind of this file) inserted before the final
    --remount-ro /, then the probe command."""
    if profile_argv[-2:] != ["--remount-ro", "/"]:
        raise Rejected("RENDER_ISOLATION_UNAVAILABLE", "PROBE_ARGV", None)
    return (profile_argv[:-2] + ["--ro-bind", verifier_host_path, PROBE_SANDBOX_PATH] + profile_argv[-2:]
            + [interpreter, "-I", "-S", "-B", PROBE_SANDBOX_PATH, "--probe", json.dumps(spec, sort_keys=True)])


def make_isolation_prober(manifest: dict, verifier_host_path: str, inspection_paths=(), timeout=60):
    """The adapter's isolation_prober(profile, argv, pass_fds): runs the
    probe inside exactly the profile the adapter built and returns
    {"ok", "reason", "profile_digest", "result"}."""
    import subprocess

    adapter = load_adapter()

    def prober(profile, argv, pass_fds):
        shared = adapter.build_argv_shared(manifest, profile, tuple(inspection_paths))
        expected = adapter.substitute_placeholders(shared, entry_fd=pass_fds[0] if pass_fds else None)
        if list(argv[1:]) != expected:
            return {"ok": False, "reason": "PROFILE_MISMATCH"}
        spec = {"expected_errnos": manifest["sandbox_expected_unreachable_errnos"],
                "canaries": manifest["sandbox_forbidden_canary_paths"],
                "home": adapter.home_path(manifest), "tmpdir": adapter.SANDBOX_TMP_PATH,
                "read_only_paths": list(manifest["sandbox_read_only_paths"] if profile == adapter.PROFILE_RENDER
                                        else inspection_paths)}
        command = [argv[0]] + probe_argv_segments(list(argv[1:]), verifier_host_path,
                                                  manifest["sandbox_probe_interpreter_path"], spec)
        try:
            completed = subprocess.run(command, capture_output=True, timeout=timeout, pass_fds=tuple(pass_fds),
                                       env={}, close_fds=True)
        except (OSError, subprocess.TimeoutExpired):
            return {"ok": False, "reason": "PROBE_FAILED"}
        try:
            result = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return {"ok": False, "reason": "PROBE_OUTPUT"}
        if completed.returncode != 0 or result.get("ok") is not True:
            return {"ok": False, "reason": "SELF_TEST_FAILED", "result": result}
        return {"ok": True, "reason": None, "result": result,
                "profile_digest": adapter.sandbox_profile_digest(manifest, profile, tuple(inspection_paths))}

    return prober


# =============================================================================
# LIVE VERIFIER (adapter S2 live check) AND OPERATOR CHECKS
# =============================================================================

def site_packages_of(prefix: str, python_version: str) -> str:
    major_minor = ".".join(python_version.split(".")[:2])
    return prefix.rstrip("/") + "/lib/python%s/site-packages" % major_minor


def installed_distributions(site_packages: str) -> dict:
    """{normalized name: (version, RECORD row paths)} of SITE_PACKAGES,
    read from the .dist-info directories without importing anything."""
    result = {}
    for entry in sorted(os.listdir(site_packages)):
        if not entry.endswith(".dist-info"):
            continue
        metadata = parse_metadata(Path(site_packages, entry, "METADATA").read_text(encoding="utf-8"))
        rows = []
        for line in Path(site_packages, entry, "RECORD").read_text(encoding="utf-8").splitlines():
            if line:
                rows.append(line.rsplit(",", 2)[0])
        name = normalize_name(metadata["Name"])
        if name in result:
            raise Rejected(ENV_UNVERIFIED, "DEPENDENCY_SET", "DUPLICATE_DISTRIBUTION", name=name)
        result[name] = (metadata["Version"], rows)
    return result


def site_files(site_packages: str) -> list:
    files = []
    for directory, dirnames, filenames in os.walk(site_packages):
        for name in filenames + [item for item in dirnames if os.path.islink(os.path.join(directory, item))]:
            relative = os.path.relpath(os.path.join(directory, name), site_packages).replace(os.sep, "/")
            files.append(relative)
    return sorted(files)


def dpkg_installed_version(package: str, architecture: str):
    import subprocess

    completed = subprocess.run(["/usr/bin/dpkg-query", "-W", "-f", "${Version}\t${Status}",
                                "%s:%s" % (package, architecture)],
                               capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    if completed.returncode != 0:
        return None
    version, _, status = completed.stdout.partition("\t")
    return version if status == "install ok installed" else None


def make_live_verifier():
    """The adapter's live_verifier(manifest): installed-set equality,
    fileset reconciliation and the apt pins; None when everything matches,
    else the named reason."""

    def live(manifest):
        try:
            interpreter = manifest["operator_base_interpreter"]
            site = site_packages_of(manifest["operator_python_prefix"], interpreter["python_version"])
            distributions = installed_distributions(site)
            installed_set_equality([(name, item[0]) for name, item in distributions.items()], manifest)
            reconcile_fileset(site_files(site), {name: item[1] for name, item in distributions.items()}, site,
                              manifest["operator_python_prefix"])
            for item in manifest["apt_plan"]["packages"]:
                if dpkg_installed_version(item["name"], item["architecture"]) != item["version"]:
                    return "APT_PIN"
            if sys.flags.isolated != 1 or sys.flags.no_site != 1 or sys.flags.dont_write_bytecode != 1:
                return "INTERPRETER_MODE"
        except Rejected as exc:
            return exc.reason
        return None

    return live


# =============================================================================
# CANDIDATE AND PLAN DIGEST
# =============================================================================

GATE2_NULL_RULE = ("provisioning_script_sha256", "verifier_sha256", "installer_pip_version",
                   "installer_pip_package_path", "installer_pip_package_tree_digest")
CONTRACT_NULL_MEMBERS = re.compile(r"extraction_spec\.laparams\Z|"
                                   r"apt_plan\.approved_dpkg_config\.files\[\d+\]\.options\[\d+\]\[1\]\Z|"
                                   r"dependency_lock_review\[\d+\]\.license_declared\.(?:%s)\Z"
                                   % "|".join(re.escape(key) for key in LICENSE_KEYS))


def null_members(value, path="") -> list:
    found = []
    if value is None:
        return [path]
    if isinstance(value, dict):
        for key in sorted(value):
            found += null_members(value[key], path + "." + key if path else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += null_members(item, "%s[%d]" % (path, index))
    return found


def gate2_eligibility(manifest: dict) -> dict:
    """The MANIFEST_PARTITION_V1 gate (2) eligibility rule plus every other
    null PRE_PROVISION_PLAN member (a PLAN_DIGEST over a plan with null
    host values is not a reviewable plan)."""
    adapter = load_adapter()
    blocking = []
    for key in GATE2_NULL_RULE:
        if manifest.get(key) is None:
            blocking.append(key)
    blocking += null_members(manifest.get("operator_base_interpreter"), "operator_base_interpreter")
    for index, target in enumerate(manifest.get("artifact_targets") or []):
        blocking += null_members(target, "artifact_targets[%d]" % index)
    apt_plan = manifest.get("apt_plan") or {}
    blocking += null_members(apt_plan.get("sources"), "apt_plan.sources")
    blocking += null_members(apt_plan.get("approved_apt_config"), "apt_plan.approved_apt_config")
    other = []
    for key in adapter.MANIFEST_PRE_PROVISION_KEYS:
        for member in null_members(manifest.get(key), key):
            if member not in blocking and not CONTRACT_NULL_MEMBERS.match(member):
                other.append(member)
    return {"gate2_rule_null_members": blocking, "other_null_pre_members": other,
            "plan_complete": not blocking and not other}


def plan_report(root: Path) -> dict:
    adapter = load_adapter()
    manifest_bytes = (root / MANIFEST_RELPATH).read_bytes()
    manifest = strict_json_loads(manifest_bytes.decode("utf-8"))
    requirements_in = (root / REQUIREMENTS_IN_RELPATH).read_bytes()
    requirements_lock = (root / REQUIREMENTS_LOCK_RELPATH).read_bytes()
    script = (root / PROVISIONING_SCRIPT_RELPATH).read_bytes()
    verifier = (root / VERIFIER_RELPATH).read_bytes()
    report = {
        "requirements_in_sha256": sha256_hex(requirements_in),
        "requirements_lock_sha256": sha256_hex(requirements_lock),
        "provisioning_script_sha256": sha256_hex(script),
        "verifier_sha256": sha256_hex(verifier),
        "manifest_file_sha256": sha256_hex(manifest_bytes),
        "instrument_hashes_match_manifest": int(manifest.get("provisioning_script_sha256") == sha256_hex(script)
                                                and manifest.get("verifier_sha256") == sha256_hex(verifier)),
        "crlf_in_plan_files": [name for name, data in (("requirements.in", requirements_in),
                                                       ("requirements-lock.txt", requirements_lock),
                                                       ("provision script", script), ("verifier", verifier))
                               if b"\r" in data],
        "post_keys_null": int(all(manifest.get(key) is None for key in adapter.MANIFEST_POST_PROVISION_KEYS)),
        "lock_review_digest": lock_review_digest(manifest["dependency_lock_review"], manifest["artifact_targets"],
                                                 manifest["lock_artifacts"]),
        "pre_provision_plan_digest": adapter.pre_provision_plan_digest(manifest),
    }
    report.update(gate2_eligibility(manifest))
    try:
        report["lock_review"] = review_lock(manifest, requirements_lock)
    except Rejected as exc:
        report["lock_review"] = {"result": "REJECTED", "reason": exc.reason, "detail": exc.detail,
                                 "evidence": exc.evidence}
    digest = adapter.plan_digest(manifest, requirements_in, requirements_lock)
    if report["plan_complete"] and report["lock_review"].get("result") == "PASS" and report[
            "instrument_hashes_match_manifest"] and not report["crlf_in_plan_files"]:
        report["PRE_PROVISION_PLAN"] = "READY"
        report["PLAN_DIGEST"] = digest
    else:
        report["PRE_PROVISION_PLAN"] = "NOT_READY"
        report["PLAN_DIGEST"] = None
        report["incomplete_candidate_digest_not_approvable"] = digest
    interpreter = manifest.get("operator_base_interpreter") or {}
    identity_inputs = (interpreter.get("executable_sha256"), manifest.get("installer_pip_package_path"),
                       manifest.get("installer_pip_package_tree_digest"), interpreter.get("path"),
                       interpreter.get("path"), interpreter.get("native_closure_digest"),
                       interpreter.get("stdlib_path"), interpreter.get("stdlib_tree_digest"))
    report["identity_digest"] = identity_digest(*identity_inputs) if None not in identity_inputs else None
    return report


# =============================================================================
# WHEEL REVIEW (QUARANTINE / BUILDER_DEV)
# =============================================================================

def review_wheels(root: Path, wheel_dir: Path, candidate_listing=None) -> dict:
    manifest = strict_json_loads((root / MANIFEST_RELPATH).read_text(encoding="utf-8"))
    lock_bytes = (root / REQUIREMENTS_LOCK_RELPATH).read_bytes()
    by_sha = {}
    for path in sorted(wheel_dir.glob("*.whl")):
        by_sha[file_sha256(path)] = path
    requires, facts, wheels = {}, {}, []
    for entry in manifest["lock_artifacts"]:
        path = by_sha.get(entry["sha256"])
        if path is None or path.name != entry["filename"]:
            _lock_rejected("HASH_SET_MISMATCH", "WHEEL_NOT_PRESENT", filename=entry["filename"])
        if entry["name"] in facts:
            continue
        record = wheel_review_record(path)
        metadata = record["metadata"]
        if normalize_name(metadata["Name"]) != entry["name"] or metadata["Version"] != entry["version"]:
            _lock_rejected("ARTIFACT_SET_UNDETERMINED", "METADATA_IDENTITY", name=entry["name"])
        requires[entry["name"]] = metadata["Requires-Dist"]
        facts[entry["name"]] = {"license_declared": license_declared_from_metadata(metadata),
                                "native_binaries": record["native_binaries"]}
        wheels.append({"filename": path.name, "sha256": entry["sha256"]})
    for record in manifest["dependency_lock_review"]:
        observed = facts[record["name"]]
        for key in ("license_declared", "native_binaries"):
            if record[key] != observed[key]:
                _lock_rejected("CLOSURE_MISMATCH", "REVIEW_RECORD_" + key.upper(), name=record["name"],
                               observed=observed[key])
    review = review_lock(manifest, lock_bytes, requires=requires, candidate_wheels=candidate_listing)
    review["wheels"] = wheels
    review["domain"] = "QUARANTINE_OR_BUILDER_DEV_METADATA_ONLY"
    return review


# =============================================================================
# READ-ONLY PLAN CAPTURE (never run under the gate (1) pass)
# =============================================================================

def capture_plan(interpreter_path: str, stdlib_path: str, pip_path: str, operator_prefix: str) -> dict:
    """Read-only capture of the host-derived PRE_PROVISION_PLAN values. It
    reads files and runs read-only queries (readelf, ldconfig -p, the loader
    with --help, apt-config, the interpreter under -I -S in a disposable
    virtual environment created under a fresh temporary directory, which
    installs nothing); it changes no system state."""
    import subprocess
    import tempfile

    env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"}

    def run(argv):
        return subprocess.run(argv, capture_output=True, text=True, env=env, check=True).stdout

    real = os.path.realpath(interpreter_path)
    fs = RealFilesystem()
    loader = fs.elf(real)["interp"]
    fs._loader_help = run([loader, "--help"])
    roots = [real] + elf_files_under(stdlib_path, stdlib=True) + elf_files_under(pip_path)
    closure = compute_native_closure(roots, fs)
    probe = "import json,sys;print(json.dumps(sys.path))"
    sys_path = json.loads(run([interpreter_path, "-I", "-S", "-B", "-c", probe]))
    with tempfile.TemporaryDirectory(prefix="career-os-capture-") as scratch:
        venv_dir = os.path.join(scratch, "venv")
        run([interpreter_path, "-I", "-S", "-B", "-c",
             "import sys,venv;venv.EnvBuilder(system_site_packages=False,clear=False,symlinks=True,"
             "with_pip=False).create(sys.argv[1])", venv_dir])
        prefix_path = json.loads(run([os.path.join(venv_dir, "bin", "python"), "-I", "-S", "-B", "-c", probe]))
        prefix_path = [item.replace(venv_dir, operator_prefix.rstrip("/")) for item in prefix_path]
    dump = run(["/usr/bin/apt-config", "dump"])

    class HostDpkg:
        lexists = staticmethod(os.path.lexists)

        @staticmethod
        def listdir(path):
            return sorted(os.listdir(path)) if os.path.isdir(path) else []

        @staticmethod
        def lstat(path):
            try:
                return os.lstat(path)
            except FileNotFoundError:
                return None

        @staticmethod
        def read_bytes(path):
            try:
                return Path(path).read_bytes()
            except FileNotFoundError:
                return None

    dpkg_record = None
    dpkg_error = None
    try:
        dpkg_record = build_dpkg_record(HostDpkg, "/nonexistent", tempfile.gettempdir())
    except Rejected as exc:
        dpkg_error = {"reason": exc.reason, "evidence": exc.evidence}
    return {
        "operator_base_interpreter": {
            "path": interpreter_path,
            "executable_sha256": file_sha256(real),
            "stdlib_path": stdlib_path,
            "stdlib_tree_digest": tree_digest(stdlib_path, "STDLIB"),
            "native_closure_digest": native_closure_digest(closure),
            "sys_path_isolated": sys_path,
            "sys_path_isolated_prefix": prefix_path,
        },
        "installer_pip_package_path": pip_path,
        "installer_pip_package_tree_digest": tree_digest(pip_path, "PIP"),
        "native_closure": closure,
        "approved_apt_config": canonical_subset(parse_config_dump(dump)),
        "approved_dpkg_config": dpkg_record,
        "dpkg_config_error": dpkg_error,
    }


# =============================================================================
# E2_HELPER_CHAIN_V1 (capture, static derivation, live check) and PROCESS_CREATION_RECORD_V2
# =============================================================================
# The chain is the PRE_PROVISION_PLAN member operator_base_interpreter.e2_helper_chain. The provisioning script
# records and rechecks every member like a host tool but never executes it; the verifier never executes a
# helper either (capture derives the descendant set by static analysis of the hash-bound lsb_release script).

CLOSED_PATH = ("/usr/sbin", "/usr/bin", "/sbin", "/bin")
CHAIN_HELPER_ARGV = {"lsb_release": ["lsb_release", "-a"], "uname": ["uname", "-rs"]}
SHELL_KEYWORDS = frozenset(("if", "then", "else", "elif", "fi", "for", "in", "do", "done", "while", "until", "case",
                            "esac", "function", "!", "{", "}"))
SHELL_BUILTINS = frozenset((".", ":", "[", "[[", "alias", "bg", "break", "cd", "command", "continue", "echo", "eval",
                            "exec", "exit", "export", "false", "fg", "getopts", "hash", "jobs", "kill", "local",
                            "printf", "pwd", "read", "readonly", "return", "set", "shift", "test", "times", "trap",
                            "true", "type", "ulimit", "umask", "unalias", "unset", "wait"))
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_FUNCTION_DEFINITION = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*\([ \t]*\)", re.M)
_HEREDOC = re.compile(r"<<(-?)[ \t]*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z0-9_]+))")


def shell_simple_commands(text: str) -> list:
    """The command words (first word of every simple command) of a POSIX shell script, found
    path-insensitively by a small lexer: quotes, comments, here-documents, command substitutions,
    separators, case patterns and function definitions are handled; builtins and keywords are kept
    in the result and filtered by the caller."""
    functions = set(_FUNCTION_DEFINITION.findall(text))
    commands = []
    pending_heredocs = []
    length = len(text)

    def scan(index: int, closer):
        """Scan from INDEX until CLOSER ('' for end of text, ')' or a backtick); return the end index."""
        at_start = True
        in_pattern = False
        skip_to_do = False
        word = ""
        word_quoted = False

        def finish():
            nonlocal at_start, in_pattern, skip_to_do, word, word_quoted
            if word == "" and not word_quoted:
                return
            current, quoted = word, word_quoted
            word, word_quoted = "", False
            if in_pattern:
                return
            if skip_to_do:
                if current in ("do",) and not quoted:
                    skip_to_do, at_start = False, True
                return
            if not at_start:
                if current == "in" and not quoted and commands_pending_case[0]:
                    commands_pending_case[0] = False
                    in_pattern = True
                return
            if not quoted and current in SHELL_KEYWORDS:
                if current == "case":
                    commands_pending_case[0] = True
                    at_start = False
                elif current == "for":
                    skip_to_do, at_start = True, False
                elif current in ("fi", "done", "esac", "}", "in"):
                    at_start = False
                else:
                    at_start = True
                return
            if _ASSIGNMENT.match(current):
                return
            if current in functions:
                at_start = False
                return
            commands.append(current)
            at_start = False

        commands_pending_case = [False]
        while index < length:
            ch = text[index]
            if ch == "\\" and index + 1 < length:
                word += text[index + 1]
                index += 2
                continue
            if ch == "'":
                end = text.index("'", index + 1)
                word += text[index + 1:end]
                word_quoted = True
                index = end + 1
                continue
            if ch == '"':
                index += 1
                while text[index] != '"':
                    if text[index] == "\\":
                        index += 2
                    elif text.startswith("$(", index):
                        index = scan(index + 2, ")")
                    elif text[index] == "`":
                        index = scan(index + 1, "`")
                    else:
                        index += 1
                word_quoted = True
                index += 1
                continue
            if text.startswith("$(", index):
                finish()
                index = scan(index + 2, ")")
                at_start = False
                continue
            if ch == "`":
                index = scan(index + 1, "`")
                continue
            if ch == "#" and word == "" and not word_quoted:
                while index < length and text[index] != "\n":
                    index += 1
                continue
            if ch == closer and closer:
                finish()
                return index + 1
            if ch == "\n":
                finish()
                for strip_tabs, delimiter in pending_heredocs:
                    index += 1
                    while index < length:
                        line_end = text.find("\n", index)
                        line_end = length if line_end < 0 else line_end
                        line = text[index:line_end]
                        index = line_end
                        if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                            break
                        index += 1
                pending_heredocs.clear()
                at_start = True
                index += 1
                continue
            if ch in " \t":
                finish()
                index += 1
                continue
            if text.startswith("<<", index) and not text.startswith("<<<", index):
                match = _HEREDOC.match(text, index)
                if match:
                    pending_heredocs.append((match.group(1) == "-", match.group(2) or match.group(3) or match.group(4)))
                    finish()
                    index = match.end()
                    continue
            if text.startswith(";;", index):
                finish()
                in_pattern, at_start = True, False
                index += 2
                continue
            if ch == ")" and in_pattern:
                finish()
                in_pattern, at_start = False, True
                index += 1
                continue
            if ch == "&" and index > 0 and text[index - 1] in "<>":
                word += ch
                index += 1
                continue
            if ch in ";&|(){}" and not (ch in "{}" and (word != "" or word_quoted)):
                finish()
                if ch in "{}":
                    word = ch
                    finish()
                    at_start = ch == "{"
                else:
                    at_start = ch != ")"
                index += 1
                continue
            word += ch
            index += 1
        finish()
        return index

    scan(0, "")
    return commands


def static_external_counts(script_text: str) -> dict:
    """{command name: static occurrence count} of the external commands the script may execute (builtins,
    keywords and its own functions excluded), an upper bound over control-flow paths."""
    counts = {}
    for word in shell_simple_commands(script_text):
        if word in SHELL_BUILTINS or word in SHELL_KEYWORDS or "/" in word or "$" in word or not word:
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def parse_xtrace_counts(stderr_text: str, functions=()) -> dict:
    """{command name: count} of the external commands in a `sh -x` trace (`+ cmd args` lines)."""
    counts = {}
    for line in stderr_text.split("\n"):
        match = re.match(r"\++ (\S+)", line)
        if not match:
            continue
        word = match.group(1)
        if word in SHELL_BUILTINS or word in SHELL_KEYWORDS or word in functions or "=" in word:
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def compare_observation(static_counts: dict, observed_counts: dict) -> dict:
    """An observation must use only statically derivable commands, each at most as often as derived."""
    extra = sorted(name for name in observed_counts if name not in static_counts)
    above = sorted(name for name, count in observed_counts.items() if count > static_counts.get(name, 0))
    return {"consistent": not extra and not above, "unexpected_commands": extra, "above_static_maximum": above}


def approved_sequence_of(head_text: str) -> list:
    """APPROVED_SEQUENCE of an embedded hook head, read from its syntax tree (never executed)."""
    import ast

    found = [node.value for node in ast.walk(ast.parse(head_text))
             if isinstance(node, ast.NamedExpr) and getattr(node.target, "id", None) == "APPROVED_SEQUENCE"]
    if len(found) != 1:
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "APPROVED_SEQUENCE_LITERAL")
    return ast.literal_eval(found[0])


def allowed_record_of(approved: list) -> list:
    return [[index + 1, item[0], item[1]] for index, item in enumerate(approved)]


def chain_rows(chain: dict) -> list:
    """The flattened chain records in the provisioning script's E2_CHAIN_TOOLS order."""
    entries = list(chain["helpers"]) + [chain["interpreter"]] + list(chain["descendants"]) + list(chain["data_files"])
    return [[entry["invoked_path"], entry["realpath"], entry["sha256"], ",".join(entry["owner_packages"]),
             ",".join(entry["owner_versions"]), entry["link_string"]] for entry in entries]


def script_chain_constants(script_text: str) -> dict:
    """E2_CHAIN_TOOLS, E2_CHAIN_ABSENT and the two allowed-record digests as the script carries them."""
    constants = {}
    for name in ("E2_CHAIN_TOOLS", "E2_CHAIN_ABSENT"):
        match = re.search(r"readonly %s=\(([^)]*)\)" % name, script_text)
        if not match:
            raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", name)
        constants[name] = match.group(1).split()
    for name in ("EMPTY_ALLOWED_SHA256", "E2_ALLOWED_SHA256"):
        match = re.search(r"readonly %s=([0-9a-f]{64})\n" % name, script_text)
        if not match:
            raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", name)
        constants[name] = match.group(1)
    return constants


class RealChainHost:
    """Read-only identity queries of the real host (no helper is executed)."""

    lexists = staticmethod(os.path.lexists)
    islink = staticmethod(os.path.islink)
    isfile = staticmethod(os.path.isfile)
    readlink = staticmethod(os.readlink)
    realpath = staticmethod(os.path.realpath)

    @staticmethod
    def read_bytes(path):
        return Path(path).read_bytes()

    @staticmethod
    def owners(real_path):
        import subprocess

        completed = subprocess.run(["/usr/bin/dpkg-query", "-S", real_path], stdin=subprocess.DEVNULL, capture_output=True,
                                   env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
        if completed.returncode != 0:
            return []
        packages = set()
        for line in completed.stdout.decode("utf-8", "replace").split("\n"):
            if line.startswith("diversion by ") or not line.endswith(": " + real_path):
                continue
            for item in line[: -len(": " + real_path)].split(", "):
                packages.add(item.split(":", 1)[0])
        return sorted(packages)

    @staticmethod
    def version(package):
        import subprocess

        completed = subprocess.run(["/usr/bin/dpkg-query", "-W", "-f", "${Version}", "--", package],
                                   stdin=subprocess.DEVNULL, capture_output=True, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
                                   check=True)
        return completed.stdout.decode("utf-8")


def _chain_identity(host, invoked: str) -> dict:
    real = host.realpath(invoked)
    owners = host.owners(real)
    if not owners:
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "UNOWNED", path=invoked)
    return {"invoked_path": invoked, "realpath": real, "sha256": sha256_hex(host.read_bytes(real)),
            "owner_packages": list(owners), "owner_versions": [host.version(item) for item in owners],
            "link_string": host.readlink(invoked) if host.islink(invoked) else ""}


def _path_hit(host, name: str) -> tuple:
    """(first existing closed-PATH candidate, the candidates that precede it)."""
    preceding = []
    for directory in CLOSED_PATH:
        candidate = "%s/%s" % (directory, name)
        if host.lexists(candidate):
            return candidate, preceding
        preceding.append(candidate)
    raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "NOT_FOUND", name=name)


def capture_e2_helper_chain(host, script_text: str, observed_counts=None) -> dict:
    """The operator_base_interpreter.e2_helper_chain record from a host and the provisioning script's own
    constants. Nothing is executed: the descendant set is derived by static analysis of the hash-bound
    lsb_release script; OBSERVED_COUNTS (from a tracer or `sh -x` on a host where observation is permitted)
    is cross-checked and recorded as evidence only."""
    constants = script_chain_constants(script_text)
    head = extract_embedded(script_text, "HOOK_HEAD_E2")
    approved = approved_sequence_of(head)
    tools, absent_expected = constants["E2_CHAIN_TOOLS"], constants["E2_CHAIN_ABSENT"]
    helpers, absent = [], []
    for name in ("lsb_release", "uname"):
        hit, preceding = _path_hit(host, name)
        if hit != "/usr/bin/" + name:
            raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "RESOLVED_PATH", path=hit)
        absent += preceding
        helpers.append(dict(_chain_identity(host, hit), argv=CHAIN_HELPER_ARGV[name], name=name))
    script_bytes = host.read_bytes(helpers[0]["realpath"])
    first_line = script_bytes.split(b"\n", 1)[0].decode("utf-8", "replace")
    if first_line != "#!/bin/sh":
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "SHEBANG", line=first_line)
    interpreter = dict(_chain_identity(host, "/bin/sh"), name="sh")
    script_text_of_helper = script_bytes.decode("utf-8")
    static_counts = static_external_counts(script_text_of_helper)
    closed_covered = sorted(name for name in static_counts if name in CLOSED_LIST_TOOL_NAMES)
    descendants = []
    for name in sorted(static_counts):
        if name in CLOSED_LIST_TOOL_NAMES:
            continue
        hit, preceding = _path_hit(host, name)
        if hit != "/usr/bin/" + name:
            raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "RESOLVED_PATH", path=hit)
        absent += preceding
        descendants.append(dict(_chain_identity(host, hit), multiplicity=static_counts[name], name=name))
    sourced = sorted(set(re.findall(r"os_release=(/[A-Za-z0-9_./-]+)", script_text_of_helper)))
    if sourced != ["/etc/os-release", "/usr/lib/os-release"]:
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "SOURCED_DATA_FILES", found=sourced)
    data_files = [_chain_identity(host, "/usr/lib/os-release"), _chain_identity(host, "/etc/os-release")]
    chain = {
        "absent_candidates": sorted(set(absent)),
        "closed_list_covered": closed_covered,
        "data_files": data_files,
        "descendants": descendants,
        "helpers": helpers,
        "interpreter": interpreter,
        "sequence": approved,
    }
    if [row[0] for row in chain_rows(chain)] != tools or chain["absent_candidates"] != absent_expected:
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "SCRIPT_CONSTANTS",
                       rows=[row[0] for row in chain_rows(chain)], absent=chain["absent_candidates"])
    for name in chain["absent_candidates"]:
        if host.lexists(name):
            raise Rejected(APT_UNEXPECTED_CHANGE, "HOST_TOOL_CHANGED", "ABSENT_CANDIDATE_PRESENT", path=name)
    if observed_counts is not None:
        chain["observation_evidence"] = dict(compare_observation(static_counts, observed_counts),
                                             observed=dict(sorted(observed_counts.items())),
                                             static_upper_bound=dict(sorted(static_counts.items())))
        if not chain["observation_evidence"]["consistent"]:
            raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "OBSERVATION_DIFFERS",
                           **chain["observation_evidence"])
    return chain


CLOSED_LIST_TOOL_NAMES = frozenset(("env", "bash", "sha256sum", "sort", "cat", "cp", "rm", "mkdir", "chmod", "mktemp",
                                    "readlink", "realpath", "stat", "find", "readelf", "ldconfig", "dpkg",
                                    "dpkg-query", "apt-get", "apt-cache", "apt-config"))


def check_e2_helper_chain(chain: dict, host, script_text: str) -> dict:
    """Hash-first identity check of every chain member against the manifest record, before E2: the same
    members the provisioning script records and rechecks. Any helper, hash, owner, version, link, path or
    absent-candidate difference is a failure; nothing is executed."""
    constants = script_chain_constants(script_text)
    rows = chain_rows(chain)
    if [row[0] for row in rows] != constants["E2_CHAIN_TOOLS"]:
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "TOOL_LIST")
    if chain["absent_candidates"] != constants["E2_CHAIN_ABSENT"]:
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "ABSENT_LIST")
    approved = approved_sequence_of(extract_embedded(script_text, "HOOK_HEAD_E2"))
    if chain["sequence"] != approved:
        raise Rejected(PROVISIONING_ENV_VIOLATION, "E2_HELPER_CHAIN", "SEQUENCE")
    for candidate in chain["absent_candidates"]:
        if host.lexists(candidate):
            raise Rejected(APT_UNEXPECTED_CHANGE, "HOST_TOOL_CHANGED", "ABSENT_CANDIDATE_PRESENT", path=candidate)
    for row in rows:
        live = _chain_identity(host, row[0])
        if live["realpath"] != row[1] or live["sha256"] != row[2]:
            raise Rejected(APT_UNEXPECTED_CHANGE, "HOST_TOOL_CHANGED", "TOOL_BYTES", path=row[0])
        if ",".join(live["owner_packages"]) != row[3] or ",".join(live["owner_versions"]) != row[4]:
            raise Rejected(APT_UNEXPECTED_CHANGE, "HOST_TOOL_PACKAGE", None, path=row[0])
        if live["link_string"] != row[5]:
            raise Rejected(APT_UNEXPECTED_CHANGE, "HOST_TOOL_CHANGED", "LINK_STRING", path=row[0])
    return {"result": "PASS", "members": [row[0] for row in rows], "absent_verified": list(chain["absent_candidates"])}


# =============================================================================
# PRE-GATE-(3) PROOF MODES: APT_NONINTERACTIVE_PROOF_V1 AND PROCESS_CREATION_PROOF_V1
# =============================================================================
# Both modes are evidence only and grant no authority. Neither mode ever runs
# `apt-get update` or installs anything; APT_NONINTERACTIVE_PROOF_V1 fails
# closed (result STOP) when the planned pins cannot be resolved against the
# package index that already exists on the host.

APT_PROOF_ENV = ("PATH=/usr/sbin:/usr/bin:/sbin:/bin", "LANG=C", "LC_ALL=C", "HOME=/nonexistent", "TMPDIR=/tmp",
                 "DEBIAN_FRONTEND=noninteractive")
APT_PROMPT_TEXT = "Do you want to continue"
APT_ABORT_TEXT = "Abort."
APT_PROOF_TIMEOUT_SECONDS = 1800
_APT_INST_LINE = re.compile(r"^Inst (\S+) ", re.M)


def apt_proof_argv(apt_plan: dict, form: str, archives_dir=None) -> list:
    """The APT_NONINTERACTIVE_PROOF_V1 argv forms: (a) SIMULATE is the governed
    argv plus --simulate; (b) DOWNLOAD_ONLY is the governed argv plus
    --download-only and the single proof-only `-o Dir::Cache::archives=<dir>`;
    (c) CONTROL is (b) without --yes. None carries an `update` verb."""
    if apt_plan["install_flags"] != list(INSTALL_FLAGS):
        _config_unapproved("INSTALL_FLAGS")
    planned = ["%s=%s" % (item["name"], item["version"]) for item in apt_plan["packages"]]
    base = ["/usr/bin/apt-get", "install"]
    if form == "SIMULATE":
        return base + list(INSTALL_FLAGS) + ["--simulate"] + planned
    if form == "DOWNLOAD_ONLY":
        return (base + list(INSTALL_FLAGS) + ["--download-only", "-o", "Dir::Cache::archives=%s" % archives_dir]
                + planned)
    if form == "CONTROL":
        flags = [flag for flag in INSTALL_FLAGS if flag != "--yes"]
        return base + flags + ["--download-only", "-o", "Dir::Cache::archives=%s" % archives_dir] + planned
    raise ValueError(form)


def apt_noninteractive_proof(manifest: dict, runner, snapshot, make_dir, remove_dir, geteuid, exists) -> dict:
    """APT_NONINTERACTIVE_PROOF_V1 on the pinned apt of the host. RUNNER(argv) -> (returncode, output)
    runs one command with stdin /dev/null in the closed environment; SNAPSHOT() is the parsed dpkg-query
    state; MAKE_DIR() creates the disposable archives directory (with an empty partial/ subdirectory);
    REMOVE_DIR(path) removes it. No step installs anything or refreshes the package index."""
    apt_plan = manifest["apt_plan"]
    record = {"proof": "APT_NONINTERACTIVE_PROOF_V1", "env": list(APT_PROOF_ENV), "stdin": "/dev/null",
              "apt_update_executed": False, "installs_anything": False, "runs": [], "result": None}

    def stop(reason, **extra):
        record.update(extra)
        record["result"] = "STOP"
        record["reason"] = reason
        return record

    def run(label, argv):
        if "update" in argv:
            raise AssertionError("the proof never refreshes the package index")
        returncode, output = runner(argv)
        entry = {"label": label, "argv": list(argv), "returncode": returncode,
                 "prompt_text_seen": APT_PROMPT_TEXT in output, "abort_seen": APT_ABORT_TEXT in output,
                 "output_tail": output[-400:]}
        record["runs"].append(entry)
        return returncode, output, entry

    if geteuid() != 0:
        return stop("NOT_ROOT")
    planned_names = {item["name"] for item in apt_plan["packages"]}
    returncode, output, _ = run("VERSION", ["/usr/bin/apt-get", "--version"])
    record["apt_get_version"] = output.split("\n", 1)[0] if returncode == 0 else None
    if returncode != 0:
        return stop("APT_VERSION_UNAVAILABLE")
    returncode, output, entry = run("SIMULATE", apt_proof_argv(apt_plan, "SIMULATE"))
    if returncode != 0 or entry["prompt_text_seen"] or entry["abort_seen"]:
        return stop("SIMULATE_FAILED")
    extras = sorted({name.split(":", 1)[0] for name in _APT_INST_LINE.findall(output)} - planned_names)
    record["extra_packages_in_resolution"] = len(extras)
    archives = make_dir()
    record["disposable_directory"] = archives
    try:
        forbidden = [manifest["operator_python_prefix"]] + list(manifest["sandbox_forbidden_canary_paths"])
        if any(_within(archives, item) for item in forbidden):
            return stop("DISPOSABLE_DIRECTORY_PLACEMENT")
        before = snapshot()
        returncode, output, entry = run("DOWNLOAD_ONLY", apt_proof_argv(apt_plan, "DOWNLOAD_ONLY", archives))
        after = snapshot()
        record["dpkg_state_unchanged"] = before == after
        if returncode != 0 or entry["prompt_text_seen"] or entry["abort_seen"] or before != after:
            return stop("DOWNLOAD_ONLY_FAILED")
        if extras:
            returncode, output, entry = run("CONTROL_WITHOUT_YES", apt_proof_argv(apt_plan, "CONTROL", archives))
            record["control"] = "PASS" if returncode != 0 and entry["abort_seen"] else "FAIL"
            if record["control"] != "PASS":
                return stop("CONTROL_NOT_ABORTED")
        else:
            record["control"] = "NOT_APPLICABLE"
    finally:
        remove_dir(archives)
        record["disposable_directory_removed"] = not exists(archives)
    if not record["disposable_directory_removed"]:
        return stop("DISPOSABLE_DIRECTORY_REMAINS")
    record["result"] = "PASS"
    return record


def real_apt_proof_dependencies():
    import shutil
    import subprocess
    import tempfile

    environment = dict(item.split("=", 1) for item in APT_PROOF_ENV)

    def runner(argv):
        try:
            completed = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, env=environment, timeout=APT_PROOF_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return 124, "TIMEOUT"
        return completed.returncode, completed.stdout.decode("utf-8", "replace")

    def snapshot():
        completed = subprocess.run(["/usr/bin/dpkg-query", "-W", "-f", "${Package}\t${Architecture}\t${Version}\t${Status}\n"],
                                   stdin=subprocess.DEVNULL, capture_output=True, env=environment, check=True)
        return parse_dpkg_query_state(completed.stdout.decode("utf-8"))

    def make_dir():
        path = tempfile.mkdtemp(prefix="career-os-apt-proof-", dir="/var/tmp")
        os.chmod(path, 0o755)
        os.mkdir(os.path.join(path, "partial"), 0o700)
        return path

    return runner, snapshot, make_dir, shutil.rmtree


PROCESS_PROOF_TIMEOUT_SECONDS = 60
PROCESS_PROOF_ENV = ("PATH=/usr/sbin:/usr/bin:/sbin:/bin", "LANG=C", "LC_ALL=C", "PYTHONDONTWRITEBYTECODE=1",
                     "PIP_CONFIG_FILE=/dev/null")
PROCESS_PROOF_STARTUP = ("-I", "-S", "-B", "-X")
ENUMERATION_PRELUDE = (
    "import os, sys\n"
    "_log = os.open(%r, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)\n"
    "def _enumerate(event, args, _write=os.write, _fd=_log):\n"
    "    _write(_fd, (event + '\\n').encode('ascii', 'replace'))\n"
    "sys.addaudithook(_enumerate)\n"
)
FORK_EXEC_CAPTURE_CODE = (
    "import subprocess\n"
    "captured = {}\n"
    "class _Captured(Exception):\n"
    "    pass\n"
    "def _intercept(*args):\n"
    "    captured['args'] = args\n"
    "    raise _Captured()\n"
    "subprocess._fork_exec = _intercept\n"
    "try:\n"
    "    subprocess.Popen(['/bin/sh', '-c', 'echo x > %s'], close_fds=True, cwd='/')\n"
    "except _Captured:\n"
    "    pass\n"
    "print(repr(captured['args']))\n"
)
PROOF_PIP_ARGUMENTS = ["--isolated", "install", "--require-hashes", "--only-binary=:all:", "--no-deps",
                       "--no-compile", "--disable-pip-version-check", "-r"]
PROOF_WHEEL_NAME = "careeros_proof-0.0.1-py3-none-any.whl"


def build_proof_wheel(directory: str) -> tuple:
    """A verifier-generated trivial pure-Python wheel (deterministic bytes)."""
    import base64
    import zipfile

    files = {
        "careeros_proof/__init__.py": b"VALUE = 1\n",
        "careeros_proof-0.0.1.dist-info/METADATA": b"Metadata-Version: 2.1\nName: careeros-proof\nVersion: 0.0.1\n",
        "careeros_proof-0.0.1.dist-info/WHEEL": (b"Wheel-Version: 1.0\nGenerator: career-os-verifier\n"
                                                 b"Root-Is-Purelib: true\nTag: py3-none-any\n"),
    }
    rows = []
    for name, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
        rows.append("%s,sha256=%s,%d" % (name, digest, len(data)))
    rows.append("careeros_proof-0.0.1.dist-info/RECORD,,")
    files["careeros_proof-0.0.1.dist-info/RECORD"] = ("\n".join(rows) + "\n").encode("ascii")
    path = os.path.join(directory, PROOF_WHEEL_NAME)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            archive.writestr(info, files[name])
    return path, file_sha256(path)


def governed_proof_code(hook_head: str, hook_tail: str, body: str) -> str:
    """HOOK_HEAD is the first statement, as in every governed execution; the
    imports precede the body that the shared HOOK_TAIL (FINAL_DENIED_CHECK) wraps."""
    return hook_head + "import sys, os, json\n" + body + hook_tail


def vector_main_body(vector_source: str) -> str:
    return "def main():\n" + "".join("    " + line + "\n" for line in vector_source.split("\n"))


def _proof_launch(interpreter: str, scratch: str, label: str, code: str) -> list:
    pycache = os.path.join(scratch, "pycache-" + label)
    os.mkdir(pycache, 0o700)
    if os.listdir(pycache):
        raise AssertionError("the pycache prefix must be empty before launch")
    return [interpreter, "-I", "-S", "-B", "-X", "pycache_prefix=" + pycache, "-c", code]


def _split_lines(text: str) -> list:
    return text.replace("\r\n", "\n").split("\n")


def _denied_record(output: str):
    prefix = "PROVISIONING_ENV_VIOLATION PROCESS_CREATION "
    for line in _split_lines(output):
        if line.startswith(prefix):
            return json.loads(line[len(prefix):])
    return None


def process_creation_proof(interpreter: str, script_text: str, run, scratch_root: str, pip_package_path=None,
                           include_prefix_run: bool = True, chain_check=None,
                           include_sequence_vectors: bool = True) -> dict:
    """PROCESS_CREATION_PROOF_V1 on the base interpreter. RUN(argv, env, cwd) -> (returncode, stdout,
    stderr) runs one fresh process. Every vector runs first under a non-denying enumeration hook and
    then under the real denying hook of the provisioning script (HOOK_HEAD, whose approved sequence is
    EMPTY, and HOOK_TAIL), in the exact governed startup form, in a disposable scratch directory that is
    removed afterwards. The disposable proof-prefix E2 run uses HOOK_HEAD_E2 (PROCESS_CREATION_RECORD_V2
    with the approved E2_HELPER_CHAIN_V1 sequence) after CHAIN_CHECK() has verified every chain member
    against the manifest record; CHAIN_CHECK raises Rejected on any difference."""
    import ast
    import shutil
    import tempfile

    record = {"proof": "PROCESS_CREATION_PROOF_V1", "interpreter": interpreter,
              "startup_form": "-I -S -B -X pycache_prefix=<empty scratch directory> -c <code>",
              "denied_event_set": list(DENIED_EVENT_SET), "vectors": [], "result": None}
    scratch = tempfile.mkdtemp(prefix="career-os-proc-proof-", dir=scratch_root)
    os.chmod(scratch, 0o700)
    record["scratch_directory"] = scratch
    environment = {item.split("=", 1)[0]: item.split("=", 1)[1] for item in PROCESS_PROOF_ENV}
    environment["HOME"] = scratch
    environment["TMPDIR"] = scratch
    failures, stops = [], []
    try:
        hook_head = extract_embedded(script_text, "HOOK_HEAD")
        hook_head_e2 = extract_embedded(script_text, "HOOK_HEAD_E2")
        hook_tail = extract_embedded(script_text, "HOOK_TAIL")
        constants = script_chain_constants(script_text)
        approved = approved_sequence_of(hook_head_e2)
        empty_digest, e2_digest = canonical_digest([]), canonical_digest(allowed_record_of(approved))
        record["approved_sequence"] = {"x0_and_e1": approved_sequence_of(hook_head), "e2": approved,
                                       "e2_allowed_events_sha256": e2_digest, "empty_allowed_events_sha256": empty_digest}
        if (approved_sequence_of(hook_head) != [] or empty_digest != constants["EMPTY_ALLOWED_SHA256"]
                or e2_digest != constants["E2_ALLOWED_SHA256"]):
            failures.append("APPROVED_SEQUENCE_CONSTANTS")
        capture_marker = os.path.join(scratch, "marker-capture")
        returncode, stdout, _ = run(_proof_launch(interpreter, scratch, "capture", FORK_EXEC_CAPTURE_CODE % capture_marker),
                                    environment, scratch)
        if returncode != 0:
            failures.append("FORK_EXEC_ARGUMENTS_UNAVAILABLE")
            fork_exec_arguments = None
        else:
            fork_exec_arguments = ast.literal_eval(stdout.strip())
        for index, vector in enumerate(PROCESS_CREATION_PROOF_VECTORS):
            marker = os.path.join(scratch, "marker-%d" % index)
            if vector == "_posixsubprocess.fork_exec" and fork_exec_arguments is None:
                record["vectors"].append({"vector": vector, "result": "FAIL", "reason": "FORK_EXEC_ARGUMENTS_UNAVAILABLE"})
                continue
            vector_arguments = fork_exec_arguments
            if vector_arguments is not None:
                vector_arguments = list(vector_arguments)
                vector_arguments[0] = [item.replace(capture_marker, marker) for item in vector_arguments[0]]
            source = vector_code(vector, marker, vector_arguments)
            log = os.path.join(scratch, "enumeration-%d.log" % index)
            _, _, _ = run(_proof_launch(interpreter, scratch, "enum-%d" % index, ENUMERATION_PRELUDE % log + source),
                          environment, scratch)
            marker_in_enumeration = os.path.lexists(marker)
            events = sorted(set(Path(log).read_text(encoding="ascii").split())) if os.path.lexists(log) else []
            if marker_in_enumeration:
                os.unlink(marker)
            observed = [event for event in events if event in DENIED_EVENT_SET]
            code = governed_proof_code(hook_head, hook_tail, vector_main_body(source))
            returncode, stdout, _ = run(_proof_launch(interpreter, scratch, "deny-%d" % index, code), environment, scratch)
            denied = _denied_record(stdout)
            recorded = sorted({row[1] for row in denied}) if denied else []
            marker_after_denial = os.path.lexists(marker)
            entry = {"vector": vector, "enumeration_marker_created": marker_in_enumeration,
                     "enumeration_events_in_denied_set": observed, "denied_events_recorded": recorded,
                     "marker_absent_after_denial": not marker_after_denial, "denying_exit_status": returncode,
                     "success_line_printed": "DENIED_EVENTS=0" in _split_lines(stdout)}
            if marker_in_enumeration and not observed:
                entry["result"], entry["reason"] = "STOP", "EVENT_SET_INCOMPLETE"
                stops.append(vector)
            elif (not marker_in_enumeration or not (set(recorded) & set(observed)) or marker_after_denial
                  or returncode == 0 or entry["success_line_printed"]):
                entry["result"], entry["reason"] = "FAIL", "VECTOR_REQUIREMENT"
                failures.append(vector)
            else:
                entry["result"] = "PASS"
            record["vectors"].append(entry)
        if include_sequence_vectors:
            record["sequence_vectors"] = _sequence_vectors(interpreter, scratch, run, environment, hook_head,
                                                           hook_head_e2, hook_tail, approved, e2_digest, empty_digest)
            for item in record["sequence_vectors"]:
                if item["result"] != "PASS":
                    failures.append("SEQUENCE_VECTOR:" + item["case"])
        if include_prefix_run:
            record["proof_prefix_run"] = _process_proof_prefix_run(
                interpreter, hook_head, hook_head_e2, hook_tail, scratch, run, environment, pip_package_path,
                approved, e2_digest, empty_digest, chain_check)
            if record["proof_prefix_run"]["result"] != "PASS":
                failures.append("PROOF_PREFIX_RUN")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        record["scratch_removed"] = not os.path.lexists(scratch)
    record["result"] = "STOP" if stops else ("FAIL" if failures or not record["scratch_removed"] else "PASS")
    record["failures"] = sorted(set(failures + stops))
    return record


def _audit_main_body(events) -> str:
    """A main() that emits synthetic audit events (no process is created): EVENTS is a list of
    (event name, Python source of the argument tuple)."""
    return "def main():\n" + "".join("    sys.audit(%r, *%s)\n" % (event, source) for event, source in events) + "    pass\n"


def _sequence_vectors(interpreter, scratch, run, environment, hook_head, hook_head_e2, hook_tail, approved,
                      e2_digest, empty_digest) -> list:
    """PROCESS_CREATION_RECORD_V2 vectors on the interpreter: exact sequence, and every deviation. Events are
    emitted with sys.audit using the approved payload sources, so no process is created."""
    exact = [(item[0], item[1]) for item in approved]

    def variant(index, old, new):
        changed = list(exact)
        assert old in changed[index][1]
        changed[index] = (changed[index][0], changed[index][1].replace(old, new))
        return changed

    cases = (
        ("exact_e2_sequence", hook_head_e2, exact, "PASS", e2_digest),
        ("empty_sequence_no_events", hook_head, [], "PASS", empty_digest),
        ("exact_sequence_under_empty_sequence", hook_head, exact, "DENIED", None),
        ("missing_last_event", hook_head_e2, exact[:3], "SEQUENCE", None),
        ("additional_event", hook_head_e2, exact + [exact[0]], "DENIED", None),
        ("repeated_first_event", hook_head_e2, [exact[0]] + exact, "DENIED", None),
        ("reordered_events", hook_head_e2, [exact[2], exact[3], exact[0], exact[1]], "DENIED", None),
        ("different_argv", hook_head_e2, variant(0, "'-a'", "'-r'"), "DENIED", None),
        ("different_executable_list", hook_head_e2, variant(1, "b'/usr/sbin/lsb_release', ", ""), "DENIED", None),
        ("different_executable", hook_head_e2, variant(2, "'uname'", "'sh'"), "DENIED", None),
        ("cwd_set", hook_head_e2, variant(0, "None, None)", "'/tmp', None)"), "DENIED", None),
        ("env_set", hook_head_e2, variant(0, "None, None)", "None, {'A': 'b'})"), "DENIED", None),
        ("other_process", hook_head_e2, [("subprocess.Popen", "('sh', ['sh', '-c', 'true'], None, None)")], "DENIED", None),
    )
    results = []
    for index, (name, head, events, expect, digest_expected) in enumerate(cases):
        code = governed_proof_code(head, hook_tail, _audit_main_body(events))
        returncode, stdout, _ = run(_proof_launch(interpreter, scratch, "seq-%d" % index, code), environment, scratch)
        lines = _split_lines(stdout)
        if expect == "PASS":
            ok = (returncode == 0 and "DENIED_EVENTS=0" in lines and ("ALLOWED_EVENTS=%s" % digest_expected) in lines)
        elif expect == "DENIED":
            ok = returncode == 71 and bool(_denied_record(stdout)) and "DENIED_EVENTS=0" not in lines
        else:
            ok = (returncode == 71 and "DENIED_EVENTS=0" not in lines and any(
                line.startswith("PROVISIONING_ENV_VIOLATION PROCESS_CREATION_SEQUENCE ") for line in lines))
        results.append({"case": name, "expected": expect, "exit_status": returncode, "result": "PASS" if ok else "FAIL"})
    return results


def _process_proof_prefix_run(interpreter, hook_head, hook_head_e2, hook_tail, scratch, run, environment,
                              pip_package_path, approved, e2_digest, empty_digest, chain_check) -> dict:
    """The E1 then E2 argv forms against a verifier-created temporary virtual environment (never the
    operator prefix) with a verifier-generated trivial wheel. E1 runs under the EMPTY approved sequence;
    E2 runs under the approved E2_HELPER_CHAIN_V1 sequence after the hash-first check of every chain
    member. PASS requires zero denied events, ALLOWED_EVENTS equal to the approved sequence, exit zero,
    no bytecode, and only IN_SITE and OUT_SCRIPT RECORD rows."""
    import glob
    import shutil

    result = {"result": "FAIL"}
    prefix = os.path.join(scratch, "proof-prefix")
    wheel_dir = os.path.join(scratch, "wheel")
    os.mkdir(wheel_dir, 0o700)
    wheel, wheel_sha = build_proof_wheel(wheel_dir)
    lock = os.path.join(scratch, "proof-requirements-lock.txt")
    with open(lock, "w", encoding="ascii", newline="\n") as handle:
        handle.write("careeros-proof @ file://%s --hash=sha256:%s\n" % (wheel, wheel_sha))
    e1_body = ("def main():\n    import venv\n    venv.EnvBuilder(system_site_packages=False, clear=False, symlinks=True,"
               " with_pip=False).create(%r)\n    sys.stdout.write('E1_PREFIX_CREATED=%%s\\n' %% %r)\n" % (prefix, prefix))
    returncode, stdout, stderr = run(_proof_launch(interpreter, scratch, "e1", governed_proof_code(hook_head, hook_tail, e1_body)),
                                     environment, scratch)
    e1_lines = _split_lines(stdout)
    result["e1"] = {"exit_status": returncode, "denied_events_zero": "DENIED_EVENTS=0" in e1_lines,
                    "allowed_events_empty": ("ALLOWED_EVENTS=%s" % empty_digest) in e1_lines,
                    "stdout_tail": stdout[-400:], "stderr_tail": stderr[-400:]}
    if returncode != 0 or not result["e1"]["denied_events_zero"] or not result["e1"]["allowed_events_empty"]:
        return result
    if pip_package_path is None:
        result["reason"] = "PIP_PACKAGE_PATH_MISSING"
        return result
    if chain_check is None:
        result["reason"] = "HELPER_CHAIN_CHECK_MISSING"
        return result
    try:
        result["helper_chain_check"] = chain_check()
    except Rejected as exc:
        result["helper_chain_check"] = {"result": "FAIL", "status": exc.status, "reason": exc.reason, "detail": exc.detail,
                                        "evidence": exc.evidence}
        result["reason"] = "HELPER_CHAIN_CHECK"
        return result
    pip_copy = os.path.join(scratch, "pip-copy")
    os.mkdir(pip_copy, 0o700)
    shutil.copytree(pip_package_path, os.path.join(pip_copy, "pip"), symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    arguments = PROOF_PIP_ARGUMENTS + [lock]
    e2_body = ("def main():\n    sys.path.insert(0, %r)\n    import runpy\n    sys.argv = ['pip'] + %r\n    status = 0\n"
               "    try:\n        runpy.run_module('pip', run_name='__main__', alter_sys=True)\n"
               "    except SystemExit as exit_request:\n        status = exit_request.code\n"
               "    if status not in (0, None):\n        raise SystemExit('PIP_INSTALL_FAILED %%s' %% status)\n"
               "    sys.stdout.write('E2_PIP_STATUS=0\\n')\n" % (pip_copy, arguments))
    returncode, stdout, stderr = run(_proof_launch(os.path.join(prefix, "bin", "python"), scratch, "e2",
                                                   governed_proof_code(hook_head_e2, hook_tail, e2_body)), environment,
                                     scratch)
    lines = _split_lines(stdout)
    counts, allowed_record = {}, None
    for line in lines:
        if line.startswith("CTYPES_EVENTS="):
            counts = json.loads(line[len("CTYPES_EVENTS="):])
        if line.startswith("ALLOWED_EVENTS_RECORD="):
            allowed_record = json.loads(line[len("ALLOWED_EVENTS_RECORD="):])
    bytecode = [os.path.join(directory, name) for directory, dirs, names in os.walk(prefix) for name in names + dirs
                if name.endswith(".pyc") or name == "__pycache__"]
    classes = set()
    dist_info = glob.glob(os.path.join(prefix, "lib", "python*", "site-packages", "careeros_proof-0.0.1.dist-info"))
    if dist_info:
        site = os.path.dirname(dist_info[0])
        with open(os.path.join(dist_info[0], "RECORD"), encoding="utf-8") as handle:
            for row in handle.read().splitlines():
                if row:
                    classes.add(record_row_class(row.rsplit(",", 2)[0], site, prefix))
    allowed_equal = allowed_record == allowed_record_of(approved) and ("ALLOWED_EVENTS=%s" % e2_digest) in lines
    result.update({"e2": {"exit_status": returncode, "pip_status_line": "E2_PIP_STATUS=0" in lines,
                          "denied_events_zero": "DENIED_EVENTS=0" in lines, "ctypes_event_counts": counts,
                          "allowed_events_equal_approved_sequence": allowed_equal,
                          "allowed_events_record": allowed_record,
                          "denied_events": _denied_record(stdout) or [],
                          "stdout_tail": stdout[-600:], "stderr_tail": stderr[-600:]},
                   "bytecode_files": len(bytecode), "record_row_classes": sorted(classes)})
    ok = (returncode == 0 and result["e2"]["pip_status_line"] and result["e2"]["denied_events_zero"] and allowed_equal
          and not bytecode and bool(classes) and classes <= {"IN_SITE", "OUT_SCRIPT"})
    result["result"] = "PASS" if ok else "FAIL"
    return result


def real_process_proof_runner(argv, environment, cwd):
    import subprocess

    try:
        completed = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, env=environment, cwd=cwd,
                                   timeout=PROCESS_PROOF_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return 124, "", "TIMEOUT"
    return (completed.returncode, completed.stdout.decode("utf-8", "replace"),
            completed.stderr.decode("utf-8", "replace"))


# =============================================================================
# PARTIAL POST-PROVISION EVIDENCE (deterministic subset only; nothing is fabricated)
# =============================================================================

EMPIRICAL_POST_FIELDS = (
    "approved_substitutions", "canonical_families", "docx_family_to_canonical", "fontconfig_file",
    "marker_glyph_map", "pdf_basefont_to_canonical", "pdfminer_type0_name_form", "sandbox_dirs",
    "sandbox_expected_unreachable_errnos", "sandbox_path", "sandbox_probe_interpreter_path",
    "sandbox_read_only_paths", "sandbox_symlinks",
)
PROVISIONING_EVIDENCE_POST_FIELDS = ("apt_installed_delta", "apt_preinstall_snapshot", "apt_source_record")
CONTENT_BINDING_ROOTS_NOT_DERIVED_HERE = (
    "(a) soffice install tree and executable", "(b) every sandbox_read_only_paths entry",
    "(c) bubblewrap executable", "(d) sandbox_probe_interpreter_path",
    "(i) NATIVE_CLOSURE_V1 members of operator_base_interpreter and native_closure_prefix",
    "(j) ABSENT roots for STARTUP_PATH_INPUTS_V1 candidates (the sys.path ABSENT roots are derived)",
)


def parse_provisioning_evidence(text: str) -> dict:
    """The `EVIDENCE key=value` lines of the provisioning script, by key (values kept verbatim)."""
    by_key = {}
    for line in text.split("\n"):
        if line.startswith("EVIDENCE ") and "=" in line:
            key, _, value = line[len("EVIDENCE "):].partition("=")
            by_key.setdefault(key, []).append(value)
    return by_key


def post_evidence(root: Path, approved_plan_digest: str, provisioning_evidence: str = None) -> dict:
    """From the exact PRE_PROVISION_PLAN manifest (POST keys still null), the live installed environment
    and optionally the provisioning evidence, compute the deterministic subset of POST_PROVISION_BINDING
    and name every field that remains. Fails closed (Rejected) on any difference between the live
    environment and the approved plan; it never populates an empirical field."""
    adapter = load_adapter()
    manifest = strict_json_loads((root / MANIFEST_RELPATH).read_bytes().decode("utf-8"))
    requirements_in = (root / REQUIREMENTS_IN_RELPATH).read_bytes()
    requirements_lock = (root / REQUIREMENTS_LOCK_RELPATH).read_bytes()
    still_null = [key for key in adapter.MANIFEST_POST_PROVISION_KEYS if manifest.get(key) is None]
    if len(still_null) != len(adapter.MANIFEST_POST_PROVISION_KEYS):
        raise Rejected(ENV_UNVERIFIED, "POST_KEYS_NOT_NULL", None, populated=sorted(
            set(adapter.MANIFEST_POST_PROVISION_KEYS) - set(still_null)))
    digest = adapter.plan_digest(manifest, requirements_in, requirements_lock)
    if digest != approved_plan_digest:
        raise Rejected(ENV_UNVERIFIED, "PLAN_DIGEST", None, computed=digest, approved=approved_plan_digest)
    interpreter = manifest["operator_base_interpreter"]
    prefix = manifest["operator_python_prefix"]
    real = os.path.realpath(interpreter["path"])
    if file_sha256(real) != interpreter["executable_sha256"]:
        raise Rejected(ENV_UNVERIFIED, "BASE_INTERPRETER", "EXECUTABLE_SHA256")
    stdlib_digest = tree_digest(interpreter["stdlib_path"], "STDLIB")
    if stdlib_digest != interpreter["stdlib_tree_digest"]:
        raise Rejected(ENV_UNVERIFIED, "BASE_INTERPRETER", "STDLIB_TREE_DIGEST")
    site = site_packages_of(prefix, interpreter["python_version"])
    distributions = installed_distributions(site)
    installed_set_equality([(name, item[0]) for name, item in distributions.items()], manifest)
    reconcile_fileset(site_files(site), {name: item[1] for name, item in distributions.items()}, site, prefix)
    apt_pins = []
    for item in manifest["apt_plan"]["packages"]:
        installed = dpkg_installed_version(item["name"], item["architecture"])
        if installed != item["version"]:
            raise Rejected(ENV_UNVERIFIED, "APT_PIN", None, package=item["name"], installed=installed)
        apt_pins.append([item["name"], item["architecture"], item["version"]])
    roots = [
        {"id": "f.base_interpreter", "kind": "FILE", "path": real},
        {"id": "g.stdlib", "kind": "STDLIB_TREE", "path": interpreter["stdlib_path"]},
        {"id": "h.prefix_pyvenv_cfg", "kind": "FILE", "path": prefix.rstrip("/") + "/pyvenv.cfg"},
    ]
    for name in sorted(distributions):
        roots.append({"id": "e.dist." + name, "kind": "DIST_RECORD", "path": name})
    runtime_sys_path = list(interpreter["sys_path_isolated_prefix"]) + [site]
    absent = sorted({entry for entry in (list(interpreter["sys_path_isolated"]) + list(
        interpreter["sys_path_isolated_prefix"]) + runtime_sys_path) if not os.path.lexists(entry)})
    for entry in absent:
        roots.append({"id": "j.absent." + entry, "kind": "ABSENT", "path": entry})

    def resolver(name):
        return site, distributions[name][1]

    for root_entry in roots:
        root_entry["expected_digest"] = adapter.root_digest(root_entry, (), {}, resolver)
    roots.sort(key=lambda item: item["id"])
    for root_entry in roots:
        if root_entry["id"] == "g.stdlib" and root_entry["expected_digest"] != interpreter["stdlib_tree_digest"]:
            raise Rejected(ENV_UNVERIFIED, "BASE_INTERPRETER", "STDLIB_TREE_DIGEST_ADAPTER")
    record = {
        "mode": "POST_EVIDENCE_PARTIAL",
        "plan_digest_verified": True,
        "approved_plan_digest": approved_plan_digest,
        "install_checks": {"base_interpreter_sha256": "MATCH", "stdlib_tree_digest": "MATCH",
                           "installed_set_equality": "PASS", "fileset_reconciliation": "PASS",
                           "apt_pins": apt_pins, "distributions": sorted(distributions)},
        "derived": {
            "approved_plan_digest": approved_plan_digest,
            "content_binding_partial": {"roots": roots, "runtime_sys_path": runtime_sys_path, "exclusions": []},
        },
        "deferred": {
            "empirical_post_fields": list(EMPIRICAL_POST_FIELDS),
            "provisioning_evidence_post_fields": list(PROVISIONING_EVIDENCE_POST_FIELDS),
            "content_binding_roots_not_derived": list(CONTENT_BINDING_ROOTS_NOT_DERIVED_HERE),
            "computed_last": ["content_binding (complete)", "manifest_self_digest"],
        },
        "manifest_post_keys_still_null": still_null,
        "post_binding_complete": False,
        "runtime_manifest_rule": "a runtime manifest with any null POST_PROVISION_BINDING key remains "
                                 "RENDER_ENVIRONMENT_UNVERIFIED (POST_BINDING_UNPOPULATED); this mode never relaxes it",
    }
    if provisioning_evidence is not None:
        by_key = parse_provisioning_evidence(provisioning_evidence)
        cache_records = parse_post_apt_ld_so_cache_records(by_key, interpreter["native_closure_digest"], approved_plan_digest)
        record["provisioning_evidence"] = {
            "sha256": sha256_hex(provisioning_evidence.encode("utf-8")),
            "line_counts": {key: len(values) for key, values in sorted(by_key.items())},
            "apt_get_version": (by_key.get("apt_get_version") or [None])[0],
            "apt_install_argv": (by_key.get("apt_install_argv") or [None])[0],
            "result": (by_key.get("result") or [None])[-1],
            "post_apt_ld_so_cache_records": cache_records,
        }
        if cache_records:
            # CONTENT BINDING of /etc/ld.so.cache is to its ACTUAL accepted post-apt bytes (the live post-provision
            # environment populates content_binding), never to the PRE_APT value that only native_closure_digest binds.
            record["derived"]["ld_so_cache_content_binding"] = {
                "path": LD_SO_CACHE_PATH, "kind": "FILE", "expected_digest": cache_records[0]["new_ld_so_cache_sha256"]}
    return record


# =============================================================================
# OPERATOR MODE
# =============================================================================

def operator_verify(root: Path) -> dict:
    """Post-provision verification of the live environment. Requires the
    governed runtime mode and a manifest whose POST keys are populated."""
    adapter = load_adapter()
    if sys.flags.isolated != 1 or sys.flags.no_site != 1 or sys.flags.dont_write_bytecode != 1:
        raise Rejected(ENV_UNVERIFIED, "INTERPRETER_MODE")
    manifest_bytes = (root / MANIFEST_RELPATH).read_bytes()
    plan_inputs = ((root / REQUIREMENTS_IN_RELPATH).read_bytes(), (root / REQUIREMENTS_LOCK_RELPATH).read_bytes())
    try:
        environment = adapter.verify_environment(manifest_bytes, make_live_verifier(), plan_inputs, None,
                                                 adapter.INSPECTION_ENTRY_PATH.read_bytes())
    except adapter.StageFailure as failure:
        return {"result": "FAIL", "outcome": failure.outcome.as_dict()}
    manifest = environment.manifest
    review = review_lock(manifest, plan_inputs[1])
    return {"result": "PASS", "manifest_digest": environment.manifest_digest,
            "content_binding_digest": environment.content_binding_digest,
            "runtime_manifest_digest": environment.runtime_manifest_digest, "lock_review": review}


# =============================================================================
# CLI
# =============================================================================

def _emit(record: dict) -> None:
    sys.stdout.write(json.dumps(record, sort_keys=True, indent=1, ensure_ascii=True) + "\n")


def apt_proof_mode(root: Path) -> dict:
    manifest = strict_json_loads((root / MANIFEST_RELPATH).read_bytes().decode("utf-8"))
    runner, snapshot, make_dir, remove_dir = real_apt_proof_dependencies()
    record = apt_noninteractive_proof(manifest, runner, snapshot, make_dir, remove_dir, os.geteuid, os.path.lexists)
    record["manifest_file_sha256"] = file_sha256(root / MANIFEST_RELPATH)
    record["verifier_sha256"] = file_sha256(root / VERIFIER_RELPATH)
    return record


def process_proof_mode(root: Path) -> dict:
    manifest = strict_json_loads((root / MANIFEST_RELPATH).read_bytes().decode("utf-8"))
    interpreter = manifest["operator_base_interpreter"]
    script_bytes = (root / PROVISIONING_SCRIPT_RELPATH).read_bytes()
    if file_sha256(os.path.realpath(interpreter["path"])) != interpreter["executable_sha256"]:
        raise Rejected(BASE_INTERPRETER_MISMATCH, "BASE_INTERPRETER", "EXECUTABLE_SHA256")
    if sha256_hex(script_bytes) != manifest["provisioning_script_sha256"]:
        raise Rejected(ENV_UNVERIFIED, "INSTRUMENT_DIGEST", "PROVISIONING_SCRIPT")
    script_text = script_bytes.decode("utf-8")
    chain = interpreter.get("e2_helper_chain")
    chain_check = None if not isinstance(chain, dict) else (
        lambda: check_e2_helper_chain(chain, RealChainHost(), script_text))
    record = process_creation_proof(interpreter["path"], script_text, real_process_proof_runner,
                                    "/tmp", manifest["installer_pip_package_path"], chain_check=chain_check)
    record["interpreter_executable_sha256"] = interpreter["executable_sha256"]
    record["provisioning_script_sha256"] = sha256_hex(script_bytes)
    record["verifier_sha256"] = file_sha256(root / VERIFIER_RELPATH)
    return record


def post_evidence_mode(root: Path, approved_plan_digest: str, evidence_path=None) -> dict:
    evidence = Path(evidence_path).read_text(encoding="utf-8") if evidence_path else None
    return post_evidence(root, approved_plan_digest, evidence)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--probe"] and len(argv) == 2:
        result = run_probe(json.loads(argv[1]))
        sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
        return 0 if result["ok"] else 1
    root = ROOT
    if "--checkout-root" in argv:
        index = argv.index("--checkout-root")
        root = Path(argv[index + 1])
        del argv[index:index + 2]
    try:
        if argv == ["--plan-digest"]:
            report = plan_report(root)
            _emit(report)
            return 0 if report["PRE_PROVISION_PLAN"] == "READY" else 3
        if len(argv) in (2, 4) and argv[0] == "--review-wheels":
            listing = None
            if len(argv) == 4 and argv[2] == "--candidate-listing":
                listing = strict_json_loads(Path(argv[3]).read_text(encoding="utf-8"))
            _emit(review_wheels(root, Path(argv[1]), listing))
            return 0
        if len(argv) == 5 and argv[0] == "--capture-plan":
            record = capture_plan(*argv[1:])
            record["e2_helper_chain"] = capture_e2_helper_chain(
                RealChainHost(), (root / PROVISIONING_SCRIPT_RELPATH).read_text(encoding="utf-8"))
            _emit(record)
            return 0
        if argv == ["--apt-noninteractive-proof"]:
            report = apt_proof_mode(root)
            _emit(report)
            return 0 if report["result"] == "PASS" else 1
        if argv == ["--process-creation-proof"]:
            report = process_proof_mode(root)
            _emit(report)
            return 0 if report["result"] == "PASS" else 1
        if (len(argv) in (2, 4) and argv[0] == "--post-evidence" and re.fullmatch(r"[0-9a-f]{64}", argv[1] or "")
                and (len(argv) == 2 or argv[2] == "--provisioning-evidence")):
            report = post_evidence_mode(root, argv[1], argv[3] if len(argv) == 4 else None)
            _emit(report)
            return 0
        if argv == ["--operator"]:
            report = operator_verify(root)
            _emit(report)
            return 0 if report["result"] == "PASS" else 1
    except Rejected as exc:
        _emit({"result": "FAIL", "status": exc.status, "reason": exc.reason, "detail": exc.detail,
               "evidence": exc.evidence})
        return 1
    sys.stderr.write("usage: verify_document_rendering_environment.py [--checkout-root DIR] "
                     "(--plan-digest | --review-wheels DIR [--candidate-listing FILE] | "
                     "--capture-plan INTERPRETER STDLIB_DIR PIP_DIR OPERATOR_PREFIX | --apt-noninteractive-proof | "
                     "--process-creation-proof | --post-evidence PLAN_DIGEST [--provisioning-evidence FILE] | "
                     "--operator | --probe SPEC)\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())

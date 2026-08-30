"""Targeted unit tests for compute_evaluation_inputs_digest()
(APPLICATION_GATE_V1_EVALUATION_INPUT_DIGEST_REMEDIATION, Cursor F-01/F-02).

Proves the recorded evaluation-input digest truthfully covers every trusted
input evaluate_application_question() actually depends on (both
evidence_index and claim_index), with deterministic canonicalization
(stable key ordering; insertion-order-independent).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_gate import compute_evaluation_inputs_digest  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


BASE_EVIDENCE = {
    "EV_001": {"evidence_id": "EV_001", "fact": "did X", "evidence_state": "VERIFIED"},
    "EV_002": {"evidence_id": "EV_002", "fact": "did Y", "evidence_state": "OBSERVED"},
}
BASE_CLAIMS = {
    "CLAIM_001": {"claim_id": "CLAIM_001", "wording": "Did X.", "evidence_ids": ["EV_001"], "human_approval": True},
    "CLAIM_002": {"claim_id": "CLAIM_002", "wording": "Did Y.", "evidence_ids": ["EV_002"], "human_approval": True},
}


# --- A. same Evidence + same Claims -> same digest ---
digest_1 = compute_evaluation_inputs_digest(copy.deepcopy(BASE_EVIDENCE), copy.deepcopy(BASE_CLAIMS))
digest_2 = compute_evaluation_inputs_digest(copy.deepcopy(BASE_EVIDENCE), copy.deepcopy(BASE_CLAIMS))
assert_true(digest_1 == digest_2, "A: identical Evidence + identical Claims must produce the same digest")
print("PASS: A -- same Evidence + same Claims -> same digest.")


# --- B. changed Evidence only -> different digest ---
changed_evidence = copy.deepcopy(BASE_EVIDENCE)
changed_evidence["EV_001"]["fact"] = "did X, revised wording"
digest_changed_evidence = compute_evaluation_inputs_digest(changed_evidence, copy.deepcopy(BASE_CLAIMS))
assert_true(digest_changed_evidence != digest_1, "B: an Evidence-only change must change the digest")
print("PASS: B -- changed Evidence only -> different digest.")


# --- C. changed Claims only -> different digest (this is exactly the F-01 gap) ---
changed_claims = copy.deepcopy(BASE_CLAIMS)
changed_claims["CLAIM_001"]["wording"] = "Did X differently."
digest_changed_claims = compute_evaluation_inputs_digest(copy.deepcopy(BASE_EVIDENCE), changed_claims)
assert_true(digest_changed_claims != digest_1, "C: a Claim-only change (wording) must change the digest -- this is the exact F-01 gap being remediated")

changed_claims_state = copy.deepcopy(BASE_CLAIMS)
changed_claims_state["CLAIM_002"]["evidence_state"] = "VERIFIED"
digest_changed_claim_state = compute_evaluation_inputs_digest(copy.deepcopy(BASE_EVIDENCE), changed_claims_state)
assert_true(digest_changed_claim_state != digest_1, "C: a Claim evidence_state-only change must also change the digest")

changed_claims_approval = copy.deepcopy(BASE_CLAIMS)
changed_claims_approval["CLAIM_002"]["human_approval"] = False
digest_changed_claim_approval = compute_evaluation_inputs_digest(copy.deepcopy(BASE_EVIDENCE), changed_claims_approval)
assert_true(digest_changed_claim_approval != digest_1, "C: a Claim human_approval-only change must also change the digest")
print("PASS: C -- changed Claims only (wording / evidence_state / human_approval) -> different digest.")


# --- D. same semantic dictionaries with different insertion order -> same digest ---
reordered_evidence = {"EV_002": BASE_EVIDENCE["EV_002"], "EV_001": BASE_EVIDENCE["EV_001"]}
reordered_claims = {"CLAIM_002": BASE_CLAIMS["CLAIM_002"], "CLAIM_001": BASE_CLAIMS["CLAIM_001"]}
digest_reordered = compute_evaluation_inputs_digest(reordered_evidence, reordered_claims)
assert_true(digest_reordered == digest_1, "D: differing dict insertion order with identical semantic content must produce the same digest")

reordered_claim_fields = {
    "CLAIM_001": {"human_approval": True, "evidence_ids": ["EV_001"], "wording": "Did X.", "claim_id": "CLAIM_001"},
    "CLAIM_002": {"human_approval": True, "evidence_ids": ["EV_002"], "wording": "Did Y.", "claim_id": "CLAIM_002"},
}
digest_reordered_fields = compute_evaluation_inputs_digest(copy.deepcopy(BASE_EVIDENCE), reordered_claim_fields)
assert_true(digest_reordered_fields == digest_1, "D: differing key insertion order within a record must not change the digest")
print("PASS: D -- differing insertion order (top-level and within a record) with identical semantic content -> same digest.")

print("ALL application_evaluation_digest_test CHECKS PASSED")

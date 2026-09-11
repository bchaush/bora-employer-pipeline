from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ledger = json.loads((ROOT / "docs" / "application" / "BORA_APPLICATION_HISTORY_V1.json").read_text(encoding="utf-8"))
agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
rule = (ROOT / ".cursor" / "rules" / "role-selection.mdc").read_text(encoding="utf-8")
blueprint = (ROOT / "BLUEPRINT.md").read_text(encoding="utf-8")
assert ledger["record_id"] == "BORA_APPLICATION_HISTORY_V1"
entries = ledger["entries"]
assert len(entries) == 14, len(entries)
keys = [(e["employer"], e["requisition_id"]) for e in entries]
assert len(keys) == len(set(keys)), "duplicate exact role identity in application ledger"
assert all(e["application_status"] == "SUBMITTED" for e in entries)
assert all(e["evidence_basis"] == "BORA_DIRECT_CONFIRMATION" for e in entries)
for req in ["003692SR","003736SR","003741SR","003836SR","RQ4076320","JR041580","R141882","R9102","JR102087","COORD002072","R0013342","260005JH","4720807005","30180"]:
    assert any(e["requisition_id"] == req for e in entries), req
assert "BORA_APPLICATION_HISTORY_V1.json" in agents
assert "BORA_APPLICATION_HISTORY_V1.json" in rule
assert "BORA_APPLICATION_HISTORY_V1.json" in blueprint
assert "LinkedIn Free and Brandeis Handshake" in agents
assert "never claim either was checked" in rule
print("PASS: canonical application-history ledger and discovery coverage lock verified.")

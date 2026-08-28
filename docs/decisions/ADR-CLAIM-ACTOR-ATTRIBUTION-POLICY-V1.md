# ADR — Claim Actor Attribution Policy v1

Status: **Approved**  
Date: 2026-08-28  
Approved by: Bora (architecture decision milestone)

## Context

MarketMind draft Claims use conventional résumé active voice (Built, Implemented, Integrated, Separated). The Claim schema stores a single `evidence_ids` list with no citation-role distinction. Claim `evidence_state` is validated against cited Evidence using a weakest-cited-Evidence floor (`claim_state_validation`).

`MM_AUTHOR_001` records a point-in-time GitHub contributor observation (`OBSERVED`). Mixing it into substantive `evidence_ids` forced otherwise `VERIFIED` MarketMind Claims to `OBSERVED`, conflating authorship metadata with substantive work facts.

Winter Walk reusable Claims already rely in practice on Bora's explicit Claim-level `human_approval` for conventional actor attribution while substantive facts remain in cited Evidence.

## Decision

Adopt **Claim Actor Attribution Policy v1**:

1. **Substantive truth** — `evidence_ids` establish what work, artifact, or capability exists. Claim `evidence_state` is calculated from substantive cited Evidence only via existing state validation. Do not cite authorship/contribution metadata Evidence solely to authorize active-voice wording.

2. **Actor attribution** — Explicit Bora `human_approval=true` on the exact Claim wording establishes that Bora confirms the Claim accurately describes work he personally performed or contributed to at the conventional résumé-authorship level.

3. **Firewall** — Human approval can never substitute for substantive Evidence. A Claim must pass schema, lineage, state, and semantic validation before approval can make it reusable.

4. **Limits of attribution** — Conventional actor attribution via human approval does **not** establish sole intellectual authorship, exclusive implementation, absence of AI assistance, absence of collaborators, authorship of every line, formal employment, paid work, or formal organizational title. Those require separate explicit Evidence and wording.

5. **Authorship Evidence use** — Records such as `MM_AUTHOR_001` remain valid Evidence but are cited only when the Claim's substantive proposition is specifically about that metadata (e.g., GitHub contributor observation), not merely because the Claim uses active voice.

## Why

Smallest reliable choice without schema expansion, citation-role fields, or weakening `ALLOWED_CITED_STATES_BY_CLAIM_STATE`. Preserves existing validators and aligns MarketMind remediation with Winter Walk practice.

## Alternatives Considered

- Citation-role schema (`substantive` vs `attribution` Evidence IDs) — deferred; larger architecture change.
- Require `MM_AUTHOR_001` in every active-voice Claim — rejected; corrupts substantive Claim state floor.
- Infer actor attribution from `experience_id` alone — rejected; no explicit architecture rule.

## Risks / Tradeoffs

- Actor attribution remains a human gate, not a deterministic Evidence field.
- `OBSERVED` Claims may rank below `VERIFIED` in requirement matching until approved substantive Evidence strengthens.
- Policy must be documented so builders do not re-mix authorship Evidence into substantive lineage.

## Affected Areas

- `claims/marketmind/CLAIM_MM_001`–`CLAIM_MM_005` (substantive lineage restored)
- `docs/decisions/ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md`
- `AGENTS.md` (reference)
- `.cursor/rules/truth.mdc` (operational pointer)
- `tests/claim_actor_attribution_policy_test.py`, `tests/marketmind_claim_drafting_test.py`

## Verification Required

- MarketMind Claims 001–004 `VERIFIED`; 005 `OBSERVED`; none cite `MM_AUTHOR_001`.
- All five remain `human_approval=false`, `reusable=false`.
- Synthetic tests: supported Claim + approval gate; invalid Claim + `human_approval=true` still fails.
- Full test suite and Golden Set pass; Winter Walk Claims and Evidence unchanged.

## Rollback / Reversal

Revert MarketMind Claim lineage changes and remove this ADR only via explicit approved architecture decision. Do not weaken state validators to simulate attribution via mixed Evidence.

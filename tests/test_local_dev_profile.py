import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / "local-dev" / "profile.json").read_text())


def test_shadow_shift_profile_is_canonical_and_offline():
    assert PROFILE["profile_schema_version"] == 1
    assert PROFILE["project_id"] == "shadow-shift"
    assert PROFILE["requires"] == []
    assert PROFILE["processes"] == []
    assert PROFILE["ingress_claims"] == []
    assert PROFILE["health_checks"] == []


def test_shadow_shift_profile_does_not_claim_shared_schema_or_edge_runtime():
    assert PROFILE["schema_overlays"] == []
    assert PROFILE["edge_functions"] == []
    assert PROFILE["optional_features"] == ["shadow-shift-cli", "shadow-shift-app"]

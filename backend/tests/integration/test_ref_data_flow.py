"""Integration tests for Reference Data (config) endpoints."""
import pytest
from httpx import AsyncClient


# ── Bloom Domains ─────────────────────────────────────────────────────────────

async def test_create_bloom_domain(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/bloom-domains",
        headers=auth_headers,
        json={"name": "Cognitive", "description": "Bloom cognitive domain"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Cognitive"
    assert data["is_active"] is True


async def test_create_bloom_domain_duplicate_name(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/config/bloom-domains",
        headers=auth_headers,
        json={"name": "Affective"},
    )
    resp = await client.post(
        "/api/v1/config/bloom-domains",
        headers=auth_headers,
        json={"name": "Affective"},
    )
    assert resp.status_code == 409


async def test_list_bloom_domains(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/config/bloom-domains",
        headers=auth_headers,
        json={"name": "Psychomotor"},
    )
    resp = await client.get("/api/v1/config/bloom-domains", headers=auth_headers)
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()]
    assert "Psychomotor" in names


async def test_update_bloom_domain(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/config/bloom-domains",
        headers=auth_headers,
        json={"name": "TempDomain"},
    )
    domain_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/config/bloom-domains/{domain_id}",
        headers=auth_headers,
        json={"description": "Updated desc"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated desc"


async def test_bloom_domain_denied_for_teacher(client: AsyncClient, teacher_auth_headers):
    resp = await client.post(
        "/api/v1/config/bloom-domains",
        headers=teacher_auth_headers,
        json={"name": "Forbidden Domain"},
    )
    assert resp.status_code == 403


# ── Bloom Levels ──────────────────────────────────────────────────────────────

async def _create_domain(client: AsyncClient, headers, name: str) -> str:
    resp = await client.post(
        "/api/v1/config/bloom-domains",
        headers=headers,
        json={"name": name},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_bloom_level(client: AsyncClient, auth_headers):
    domain_id = await _create_domain(client, auth_headers, "CognitiveLvl")
    resp = await client.post(
        "/api/v1/config/bloom-levels",
        headers=auth_headers,
        json={"bloom_domain_id": domain_id, "code": "C1", "name": "Remember", "order_index": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "C1"
    assert data["bloom_domain_id"] == domain_id


async def test_list_bloom_levels_by_domain(client: AsyncClient, auth_headers):
    domain_id = await _create_domain(client, auth_headers, "CognitiveLvlList")
    for i, (code, name) in enumerate([("C1", "Remember"), ("C2", "Understand")], 1):
        await client.post(
            "/api/v1/config/bloom-levels",
            headers=auth_headers,
            json={"bloom_domain_id": domain_id, "code": code, "name": name, "order_index": i},
        )
    resp = await client.get(f"/api/v1/config/bloom-domains/{domain_id}/levels", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_create_bloom_level_duplicate_code(client: AsyncClient, auth_headers):
    domain_id = await _create_domain(client, auth_headers, "CognitiveDup")
    payload = {"bloom_domain_id": domain_id, "code": "C1", "name": "Remember", "order_index": 1}
    await client.post("/api/v1/config/bloom-levels", headers=auth_headers, json=payload)
    resp = await client.post("/api/v1/config/bloom-levels", headers=auth_headers, json=payload)
    assert resp.status_code == 409


# ── Delivery Methods ──────────────────────────────────────────────────────────

async def test_create_delivery_method(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/delivery-methods",
        headers=auth_headers,
        json={"name": "Lecture", "description": "Instructor-led"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Lecture"


async def test_create_delivery_method_duplicate(client: AsyncClient, auth_headers):
    await client.post("/api/v1/config/delivery-methods", headers=auth_headers, json={"name": "Lab"})
    resp = await client.post("/api/v1/config/delivery-methods", headers=auth_headers, json={"name": "Lab"})
    assert resp.status_code == 409


async def test_list_delivery_methods(client: AsyncClient, auth_headers):
    await client.post("/api/v1/config/delivery-methods", headers=auth_headers, json={"name": "Tutorial"})
    resp = await client.get("/api/v1/config/delivery-methods", headers=auth_headers)
    assert resp.status_code == 200
    assert any(d["name"] == "Tutorial" for d in resp.json())


# ── Assessment Types ──────────────────────────────────────────────────────────

async def test_create_assessment_type(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/assessment-types",
        headers=auth_headers,
        json={"name": "Quiz", "is_sessional": False},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Quiz"
    assert data["is_sessional"] is False


async def test_create_sessional_assessment_type(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/assessment-types",
        headers=auth_headers,
        json={"name": "Lab Report", "is_sessional": True},
    )
    assert resp.status_code == 201
    assert resp.json()["is_sessional"] is True


# ── Mapping Weight Labels ─────────────────────────────────────────────────────

async def test_create_mapping_weights(client: AsyncClient, auth_headers):
    for value, label in [(1, "Low"), (2, "Medium"), (3, "High")]:
        resp = await client.post(
            "/api/v1/config/mapping-weights",
            headers=auth_headers,
            json={"weight_value": value, "label": label},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["weight_value"] == value
        assert data["label"] == label


async def test_create_mapping_weight_invalid_value(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/mapping-weights",
        headers=auth_headers,
        json={"weight_value": 5, "label": "Invalid"},
    )
    assert resp.status_code == 422


async def test_create_mapping_weight_duplicate(client: AsyncClient, auth_headers):
    await client.post(
        "/api/v1/config/mapping-weights",
        headers=auth_headers,
        json={"weight_value": 1, "label": "Low"},
    )
    resp = await client.post(
        "/api/v1/config/mapping-weights",
        headers=auth_headers,
        json={"weight_value": 1, "label": "Also Low"},
    )
    assert resp.status_code == 409


async def test_list_mapping_weights(client: AsyncClient, auth_headers):
    for value, label in [(1, "Low"), (2, "Medium"), (3, "High")]:
        await client.post(
            "/api/v1/config/mapping-weights",
            headers=auth_headers,
            json={"weight_value": value, "label": label},
        )
    resp = await client.get("/api/v1/config/mapping-weights", headers=auth_headers)
    assert resp.status_code == 200
    weights = resp.json()
    assert len([w for w in weights if w["weight_value"] in (1, 2, 3)]) >= 3


async def test_update_mapping_weight_label(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/config/mapping-weights",
        headers=auth_headers,
        json={"weight_value": 2, "label": "Mid"},
    )
    record_id = create_resp.json()["id"]
    resp = await client.patch(
        f"/api/v1/config/mapping-weights/{record_id}",
        headers=auth_headers,
        json={"label": "Medium"},
    )
    assert resp.status_code == 200
    assert resp.json()["label"] == "Medium"


# ── Complex Problems / Activities / Knowledge Profiles ────────────────────────

async def test_create_complex_problem(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/complex-problems",
        headers=auth_headers,
        json={"code": "CP1", "description": "Involves novel design constraints"},
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "CP1"


async def test_create_complex_activity(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/complex-activities",
        headers=auth_headers,
        json={"code": "CA1", "description": "Design and implementation activity"},
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "CA1"


async def test_create_knowledge_profile(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/config/knowledge-profiles",
        headers=auth_headers,
        json={"code": "KP1", "description": "Fundamental knowledge"},
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "KP1"

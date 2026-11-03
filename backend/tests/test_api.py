"""Tests for API routes in Aegis Knowledge System."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingest_and_query_workflow(client: AsyncClient) -> None:
    """Test full workflow: trigger ingestion, browse entities/facts, and execute queries."""
    # 1. Trigger ingestion
    ingest_resp = await client.post("/api/ingest")
    assert ingest_resp.status_code == 200
    report = ingest_resp.json()
    assert report["status"] in ["completed", "partial"]
    assert report["documents_processed"] >= 1
    assert report["total_facts_extracted"] >= 1

    # 2. Check ingestion status
    status_resp = await client.get("/api/ingest/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["total_documents"] >= 1
    assert status_data["total_facts"] >= 1

    # 3. List entities
    entities_resp = await client.get("/api/entities")
    assert entities_resp.status_code == 200
    entities = entities_resp.json()
    assert len(entities) >= 1
    first_entity_id = entities[0]["entity_id"]

    # 4. Get entity detail
    entity_detail_resp = await client.get(f"/api/entities/{first_entity_id}")
    assert entity_detail_resp.status_code == 200
    entity_detail = entity_detail_resp.json()
    assert entity_detail["entity_id"] == first_entity_id

    # 5. List facts
    facts_resp = await client.get("/api/facts")
    assert facts_resp.status_code == 200
    facts = facts_resp.json()
    assert len(facts) >= 1

    # 6. Query knowledge
    query_payload = {
        "question": "What is the operating pressure of the HPU-5000 Hydraulic Power Unit?",
        "top_k": 5,
        "include_conflicts": True,
    }
    query_resp = await client.post("/api/query", json=query_payload)
    assert query_resp.status_code == 200
    q_data = query_resp.json()
    assert q_data["question"] == query_payload["question"]
    assert len(q_data["answer"]) > 0
    assert q_data["confidence"] > 0


@pytest.mark.asyncio
async def test_conflicts_and_evaluation_endpoints(client: AsyncClient) -> None:
    """Test conflict browsing and evaluation harness."""
    # Trigger ingestion first to populate test data
    await client.post("/api/ingest")

    # List conflicts
    conflicts_resp = await client.get("/api/conflicts")
    assert conflicts_resp.status_code == 200
    conflicts = conflicts_resp.json()
    assert isinstance(conflicts, list)

    # Run evaluation
    eval_resp = await client.post("/api/evaluate", json={"sample_size": 2})
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["status"] == "completed"
    assert "metrics" in eval_data
    assert eval_data["metrics"]["total_questions"] == 2

    # Get latest evaluation results
    results_resp = await client.get("/api/evaluate/results")
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert results_data["status"] == "completed"

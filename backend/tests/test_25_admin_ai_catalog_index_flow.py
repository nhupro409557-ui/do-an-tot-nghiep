import asyncio


async def test_admin_ai_catalog_refresh_job_persists_without_external_commands(
    api_client,
    admin_headers,
    monkeypatch,
):
    from app.application.ai import catalog_index_refresh

    executed_steps: list[str] = []
    catalog_index_refresh._refresh_job = None

    async def fake_run_command(step: str, command: list[str]) -> None:
        assert catalog_index_refresh._refresh_job is not None
        executed_steps.append(step)
        output = catalog_index_refresh._refresh_job.get("output_tail") or ""
        catalog_index_refresh._refresh_job["step"] = step
        catalog_index_refresh._refresh_job["output_tail"] = (
            f"{output}\n{step}: ok"
        )[-catalog_index_refresh.OUTPUT_TAIL_CHARS :]
        await catalog_index_refresh._persist_refresh_job_safely(
            catalog_index_refresh._refresh_job
        )

    monkeypatch.setattr(catalog_index_refresh, "_run_command", fake_run_command)

    started = await api_client.post(
        "/api/admin/ai-catalog-index/refresh",
        headers=admin_headers,
    )
    assert started.status_code == 200, started.text
    started_payload = started.json()
    assert started_payload["started"] is True
    job_id = started_payload["job"]["id"]

    latest_job = None
    for _ in range(30):
        jobs = await api_client.get(
            "/api/admin/ai-catalog-index/jobs?limit=1",
            headers=admin_headers,
        )
        assert jobs.status_code == 200, jobs.text
        items = jobs.json()["items"]
        latest_job = items[0] if items else None
        if latest_job and latest_job["id"] == job_id and latest_job["status"] == "succeeded":
            break
        await asyncio.sleep(0.05)

    assert executed_steps == ["migrations", "cocoindex_markdown", "embedding_sync"]
    assert latest_job is not None
    assert latest_job["id"] == job_id
    assert latest_job["status"] == "succeeded"
    assert latest_job["step"] == "done"
    assert latest_job["error"] is None
    assert "embedding_sync: ok" in latest_job["output_tail"]

    status = await api_client.get(
        "/api/admin/ai-catalog-index/status",
        headers=admin_headers,
    )
    assert status.status_code == 200, status.text
    status_payload = status.json()
    assert status_payload["refresh_job"]["id"] == job_id
    assert status_payload["refresh_job"]["status"] == "succeeded"
    assert status_payload["recent_refresh_jobs"][0]["id"] == job_id

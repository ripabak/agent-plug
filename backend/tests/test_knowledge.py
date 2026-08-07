"""API tests for the knowledge base (sources) routes.

Indexing is monkeypatched to a no-op so tests never hit the network; the
pipeline itself is covered in test_pipeline.py / test_pdf.py.
"""
from pathlib import Path

from app.config import UPLOAD_DIR
from tests.test_pdf import make_pdf


async def noop_index(agent_id, mgr=None):
    return 0


async def noop_reindex(agent_id, only_failed=False, mgr=None):
    return 3


def _create_agent(client, headers):
    res = client.post(
        "/api/agents",
        json={"name": "KB Bot", "description": "kb"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_add_list_and_status(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)

    # no-op indexing (tests must not hit the network)
    async def noop_index(agent_id, mgr=None):
        return 0

    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources",
        json={"urls": ["https://example.com/a", "https://example.com/b", "https://example.com/a"]},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    sources = res.json()
    # duplicate URL skipped
    assert len(sources) == 2
    assert all(s["status"] == "pending" for s in sources)

    res = client.get(f"/api/agents/{agent['id']}/sources", headers=headers)
    assert len(res.json()) == 2


def test_invalid_url_rejected(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)

    async def noop_index(agent_id, mgr=None):
        return 0

    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources",
        json={"urls": ["not-a-url", "ftp://x.com"]},
        headers=headers,
    )
    assert res.status_code == 422


def test_delete_source(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)

    async def noop_index(agent_id, mgr=None):
        return 0

    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources",
        json={"urls": ["https://example.com/keep"]},
        headers=headers,
    )
    source_id = res.json()[0]["id"]

    assert client.delete(f"/api/agents/{agent['id']}/sources/{source_id}", headers=headers).status_code == 204
    res = client.get(f"/api/agents/{agent['id']}/sources", headers=headers)
    assert res.json() == []


def test_sources_scoped_to_agent(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent_a = _create_agent(client, headers)
    agent_b = _create_agent(client, headers)

    async def noop_index(agent_id, mgr=None):
        return 0

    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    client.post(
        f"/api/agents/{agent_a['id']}/sources",
        json={"urls": ["https://example.com/only-a"]},
        headers=headers,
    )
    res = client.get(f"/api/agents/{agent_b['id']}/sources", headers=headers)
    assert res.json() == []


def test_reindex_route(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)

    async def noop_reindex(agent_id, only_failed=False, mgr=None):
        return 3

    monkeypatch.setattr("app.routers.knowledge.reindex_agent", noop_reindex)

    res = client.post(f"/api/agents/{agent['id']}/sources/reindex", headers=headers)
    assert res.status_code == 200
    assert res.json() == {"scheduled": 3}


def test_upload_pdf_files(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    pdf_bytes = make_pdf("Uploaded manual content page one")
    res = client.post(
        f"/api/agents/{agent['id']}/sources/files",
        files=[
            ("files", ("manual.pdf", pdf_bytes, "application/pdf")),
            ("files", ("specs.pdf", make_pdf("Specs page"), "application/pdf")),
        ],
        headers=headers,
    )
    assert res.status_code == 201, res.text
    sources = res.json()
    assert len(sources) == 2
    for s in sources:
        assert s["kind"] == "pdf"
        assert s["status"] == "pending"
        assert s["file_name"].endswith(".pdf")
        assert s["file_size"] == len(pdf_bytes) or s["file_size"] > 0
        assert s["url"].startswith("file://")
        # the file must exist on disk under uploads/{agent_id}/
        rel = s["url"][len("file://"):]
        assert Path(UPLOAD_DIR, rel).is_file()


def test_upload_rejects_non_pdf(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources/files",
        files=[("files", ("notes.txt", b"not a pdf", "text/plain"))],
        headers=headers,
    )
    assert res.status_code == 422
    # nothing created
    res = client.get(f"/api/agents/{agent['id']}/sources", headers=headers)
    assert res.json() == []


def test_upload_rejects_oversized_file(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)
    monkeypatch.setattr("app.routers.knowledge.UPLOAD_MAX_SIZE", 10)  # 10 bytes

    res = client.post(
        f"/api/agents/{agent['id']}/sources/files",
        files=[("files", ("big.pdf", make_pdf("x"), "application/pdf"))],
        headers=headers,
    )
    assert res.status_code == 422
    assert "limit" in res.json()["detail"]


def test_delete_pdf_source_removes_file(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources/files",
        files=[("files", ("doc.pdf", make_pdf("Doc content"), "application/pdf"))],
        headers=headers,
    )
    source = res.json()[0]
    rel = source["url"][len("file://"):]
    path = Path(UPLOAD_DIR, rel)
    assert path.is_file()

    assert client.delete(
        f"/api/agents/{agent['id']}/sources/{source['id']}", headers=headers
    ).status_code == 204
    assert not path.exists()  # file removed from storage


def test_get_pdf_file_serves_document(client, auth_headers, monkeypatch):
    """The dashboard opens PDFs via the authed file endpoint."""
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    pdf_bytes = make_pdf("Clickable document content")
    res = client.post(
        f"/api/agents/{agent['id']}/sources/files",
        files=[("files", ("guide.pdf", pdf_bytes, "application/pdf"))],
        headers=headers,
    )
    source = res.json()[0]

    res = client.get(
        f"/api/agents/{agent['id']}/sources/{source['id']}/file", headers=headers
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "inline" in res.headers["content-disposition"]
    assert "guide.pdf" in res.headers["content-disposition"]
    assert res.content == pdf_bytes


def test_get_file_404_for_non_pdf_and_missing(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources",
        json={"urls": ["https://example.com/x"]},
        headers=headers,
    )
    url_source = res.json()[0]
    assert (
        client.get(
            f"/api/agents/{agent['id']}/sources/{url_source['id']}/file", headers=headers
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/agents/{agent['id']}/sources/999999/file", headers=headers
        ).status_code
        == 404
    )


def test_add_text_source(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources/text",
        json={"title": "FAQ Internal", "content": "Return policy is thirty days. Refunds are processed within five business days. " * 5},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    source = res.json()[0]
    assert source["kind"] == "text"
    assert source["title"] == "FAQ Internal"
    assert source["url"].startswith("text://")
    assert source["status"] == "pending"


def test_add_text_source_rejects_short_content(client, auth_headers, monkeypatch):
    headers, _ = auth_headers
    agent = _create_agent(client, headers)
    monkeypatch.setattr("app.routers.knowledge.index_pending_sources", noop_index)

    res = client.post(
        f"/api/agents/{agent['id']}/sources/text",
        json={"title": "Too short", "content": "hi"},
        headers=headers,
    )
    assert res.status_code == 422

import io

from docx import Document

from tests.conftest import JD, RESUME


def _post(client, name="resume.txt", content=RESUME, jd=JD, title="AI Engineer"):
    return client.post(
        "/api/analyze",
        files={"resume": (name, content, "application/octet-stream")},
        data={"job_description": jd, "job_title": title},
    )


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_configured"] is True


def test_analyze_txt_and_history_flow(client):
    res = _post(client)
    assert res.status_code == 200
    data = res.json()
    assert data["result"]["match_score"] == 82
    assert data["job_title"] == "AI Engineer"

    items = client.get("/api/history").json()
    assert any(i["id"] == data["id"] for i in items)

    detail = client.get(f"/api/history/{data['id']}")
    assert detail.status_code == 200
    assert detail.json()["result"]["missing_skills"] == ["Docker"]

    assert client.delete(f"/api/history/{data['id']}").status_code == 204
    assert client.get(f"/api/history/{data['id']}").status_code == 404


def test_analyze_docx(client):
    doc = Document()
    doc.add_paragraph(RESUME.decode())
    buf = io.BytesIO()
    doc.save(buf)
    assert _post(client, "resume.docx", buf.getvalue()).status_code == 200


def test_rejects_unsupported_type(client):
    assert _post(client, "resume.exe").status_code == 400


def test_rejects_short_job_description(client):
    assert _post(client, jd="too short").status_code == 422


def test_rejects_empty_resume(client):
    assert _post(client, content=b"hi").status_code == 400


def test_rejects_corrupt_pdf(client):
    assert _post(client, "resume.pdf", b"not a pdf").status_code == 400

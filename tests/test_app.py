import io, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import fitz, pytest
from PIL import Image
import app as A
@pytest.fixture(autouse=True)
def nokey(monkeypatch): monkeypatch.delenv("GROQ_API_KEY", raising=False)
c = A.app.test_client()
def pdf(text):
    d = fitz.open(); p = d.new_page()
    if text: p.insert_text((72, 72), text)
    return d.tobytes()
def img(w=100, h=100):
    b = io.BytesIO(); Image.effect_noise((w, h), 80).convert("RGB").save(b, "JPEG"); return b.getvalue()
def test_health(): assert c.get("/api/health").json["status"] == "ok"
def test_pdf_extract_no_key():
    r = c.post("/api/analyze-notification", data={"file": (io.BytesIO(pdf("Last date 5 May")), "n.pdf")})
    assert r.status_code == 200 and "Last date" in r.json["pages"][0]["text"] and r.json["source"] == "manual"
def test_empty_pdf(): assert c.post("/api/analyze-notification", data={"file": (io.BytesIO(pdf("")), "n.pdf")}).status_code == 422
def test_invalid_pdf(): assert c.post("/api/analyze-notification", data={"file": (io.BytesIO(b"junk"), "n.pdf")}).status_code == 415
def test_malformed_ai(monkeypatch):
    monkeypatch.setattr(A, "groq_chat", lambda s, u: (["bad"], None))
    r = c.post("/api/analyze-notification", data={"text": "hello"}); assert r.json["source"] == "manual"
def test_valid_ai(monkeypatch):
    monkeypatch.setattr(A, "groq_chat", lambda s, u: ({"title": "T", "dates": [{"text": "d", "page": 1}]}, None))
    assert c.post("/api/analyze-notification", data={"text": "hello"}).json["requirements"]["dates"][0]["page"] == 1
def v(data, name, rules): return c.post("/api/validate-document", data={"file": (io.BytesIO(data), name), "rules": json.dumps(rules)})
def test_size_dims():
    assert v(img(), "a.jpg", {"max_kb": 0.1}).json["status"] == "FIX REQUIRED"
    assert v(img(), "a.jpg", {"max_w": 50}).json["status"] == "FIX REQUIRED"
    assert v(img(), "a.jpg", {"max_w": 500, "max_kb": 500}).json["status"] == "PASS"
    assert v(img(), "a.jpg", {}).json["status"] == "VERIFY MANUALLY"
def test_unsupported(): assert v(b"hello", "a.txt", {}).status_code == 415
def test_ext_mismatch(): assert v(img(), "a.png", {"max_kb": 500}).json["status"] == "FIX REQUIRED"
def test_process_image():
    r = c.post("/api/process-image", data={"file": (io.BytesIO(img(400, 400)), "a.jpg"), "max_w": "100", "target_kb": "50"})
    assert r.status_code == 200 and Image.open(io.BytesIO(r.data)).width == 100
def test_process_impossible():
    assert c.post("/api/process-image", data={"file": (io.BytesIO(img(400, 400)), "a.jpg"), "target_kb": "1"}).status_code == 422
def test_report_and_errors():
    r = c.post("/api/generate-report", json={"title": "X", "answers": [{"label": "Percentage", "status": "Missing"}]})
    assert "Percentage" in r.json["report"] and "MANUAL" in r.json["report"]
    assert c.post("/api/generate-report", data="x").status_code == 400
def test_interpret_no_key(): assert c.post("/api/interpret-field", json={"label": "Univ", "profile_keys": ["institution"]}).json["key"] is None
def test_report_missing_doc():
    r = c.post("/api/generate-report", json={"documents": [{"name": "Photograph", "status": "MISSING"}]})
    assert "Document: Photograph (MISSING)" in r.json["report"]

def pdfs(n):
    d = fitz.open()
    for _ in range(n): d.new_page()
    return d.tobytes()
def test_pdf_merge_split_errors():
    r = c.post("/api/process-pdf", data={"op": "merge", "files": [(io.BytesIO(pdfs(1)), "a.pdf"), (io.BytesIO(pdfs(2)), "b.pdf")]})
    assert r.status_code == 200 and len(fitz.open(stream=r.data, filetype="pdf")) == 3
    f = lambda op, pg="": c.post("/api/process-pdf", data={"op": op, "pages": pg, "files": (io.BytesIO(pdfs(3)), "x.pdf")})
    assert len(fitz.open(stream=f("split", "3,1").data, filetype="pdf")) == 2
    assert f("split", "9").status_code == 400 and f("merge").status_code == 400
    assert f("compress").status_code == 200 and f("info").json["files"][0]["pages"] == 3
    assert c.post("/api/process-pdf", data={"op": "info", "files": (io.BytesIO(b"junk"), "x.pdf")}).status_code == 415
def test_readiness_pdf_and_headers():
    body = {"requirements": [{"text": "a", "review": "approved"}, {"text": "z", "review": "rejected"}], "answers": [{"label": "n", "status": "Ready", "reviewed": True}], "documents": [{"name": "P", "status": "MISSING"}]}
    j = c.post("/api/generate-report", json=body).json
    assert j["readiness"] == 67 and "z" not in j["report"]
    assert c.post("/api/generate-report", json={**body, "format": "pdf"}).data.startswith(b"%PDF")
    assert c.get("/api/health").headers["X-Content-Type-Options"] == "nosniff"
def test_unreviewed_not_counted():
    assert c.post("/api/generate-report", json={"answers": [{"label": "n", "status": "Ready"}]}).json["readiness"] == 0

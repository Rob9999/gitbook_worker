from gitbook_worker.src.gitbook_worker.utils import run
from gitbook_worker.src.gitbook_worker.linkcheck import check_links


class DummyResponse:
    def __init__(self, status_code=200, reason="OK"):
        self.status_code = status_code
        self.reason = reason


def test_run_success():
    out, err, code = run(["echo", "hello"], capture_output=True)
    assert code == 0
    assert "hello" in out


def test_check_links(tmp_path, monkeypatch):
    md = tmp_path / "test.md"
    md.write_text("[ok](https://example.com)\n[bad](https://bad.com)")
    responses = {
        "https://example.com": DummyResponse(200, "OK"),
        "https://bad.com": DummyResponse(404, "Not Found"),
    }

    def fake_head(url, timeout=5):
        return responses[url]

    monkeypatch.setattr("gitbook_worker.linkcheck.requests.head", fake_head)
    report = tmp_path / "report.csv"
    check_links([str(md)], str(report))
    content = report.read_text()
    assert "https://bad.com" in content

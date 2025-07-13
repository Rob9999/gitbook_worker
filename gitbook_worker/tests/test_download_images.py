import os
from gitbook_worker.src.gitbook_worker.utils import download_remote_images


class DummyResponse:
    def __init__(self, content=b"x", status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("bad status")


def test_download_remote_images(tmp_path, monkeypatch):
    md = tmp_path / "doc.md"
    md.write_text("![](http://ex.com/a.png)")
    dest = tmp_path / "imgs"

    def fake_get(url, timeout=10):
        return DummyResponse(b"data")

    monkeypatch.setattr("gitbook_worker.utils.requests.get", fake_get)
    count = download_remote_images(str(md), str(dest))
    assert count == 1
    text = md.read_text()
    assert "ex.com" not in text
    assert (dest / "a.png").exists()


def test_download_remote_images_name_conflict(tmp_path, monkeypatch):
    md = tmp_path / "doc.md"
    md.write_text("![](http://ex.com/a.png)")
    dest = tmp_path / "imgs"
    dest.mkdir()
    existing = dest / "a.png"
    existing.write_text("old")

    def fake_get(url, timeout=10):
        return DummyResponse(b"data")

    monkeypatch.setattr("gitbook_worker.utils.requests.get", fake_get)
    count = download_remote_images(str(md), str(dest))
    assert count == 1
    # existing file must remain untouched
    assert existing.read_text() == "old"
    files = sorted(p.name for p in dest.iterdir())
    assert "a.png" in files
    files.remove("a.png")
    assert len(files) == 1 and files[0].startswith("a_") and files[0].endswith(".png")
    text = md.read_text()
    assert os.path.join(str(dest), files[0]) in text

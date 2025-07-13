from gitbook_worker import utils, linkcheck, source_extract, validate_metadata

class DummyResponse:
    def __init__(self, status_code=200, reason="OK"):
        self.status_code = status_code
        self.reason = reason


def test_parse_summary(tmp_path):
    summary = tmp_path / "SUMMARY.md"
    chapter1 = tmp_path / "chapter1.md"
    sub = tmp_path / "sub"
    sub.mkdir()
    chapter2 = sub / "chapter2.md"
    chapter1.write_text("c1")
    chapter2.write_text("c2")
    summary.write_text("* [C1](chapter1.md)\n  * [C2](sub/chapter2.md)\n")
    result = utils.parse_summary(str(summary))
    assert result == [str(chapter1), str(chapter2)]


def test_extract_multiline_list_items():
    text = "1. first\ncontinued\n2- second\n* bullet\n  more bullet"
    items = source_extract.extract_multiline_list_items(text)
    assert items == [
        "1. first\ncontinued",
        "2- second",
        "* bullet\n  more bullet",
    ]


def test_validate_metadata(tmp_path):
    good = tmp_path / "good.md"
    good.write_text("---\ntitle: T\nauthor: A\ndate: 2021\n---\n")
    bad = tmp_path / "bad.md"
    bad.write_text("---\ntitle: T\ndate: 2021\n---\n")
    issues = validate_metadata([str(good), str(bad)])
    assert (str(bad), "Missing metadata field: author") in issues
    assert not any(i[0] == str(good) for i in issues)


def test_check_duplicate_headings(tmp_path):
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f1.write_text("# Title\n")
    f2.write_text("# Title\n")
    dup = linkcheck.check_duplicate_headings([str(f1), str(f2)])
    assert dup == [(str(f2), 1, "title", f"{f1}:1")]


def test_list_todos(tmp_path):
    md = tmp_path / "todo.md"
    md.write_text("line\n# TODO: task\ncontent\n# FIXME something")
    todos = linkcheck.list_todos([str(md)])
    assert len(todos) == 2
    assert todos[0][1] == 2


def test_check_images(tmp_path, monkeypatch):
    img_exists = tmp_path / "ok.png"
    img_exists.write_text("data")
    md = tmp_path / "img.md"
    md.write_text(
        f"![ok]({img_exists.name})\n"
        "![missing](missing.png)\n"
        "![remote](https://example.com/x.png)"
    )
    def fake_head(url, timeout=5):
        return DummyResponse(404, "Not Found")
    monkeypatch.setattr(linkcheck.requests, "head", fake_head)
    missing = linkcheck.check_images([str(md)])
    paths = [m[2] for m in missing]
    assert str(tmp_path / "missing.png") in paths
    assert "https://example.com/x.png" in paths
    assert all(m[0] == str(md) for m in missing)

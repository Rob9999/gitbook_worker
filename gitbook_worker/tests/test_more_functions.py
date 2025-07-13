import os
from gitbook_worker.src.gitbook_worker import (
    utils,
    linkcheck,
    source_extract,
    validate_metadata,
)


class DummyResponse:
    def __init__(self, status=200, reason="OK"):
        self.status_code = status
        self.reason = reason


def test_parse_summary_nested(tmp_path):
    nested = tmp_path / "nested" / "level"
    nested.mkdir(parents=True)
    f1 = tmp_path / "chap1.md"
    f2 = nested / "chap2.md"
    f1.write_text("c1")
    f2.write_text("c2")
    summary = tmp_path / "SUMMARY.md"
    summary.write_text(
        """\
* [One](chap1.md)
  * [Two](nested/level/chap2.md)
"""
    )
    result = utils.parse_summary(str(summary))
    assert result == [str(f1), str(f2)]


def test_extract_multiline_list_items_alpha():
    text = "a) Apple\nb) Banana\n  extra\n1. Numbered"
    items = source_extract.extract_multiline_list_items(text)
    assert items == ["a) Apple", "b) Banana\n  extra", "1. Numbered"]


def test_validate_metadata_no_frontmatter(tmp_path):
    md = tmp_path / "file.md"
    md.write_text("content only")
    issues = validate_metadata([str(md)])
    assert issues == []


def test_check_duplicate_headings_same_file(tmp_path):
    md = tmp_path / "dup.md"
    md.write_text("# Head\ntext\n## Other\n# Head\n")
    dups = linkcheck.check_duplicate_headings([str(md)])
    assert dups == [(str(md), 4, "head", f"{md}:1")]


def test_list_todos_multi(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("TODO first\n")
    b.write_text("text\nFIXME second\n")
    todos = linkcheck.list_todos([str(a), str(b)])
    assert [(os.path.basename(t[0]), t[1]) for t in todos] == [("a.md", 1), ("b.md", 2)]


def test_check_images_errors(tmp_path, monkeypatch):
    img = tmp_path / "ok.png"
    img.write_text("data")
    md = tmp_path / "file.md"
    md.write_text(f"![]({img.name})\n![](missing.png)\n![](http://remote/img)\n")

    def fake_head(url, timeout=5):
        raise Exception("boom")

    monkeypatch.setattr(linkcheck.requests, "head", fake_head)
    missing = linkcheck.check_images([str(md)])
    paths = [m[2] for m in missing]
    assert os.path.join(str(tmp_path), "missing.png") in paths
    assert "http://remote/img" in paths
    assert os.path.join(str(tmp_path), "ok.png") not in paths

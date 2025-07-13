import os
from gitbook_worker.src.gitbook_worker import (
    utils,
    linkcheck,
    source_extract,
    validate_metadata,
)


class DummyResp:
    def __init__(self, status=200, reason="OK"):
        self.status_code = status
        self.reason = reason


def test_parse_summary_nested(tmp_path):
    (tmp_path / "sub").mkdir()
    md1 = tmp_path / "a.md"
    md2 = tmp_path / "sub" / "b.md"
    md1.write_text("A")
    md2.write_text("B")
    summary = tmp_path / "SUMMARY.md"
    summary.write_text("* [A](a.md)\n  * [B](sub/b.md)\n")
    files = utils.parse_summary(str(summary))
    assert files == [str(md1), str(md2)]


def test_extract_multiline_list_items_complex():
    text = "1. one\n  continued\n- bullet\n  second line\n"
    items = source_extract.extract_multiline_list_items(text)
    assert items == ["1. one\n  continued", "- bullet\n  second line\n"]


def test_validate_metadata_mixed(tmp_path):
    good = tmp_path / "good.md"
    bad = tmp_path / "bad.md"
    good.write_text("---\ntitle: T\nauthor: A\ndate: 2020\n---\ntext")
    bad.write_text("---\ntitle: T\ndate: 2020\n---\ntext")
    issues = validate_metadata([str(good), str(bad)])
    assert (str(bad), "Missing metadata field: author") in issues
    assert not any(i[0] == str(good) for i in issues)


def test_check_duplicate_headings_detect(tmp_path):
    f1 = tmp_path / "f1.md"
    f2 = tmp_path / "f2.md"
    f1.write_text("# Title\n")
    f2.write_text("## Title\n")
    dup = linkcheck.check_duplicate_headings([str(f1), str(f2)])
    assert dup == [(str(f2), 1, "title", f"{f1}:1")]


def test_list_todos_collect(tmp_path):
    md = tmp_path / "todo.md"
    md.write_text("some\n# TODO fix\nmore\n# FIXME later")
    todos = linkcheck.list_todos([str(md)])
    assert [t[1] for t in todos] == [2, 4]


def test_check_images_network(tmp_path, monkeypatch):
    img = tmp_path / "x.png"
    img.write_text("data")
    md = tmp_path / "file.md"
    md.write_text(
        f"![](x.png)\n![](missing.png)\n![](http://good.com/img)\n![](http://bad.com/img)"
    )

    def fake_head(url, timeout=5):
        return DummyResp(200) if "good" in url else DummyResp(404, "Not Found")

    monkeypatch.setattr(linkcheck.requests, "head", fake_head)
    result = linkcheck.check_images([str(md)])
    paths = [r[2] for r in result]
    assert os.path.join(str(tmp_path), "missing.png") in paths
    assert "http://bad.com/img" in paths
    assert "http://good.com/img" not in paths
    assert os.path.join(str(tmp_path), "x.png") not in paths

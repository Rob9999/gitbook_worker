import os
from gitbook_worker.src.gitbook_worker import (
    utils,
    linkcheck,
    source_extract,
    validate_metadata,
)


class FakeResponse:
    def __init__(self, status=200, reason="OK"):
        self.status_code = status
        self.reason = reason


def test_parse_summary_multi_level(tmp_path):
    nested = tmp_path / "dir" / "sub"
    nested.mkdir(parents=True)
    md_1 = tmp_path / "root.md"
    md_2 = nested / "child.md"
    md_1.write_text("Root")
    md_2.write_text("Child")
    summary = tmp_path / "SUMMARY.md"
    summary.write_text("* [R](root.md)\n  * [C](dir/sub/child.md)\n")
    files = utils.parse_summary(str(summary))
    assert files == [str(md_1), str(md_2)]


def test_extract_multiline_list_items_various():
    text = "1. One\n  continued\n2) Two\n* Bullet\n  extra line"
    result = source_extract.extract_multiline_list_items(text)
    assert result == ["1. One\n  continued", "2) Two", "* Bullet\n  extra line"]


def test_validate_metadata_mixed_files(tmp_path):
    good = tmp_path / "good.md"
    bad = tmp_path / "bad.md"
    good.write_text("---\ntitle: T\nauthor: A\ndate: 2020\n---\n")
    bad.write_text("---\ntitle: T\n---\n")
    issues = validate_metadata([str(good), str(bad)])
    assert (str(bad), "Missing metadata field: author") in issues
    assert not any(i[0] == str(good) for i in issues)


def test_check_duplicate_headings_across_files(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("# Heading\n")
    b.write_text("## Heading\n")
    dups = linkcheck.check_duplicate_headings([str(a), str(b)])
    assert dups == [(str(b), 1, "heading", f"{a}:1")]


def test_list_todos_simple(tmp_path):
    md = tmp_path / "todo.md"
    md.write_text("Do\nTODO item\ntext\nFIXME note")
    todos = linkcheck.list_todos([str(md)])
    assert [t[1] for t in todos] == [2, 4]


def test_check_images_local_and_remote(tmp_path, monkeypatch):
    img = tmp_path / "ok.png"
    img.write_text("data")
    md = tmp_path / "file.md"
    md.write_text(
        f"![]({img.name})\n![](missing.png)\n![](https://good/img)\n![](https://bad/img)"
    )

    def fake_head(url, timeout=5):
        return FakeResponse(200) if "good" in url else FakeResponse(404, "Not Found")

    monkeypatch.setattr(linkcheck.requests, "head", fake_head)
    missing = linkcheck.check_images([str(md)])
    paths = [m[2] for m in missing]
    assert os.path.join(str(tmp_path), "missing.png") in paths
    assert "https://bad/img" in paths
    assert "https://good/img" not in paths
    assert os.path.join(str(tmp_path), "ok.png") not in paths

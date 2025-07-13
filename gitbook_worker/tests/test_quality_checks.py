import os
from gitbook_worker.src.gitbook_worker import (
    utils,
    linkcheck,
    source_extract,
    validate_metadata,
    readability_report,
    proof_and_repair_internal_references,
    ai_tools,
)


class DummyResponse:
    def __init__(self, status_code=200, reason="OK"):
        self.status_code = status_code
        self.reason = reason


def test_parse_summary(tmp_path):
    (tmp_path / "sub").mkdir()
    md1 = tmp_path / "chap1.md"
    md2 = tmp_path / "sub" / "chap2.md"
    md1.write_text("# A")
    md2.write_text("# B")
    summary = tmp_path / "SUMMARY.md"
    summary.write_text("* [One](chap1.md)\n* [Two](sub/chap2.md)\n")

    result = utils.parse_summary(str(summary))
    assert result == [str(md1), str(md2)]


def test_extract_multiline_list_items():
    text = "1. First line\ncontinued\n* Bullet\nmore bullet\n"
    items = source_extract.extract_multiline_list_items(text)
    assert items == ["1. First line\ncontinued", "* Bullet\nmore bullet\n"]


def test_validate_metadata(tmp_path):
    md = tmp_path / "meta.md"
    md.write_text("---\ntitle: T\nauthor: A\n---\nbody")
    issues = validate_metadata([str(md)])
    assert issues == [(str(md), "Missing metadata field: date")]


def test_check_duplicate_headings(tmp_path):
    md1 = tmp_path / "a.md"
    md2 = tmp_path / "b.md"
    md1.write_text("# Title\n")
    md2.write_text("## Title\n")
    dups = linkcheck.check_duplicate_headings([str(md1), str(md2)])
    assert dups and dups[0][0] == str(md2)


def test_list_todos(tmp_path):
    md = tmp_path / "todo.md"
    md.write_text("Line\n# TODO fix\nText\n# FIXME later\n")
    todos = linkcheck.list_todos([str(md)])
    assert [t[1] for t in todos] == [2, 4]


def test_check_images(tmp_path, monkeypatch):
    img = tmp_path / "img.png"
    img.write_text("x")
    md = tmp_path / "file.md"
    md.write_text(
        "![](img.png)\n![](missing.png)\n![](http://good.com/i.png)\n![](http://bad.com/i.png)\n"
    )

    responses = {
        "http://good.com/i.png": DummyResponse(200, "OK"),
        "http://bad.com/i.png": DummyResponse(404, "Not Found"),
    }

    def fake_head(url, timeout=5):
        return responses[url]

    monkeypatch.setattr(linkcheck.requests, "head", fake_head)

    result = linkcheck.check_images([str(md)])

    missing_paths = [r[2] for r in result]
    assert os.path.join(str(tmp_path), "missing.png") in missing_paths
    assert "http://bad.com/i.png" in missing_paths
    assert "http://good.com/i.png" not in missing_paths
    assert os.path.join(str(tmp_path), "img.png") not in missing_paths


def test_extract_sources_and_readability(tmp_path):
    md1 = tmp_path / "one.md"
    md1.write_text("# T\n\n## Sources\n1. Ref https://ex.com\n")
    md2 = tmp_path / "two.md"
    md2.write_text("No sources here")
    sources = source_extract.extract_sources_to_dict([str(md1), str(md2)])
    assert str(md1) in sources and sources[str(md1)]

    csv = tmp_path / "out.csv"
    source_extract.extract_sources([str(md1)], str(csv))
    assert csv.exists()

    report = readability_report([str(md2)])
    assert report[0][0] == str(md2)


def test_citation_numbering(tmp_path):
    md = tmp_path / "cit.md"
    md.write_text("1. A\n3. B\n")
    gaps = linkcheck.check_citation_numbering([str(md)])
    assert gaps == [(str(md), [2])]


def test_internal_reference_noop(tmp_path, monkeypatch):
    summary = tmp_path / "SUMMARY.md"
    summary.write_text("* [A](a.md)\n")
    md = tmp_path / "a.md"
    md.write_text("text\n")
    monkeypatch.setattr(
        source_extract, "extract_sources_of_a_md_file_to_dict", lambda m: {}
    )
    monkeypatch.setattr(ai_tools, "extract_sources_of_a_md_file_to_dict", lambda m: {})
    proof_and_repair_internal_references([str(md)], str(summary))
    assert md.read_text() == "text\n"


def test_internal_reference_adds_footnote(tmp_path, monkeypatch):
    summary = tmp_path / "SUMMARY.md"
    summary.write_text("* [A](a.md)\n")
    md = tmp_path / "a.md"
    md.write_text("content\n")

    def fake_extract(file):
        return {
            str(file): [
                {
                    "Ref": {
                        "lineno": 1,
                        "line": "1. Ref missing",
                        "level": 1,
                        "link": "missing.md",
                        "numbering": "1",
                    }
                }
            ]
        }

    monkeypatch.setattr(
        source_extract, "extract_sources_of_a_md_file_to_dict", fake_extract
    )
    monkeypatch.setattr(ai_tools, "extract_sources_of_a_md_file_to_dict", fake_extract)
    proof_and_repair_internal_references([str(md)], str(summary))
    lines = md.read_text().splitlines()
    assert lines[0] == "Ref"
    assert lines[1] == "content"


def test_internal_reference_inserts_at_position(tmp_path, monkeypatch):
    summary = tmp_path / "SUMMARY.md"
    summary.write_text("* [A](a.md)\n")
    md = tmp_path / "a.md"
    md.write_text("line1\nline2\nline3\n")

    def fake_extract(file):
        return {
            str(file): [
                {
                    "Note": {
                        "lineno": 2,
                        "line": "1. Note missing",
                        "level": 1,
                        "link": "missing.md",
                        "numbering": "1",
                    }
                }
            ]
        }

    monkeypatch.setattr(
        source_extract, "extract_sources_of_a_md_file_to_dict", fake_extract
    )
    monkeypatch.setattr(ai_tools, "extract_sources_of_a_md_file_to_dict", fake_extract)
    proof_and_repair_internal_references([str(md)], str(summary))
    assert md.read_text().splitlines() == ["line1", "Note", "line2", "line3"]

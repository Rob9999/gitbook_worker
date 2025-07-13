from gitbook_worker.src.gitbook_worker import ai_tools, source_extract


def test_proof_and_repair_replaces_content(tmp_path, monkeypatch):
    md = tmp_path / "test.md"
    original_lines = [
        "# Title\n",
        "\n",
        "## Quellen\n",
        "1. Example https://example.com\n",
    ]
    md.write_text("".join(original_lines))

    def fake_extract(file):
        return {
            str(file): [
                {
                    "Example": {
                        "lineno": 4,
                        "line": "1. Example https://example.com",
                        "numbering": "1",
                        "level": 2,
                    }
                }
            ]
        }

    def fake_ask(prompt, ai_url, ai_api_key, ai_provider):
        return True, {
            "success": True,
            "new": "1. Example NEW",
            "validation_date": "2024-01-01",
            "type": "external reference",
            "hint": None,
            "error": None,
        }

    monkeypatch.setattr(
        source_extract, "extract_sources_of_a_md_file_to_dict", fake_extract
    )
    monkeypatch.setattr(ai_tools, "ask_ai", fake_ask)

    ai_tools.proof_and_repair_external_references([str(md)], "", "", "", "")

    content = md.read_text().splitlines()
    assert content.count("1. Example NEW") == 1
    assert "1. Example https://example.com" not in content

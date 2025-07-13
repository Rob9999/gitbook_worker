import os
from gitbook_worker.src.gitbook_worker import emoji_report


def test_emoji_report_counts(tmp_path):
    md = tmp_path / "file.md"
    md.write_text("Hello 😊 world 🚀")
    counts, table = emoji_report(str(md))
    assert counts.get("Emoticons") == 1
    assert counts.get("Transport and Map Symbols") == 1
    assert "| Unicode Block |" in table
    assert "Transport and Map Symbols" in table

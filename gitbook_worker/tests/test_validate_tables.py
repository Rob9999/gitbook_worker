from gitbook_worker.src.gitbook_worker.utils import validate_table_columns


def test_validate_table_columns_ok(tmp_path):
    md = tmp_path / "table.md"
    md.write_text("|A|B|\n|--|--|\n|1|2|\n")
    assert validate_table_columns(str(md)) == []


def test_validate_table_columns_reports_mismatch(tmp_path):
    md = tmp_path / "bad.md"
    md.write_text("|A|B|\n|--|--|\n|1|2|\n|3|\n")
    errs = validate_table_columns(str(md))
    assert errs
    assert "Line" in errs[0]

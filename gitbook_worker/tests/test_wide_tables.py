import shutil
import pytest
from pathlib import Path
from gitbook_worker.src.gitbook_worker.utils import (
    wrap_wide_tables,
    _write_pandoc_header,
    run,
)


def test_wrap_wide_tables_adds_landscape(tmp_path):
    md = tmp_path / "wide.md"
    md.write_text("|A|B|C|D|E|F|G|\n|--|--|--|--|--|--|--|\n|1|2|3|4|5|6|7|\n")
    wrap_wide_tables(str(md), threshold=5)
    text = md.read_text()
    assert text.startswith("::: {.landscape cols=7}\n")
    assert text.strip().endswith(":::")


def test_wrap_wide_tables_ignores_narrow(tmp_path):
    md = tmp_path / "narrow.md"
    md.write_text("|A|B|\n|--|--|\n|1|2|\n")
    wrap_wide_tables(str(md), threshold=5)
    text = md.read_text()
    assert "::: {.landscape" not in text
    assert ":::" not in text


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_wrap_wide_tables_html(tmp_path):
    md = tmp_path / "html.md"
    md.write_text(
        "<table><tr><td>A</td><td>B</td><td>C</td><td>D</td><td>E</td><td>F</td><td>G</td></tr></table>"
    )
    wrap_wide_tables(str(md), threshold=5)
    text = md.read_text()
    assert text.startswith("::: {.landscape cols=7}\n")
    assert text.strip().endswith(":::")


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_wrap_wide_tables_html_converted(tmp_path):
    md = tmp_path / "html2.md"
    md.write_text(
        "<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
    )
    wrap_wide_tables(str(md), threshold=1)
    lines = md.read_text().splitlines()
    assert lines[0] == "::: {.landscape cols=2}"
    assert "| A   | B   |" in lines
    assert "| 1   | 2   |" in lines
    assert lines[-1] == ":::"


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc not installed")
def test_landscape_longtable(tmp_path):
    md = tmp_path / "long.md"
    header = "|" + "|".join([f"C{i}" for i in range(6)]) + "|"
    sep = "|" + "|".join(["--"] * 6) + "|"
    rows = "\n".join(
        "|" + "|".join([str(j) for j in range(6)]) + "|" for _ in range(40)
    )
    md.write_text("\n".join([header, sep, rows]))
    wrap_wide_tables(str(md), threshold=5)
    header_tex = _write_pandoc_header(
        str(tmp_path),
        "",
        "Sans",
        "Mono",
        "Main",
        True,
        5,
        str(md),
    )
    filter_path = Path(__import__("gitbook_worker").__file__).with_name("landscape.lua")
    out_tex = tmp_path / "out.tex"
    cmd = [
        "pandoc",
        str(md),
        "-t",
        "latex",
        "--lua-filter",
        str(filter_path),
        "-H",
        header_tex,
        "-o",
        str(out_tex),
    ]
    _, _, code = run(cmd, capture_output=True)
    assert code == 0
    text = out_tex.read_text()
    assert "\\begin{ltablex}{\\linewidth}" in text
    assert "{XXXXXX}" in text

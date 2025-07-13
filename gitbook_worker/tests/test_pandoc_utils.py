from gitbook_worker.src.gitbook_worker.pandoc_utils import (
    build_docker_pandoc_cmd,
    build_pandoc_cmd,
)
from pathlib import Path


def test_build_docker_pandoc_cmd_includes_filter(tmp_path):
    cmd = build_docker_pandoc_cmd(
        out_dir=str(tmp_path),
        temp_dir=str(tmp_path),
        clone_dir=str(tmp_path),
        combined_md=str(tmp_path / "file.md"),
        pdf_output=str(tmp_path / "out.pdf"),
        header_file=str(tmp_path / "header.tex"),
        filter_paths=[str(tmp_path / "landscape.lua")],
    )
    assert "--lua-filter=/filters/landscape.lua" in cmd
    assert any("/filters" in part for part in cmd)
    assert "latex" in cmd


def test_build_pandoc_cmd_includes_filter():
    md_file = Path("anhang-a-erda-staatenarchitektur-konzentrische-kreise.md")
    cmd = build_pandoc_cmd(
        combined_md=str(md_file),
        pdf_output="out.pdf",
        resource_path=".",
        header_file="header.tex",
        filter_paths=["filter.lua"],
        extra_args=None,
    )
    assert str(md_file) in cmd
    assert "--lua-filter=filter.lua" in cmd
    assert "latex" in cmd


def test_landscape_lua_trailing_newline():
    path = Path(__import__("gitbook_worker").__file__).with_name("landscape.lua")
    data = path.read_bytes()
    assert data.endswith(b"\n")

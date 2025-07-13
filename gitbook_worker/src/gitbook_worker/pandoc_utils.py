import os
import logging
from datetime import datetime
from .utils import run


def build_docker_pandoc_cmd(
    out_dir: str,
    temp_dir: str,
    clone_dir: str,
    combined_md: str,
    pdf_output: str,
    header_file: str,
    filter_paths: list[str] | None,
) -> list[str]:
    """Return the Docker command to run pandoc with optional Lua filters."""
    abs_out_dir = os.path.abspath(out_dir)
    abs_temp_dir = os.path.abspath(temp_dir)
    abs_clone_dir = os.path.abspath(clone_dir)

    docker_out_dir = "/data"
    docker_temp_dir = "/temp"
    docker_clone_dir = "/gitbook_repo"

    docker_combined_md = f"/temp/{os.path.basename(combined_md)}"
    docker_pdf_output = f"/data/{os.path.basename(pdf_output)}"
    docker_header_file = f"/temp/{os.path.basename(header_file)}"

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{abs_out_dir}:{docker_out_dir}",
        "-v",
        f"{abs_temp_dir}:{docker_temp_dir}",
        "-v",
        f"{abs_clone_dir}:{docker_clone_dir}",
    ]
    if filter_paths:
        for p in filter_paths:
            cmd += ["-v", f"{os.path.dirname(p)}:/filters"]
    cmd += [
        "erda-pandoc",
        docker_combined_md,
        "-o",
        docker_pdf_output,
        "-f",
        "gfm+emoji+fenced_divs+raw_attribute",
        "-t",
        "latex",
        "--pdf-engine=lualatex",
        "--toc",
        "-V",
        "geometry=a4paper",
        f"--resource-path={docker_clone_dir}",
        "-H",
        docker_header_file,
    ]
    if filter_paths:
        for p in filter_paths:
            cmd.append(f"--lua-filter=/filters/{os.path.basename(p)}")
    return cmd


def build_pandoc_cmd(
    combined_md: str,
    pdf_output: str,
    resource_path: str,
    header_file: str,
    filter_paths: list[str] | None,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Return the pandoc command for local execution with optional Lua filters."""
    cmd = [
        "pandoc",
        combined_md,
        "-o",
        pdf_output,
        "-f",
        "gfm+emoji+fenced_divs+raw_attribute",
        "-t",
        "latex",
        "--pdf-engine=lualatex",
        "--toc",
        "-V",
        "geometry=a4paper",
    ]
    if extra_args:
        cmd.extend(extra_args)
    args = []
    if filter_paths:
        args.extend(f"--lua-filter={p}" for p in filter_paths)
    args.extend([f"--resource-path={resource_path}", "-H", header_file])
    cmd.extend(args)
    return cmd


def run_pandoc(cmd: list[str]):
    """Execute pandoc and return (stdout, stderr, exit_code)."""
    start = datetime.now()
    logging.info("Starting pandoc at %s", start.isoformat())
    logging.info("Pandoc command: %s", cmd)
    out, err, code = run(cmd, capture_output=True)
    end = datetime.now()
    logging.info("Pandoc finished at %s with exit code %s", end.isoformat(), code)
    return out, err, code

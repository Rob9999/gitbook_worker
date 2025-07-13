import logging
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - optional dep
    yaml = None

__version__ = "2.1.1"

from .utils import (
    run,
    parse_summary,
    readability_report,
    wrap_wide_tables,
    validate_table_columns,
    download_remote_images,
    emoji_report,
)
from .linkcheck import (
    check_links,
    check_images,
    check_duplicate_headings,
    check_citation_numbering,
    list_todos,
)
from .source_extract import (
    get_extract_multiline_list_items_pattern,
    extract_multiline_list_items,
    get_language_dependent_header_pattern_for_sources,
    extract_sources_of_a_md_file_to_dict,
    extract_sources_to_dict,
    extract_sources,
)
from .ai_tools import (
    ask_ai,
    extract_json_from_ai_output,
    proof_and_repair_internal_references,
    proof_and_repair_external_reference,
    proof_and_repair_external_references,
)
from .repo import (
    clone_or_update_repo,
    checkout_branch,
    remove_tree,
    remove_readonly,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def split_reference_to_description_and_urluri(name: str) -> tuple[str, str]:
    url_pattern = re.compile(r"\(?\[?(https?://[^\s\)\]\[]+|[^\s\)\]\[]+\.[^\s\)\]\[]+)\]?\)?")
    url_match = url_pattern.search(name)
    if url_match:
        value_part = url_match.group(1).strip()
        key_part = url_pattern.sub("", name).strip(', ":()[]').strip()
    else:
        key_part = name.strip(', ":()[]').strip()
        value_part = ""
    return key_part, value_part


def lint_markdown(repo_dir: str):
    """Run markdownlint on the repository and return its output."""
    return run(["markdownlint", "**/*.md"], cwd=repo_dir, capture_output=True)


def validate_metadata(md_files):
    """Validate YAML frontmatter metadata in markdown files."""
    issues = []
    if not yaml:
        logging.warning("PyYAML not installed; skipping metadata validation.")
        return issues
    for md in md_files:
        try:
            with open(md, encoding="utf-8") as f:
                content = f.read()
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    meta = yaml.safe_load(parts[1])
                    for field in ("title", "author", "date"):
                        if field not in meta:
                            issues.append((md, f"Missing metadata field: {field}"))
        except Exception as e:
            issues.append((md, f"Metadata parse error: {e}"))
    return issues


def spellcheck(repo_dir: str):
    """Run codespell to check for common spelling mistakes."""
    return run(["codespell", "-q", "3"], cwd=repo_dir, capture_output=True)

# Compatibility shim so tests can import "gitbook_worker.src.gitbook_worker".
import types
if "gitbook_worker.src.gitbook_worker" not in sys.modules:
    src_pkg = types.ModuleType("gitbook_worker.src")
    sys.modules["gitbook_worker.src"] = src_pkg
    sys.modules["gitbook_worker.src.gitbook_worker"] = sys.modules[__name__]

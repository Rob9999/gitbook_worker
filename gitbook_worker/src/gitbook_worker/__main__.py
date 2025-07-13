import sys
import argparse
import io
import os
import logging
from datetime import datetime
from .utils import (
    run,
    parse_summary,
    readability_report,
    wrap_wide_tables,
    validate_table_columns,
    download_remote_images,
    _write_pandoc_header,
    get_pandoc_version,
    emoji_report,
)
from .linkcheck import (
    check_links,
    check_images,
    check_duplicate_headings,
    check_citation_numbering,
    list_todos,
)
from .source_extract import extract_sources
from .ai_tools import (
    proof_and_repair_internal_references,
    proof_and_repair_external_references,
)
from .repo import clone_or_update_repo
from .docker_tools import ensure_docker_image, ensure_docker_desktop
from .pandoc_utils import build_docker_pandoc_cmd, build_pandoc_cmd, run_pandoc
from . import lint_markdown, validate_metadata, spellcheck


def main():

    parser = argparse.ArgumentParser(
        description="Works on a GITBook; e.g. builds a PDF and or runs quality checks"
    )
    parser.add_argument("repo_url", help="URL of the Git repository")
    parser.add_argument(
        "--branch",
        type=str,
        default="published",
        help="Branch of the Git repository",
    )
    parser.add_argument(
        "--use-docker",
        action="store_true",
        help="Execute the PDF-build in a docker container.",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default="",
        help="Export a pdf. (Path File) name for the output PDF.",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=str,
        default=".",
        help="Output directory to place all generated documents, lists, etc - except temp files.",
    )
    parser.add_argument(
        "-c",
        "--clone-dir",
        type=str,
        default="gitbook_repo",
        help="Directory to clone the repository into.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing clone directory without prompting.",
    )
    parser.add_argument(
        "-q",
        "--temp-dir",
        type=str,
        default="temp",
        help="Directory to place all temp results into.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show progress messages on the console.",
    )
    parser.add_argument(
        "--wrap-wide-tables",
        action="store_true",
        help="Wrap tables wider than a threshold in a landscape environment.",
    )
    parser.add_argument(
        "--disable-longtable",
        action="store_true",
        help="Disable LaTeX longtable output from pandoc.",
    )
    parser.add_argument(
        "--table-threshold",
        type=int,
        default=6,
        help="Number of columns considered wide for --wrap-wide-tables.",
    )
    parser.add_argument(
        "--main-font",
        type=str,
        default="DejaVu Serif",
        help="Main font for the generated PDF.",
    )
    parser.add_argument(
        "--mono-font",
        type=str,
        default="DejaVu Serif",
        help="Mono font for the generated PDF.",
    )
    parser.add_argument(
        "--sans-font",
        type=str,
        default="DejaVu Serif",
        help="Sans font for the generated PDF.",
    )
    parser.add_argument(
        "--emoji-color",
        action="store_true",
        help="Render emojis using a color font instead of monochrome.",
    )
    parser.add_argument(
        "-s", "--export-sources", action="store_true", help="Export sources to CSV."
    )
    parser.add_argument(
        "-l", "--check-links", action="store_true", help="Check for broken HTTP links."
    )
    parser.add_argument(
        "-m", "--markdownlint", action="store_true", help="Run markdownlint."
    )
    parser.add_argument(
        "-i", "--check-images", action="store_true", help="Verify image references."
    )
    parser.add_argument(
        "-r", "--readability", action="store_true", help="Generate readability report."
    )
    parser.add_argument(
        "-d", "--metadata", action="store_true", help="Validate YAML metadata."
    )
    parser.add_argument(
        "-u",
        "--duplicate-headings",
        action="store_true",
        help="Find duplicate headings.",
    )
    parser.add_argument(
        "-a", "--citations", action="store_true", help="Check citation numbering."
    )
    parser.add_argument(
        "-t", "--todos", action="store_true", help="List TODO/FIXME items."
    )
    parser.add_argument(
        "-p", "--spellcheck", action="store_true", help="Run spellchecker."
    )
    parser.add_argument(
        "-E",
        "--emoji-report",
        action="store_true",
        help="Analyze emoji usage and write a markdown report.",
    )
    parser.add_argument(
        "--fix-internal-links",
        action="store_true",
        help="Proof and repair internal GitBook links using SUMMARY.md and generate a report.",
    )
    parser.add_argument(
        "--ai-url",
        type=str,
        default="https://api.openai.com/v1/chat/completions",
        help="URL of the AI API endpoint (default: OpenAI).",
    )
    parser.add_argument(
        "--ai-api-key",
        type=str,
        default="",
        help="API key for the AI service (required for OpenAI and GenAI).",
    )
    parser.add_argument(
        "--ai-provider",
        type=str,
        default="genai",
        help="AI provider (default: OpenAI). Options: 'openai', 'genai'.",
    )
    parser.add_argument(
        "--ai-prompt-reference",
        type=str,
        default="Proof and repair the reference",
        help="Prompt for the AI service (default: 'Proof and repair the reference').",
    )
    parser.add_argument(
        "--fix-external-references",
        action="store_true",
        help="Proof and repair external references using AI.",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 2:  # Exit code 2 indicates an argument parsing error
            error_output = io.StringIO()
            parser.print_usage(file=error_output)
            parser.print_help(file=error_output)
            error_message = error_output.getvalue()
            error_output.close()
            logger.error("Invalid or missing arguments.")
            logger.error("Details:\n%s", error_message)
        sys.exit(e.code)

    # Get the current working directory
    current_dir = os.getcwd()

    # Create out directory if it doesn't exist
    out_dir = args.out_dir
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
    out_dir = os.path.abspath(out_dir)

    # Setup logging
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(out_dir, f"gitbook_worker_{run_timestamp}.log")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
    error_console = logging.StreamHandler()
    error_console.setLevel(logging.ERROR)
    error_console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(error_console)
    if args.verbose:
        info_console = logging.StreamHandler()
        info_console.setLevel(logging.INFO)
        info_console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(info_console)
        logger.info("Logging to %s", log_file)

    # Create temp directory if it doesn't exist
    temp_dir = args.temp_dir
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    temp_dir = os.path.abspath(temp_dir)

    # Clone or update repository
    clone_dir = args.clone_dir  # resolve path
    clone_dir = os.path.abspath(clone_dir)
    clone_or_update_repo(
        args.repo_url,
        clone_dir,
        branch_name=args.branch,
        force=args.force,
    )

    # Parse SUMMARY.md
    summary_path = os.path.join(clone_dir, "SUMMARY.md")
    if not os.path.isfile(summary_path):
        logging.error("SUMMARY.md not found in %s", clone_dir)
        sys.exit(1)
    md_files = parse_summary(summary_path)
    if not md_files:
        logging.error("No markdown files listed in SUMMARY.md")
        sys.exit(1)

    # Combine markdown into one file
    combined_md = os.path.join(temp_dir, f"combined_{run_timestamp}.md")
    logging.info(f"combining gitbook markdowns into one file: %s ...", combined_md)
    try:
        with open(combined_md, "w", encoding="utf-8") as out:
            for md in md_files:
                if os.path.isfile(md):
                    with open(md, encoding="utf-8") as mdf:
                        out.write(mdf.read())
                        out.write("\n\n")
                else:
                    logging.warning("Skipping missing file: %s", md)
    except Exception as e:
        logging.error("Failed to write combined markdown: %s", e)
        sys.exit(1)
    logging.info(f"gitbook markdowns are combined to: %s", combined_md)

    logging.info("Fetching remote images referenced in markdown...")
    img_dir = os.path.join(temp_dir, "images")
    downloaded = download_remote_images(combined_md, img_dir)
    logging.info("Downloaded %s remote images", downloaded)

    # Validate table column consistency before further processing
    logging.info("Validating table columns in combined markdown...")
    table_errors = validate_table_columns(combined_md)
    if table_errors:
        for err in table_errors:
            logging.error(err)
        logging.error("Table column mismatches detected.")
        sys.exit(1)
    logging.info("Table columns validated successfully.")

    logging.info("All markdown files processed successfully.")

    # Build PDF
    if args.pdf:
        pdf_output = args.pdf
        # Remove .pdf extension if present
        if pdf_output.endswith(".pdf"):
            pdf_output = pdf_output[:-4]
        # Add timestamp to output filename
        pdf_output = f"{pdf_output}_{run_timestamp}.pdf"
        # Build PDF with Pandoc
        if args.use_docker:
            # Docker-Workflow
            logging.info("Using Docker to build PDF...")
            ensure_docker_desktop()
            dockerfile_path = os.path.join(
                os.path.dirname(__file__),
                "Dockerfile",
            )
            ensure_docker_image("erda-pandoc", dockerfile_path)
            logging.info("Preparing pandoc header tex file...")
            emoji_font = "OpenMoji Color" if args.emoji_color else "OpenMoji Black"
            try:
                header_file = _write_pandoc_header(
                    temp_dir,
                    emoji_font,
                    args.sans_font,
                    args.mono_font,
                    args.main_font,
                    args.wrap_wide_tables,
                    args.table_threshold,
                    combined_md,
                    disable_longtable=args.disable_longtable,
                )
            except Exception as e:
                logging.error("Failed to write pandoc header tex file: %s", e)
                sys.exit(1)
            wide_tables = False
            if args.wrap_wide_tables:
                try:
                    with open(combined_md, encoding="utf-8") as cf:
                        if "::: {.landscape" in cf.read():
                            logging.info("Wide tables detected in markdown")
                            wide_tables = True
                except Exception as e:
                    logging.error("Failed to inspect markdown for wide tables: %s", e)
            filter_paths = []
            if args.wrap_wide_tables:
                filter_paths.append(
                    os.path.join(os.path.dirname(__file__), "landscape.lua")
                )
            if args.disable_longtable:
                filter_paths.append(
                    os.path.join(os.path.dirname(__file__), "no-longtable.lua")
                )
            if wide_tables and args.wrap_wide_tables:
                logging.info("Converting tables to ltablex via landscape.lua")
            docker_cmd = build_docker_pandoc_cmd(
                out_dir,
                temp_dir,
                clone_dir,
                combined_md,
                pdf_output,
                header_file,
                filter_paths,
            )
            logging.info("Docker command: %s", docker_cmd)
            out, err, code = run_pandoc(docker_cmd)
        else:
            # Non-Docker workflow
            logging.info("Building PDF with Pandoc...")
            filter_paths = []
            if args.wrap_wide_tables:
                filter_paths.append(
                    os.path.join(os.path.dirname(__file__), "landscape.lua")
                )
            if args.disable_longtable:
                filter_paths.append(
                    os.path.join(os.path.dirname(__file__), "no-longtable.lua")
                )
            version = get_pandoc_version()
            logging.info("Detected pandoc version: %s", ".".join(map(str, version)))
            logging.info("Preparing pandoc header tex file...")
            if version >= (3, 1, 12):
                logging.info("Using pandoc mainfontfallback for Segoe UI Emoji")
                try:
                    header_file = _write_pandoc_header(
                        temp_dir,
                        "",
                        args.sans_font,
                        args.mono_font,
                        args.main_font,
                        args.wrap_wide_tables,
                        args.table_threshold,
                        combined_md,
                        write_mainfont=False,
                        disable_longtable=args.disable_longtable,
                    )
                except Exception as e:
                    logging.error("Failed to write pandoc header tex file: %s", e)
                    sys.exit(1)
                extra = [
                    "-V",
                    "mainfontfallback=Segoe UI Emoji:mode=harf",
                    "-V",
                    f"mainfont={args.main_font}",
                    "-V",
                    f"sansfont={args.sans_font}",
                    "-V",
                    f"monofont={args.mono_font}",
                ]
            else:
                logging.info("Using manual Segoe UI Emoji fallback")
                try:
                    header_file = _write_pandoc_header(
                        temp_dir,
                        "Segoe UI Emoji",
                        args.sans_font,
                        args.mono_font,
                        args.main_font,
                        args.wrap_wide_tables,
                        args.table_threshold,
                        combined_md,
                        disable_longtable=args.disable_longtable,
                    )
                except Exception as e:
                    logging.error("Failed to write pandoc header tex file: %s", e)
                    sys.exit(1)
                extra = []
            wide_tables = False
            if args.wrap_wide_tables:
                try:
                    with open(combined_md, encoding="utf-8") as cf:
                        if "::: {.landscape" in cf.read():
                            logging.info("Wide tables detected in markdown")
                            wide_tables = True
                except Exception as e:
                    logging.error("Failed to inspect markdown for wide tables: %s", e)
            if wide_tables and args.wrap_wide_tables:
                logging.info("Converting tables to ltablex via landscape.lua")
            pandoc_cmd = build_pandoc_cmd(
                combined_md,
                pdf_output,
                clone_dir,
                header_file,
                filter_paths,
                extra,
            )
            out, err, code = run_pandoc(pandoc_cmd)
        if out:
            logging.info("Pandoc stdout:\n%s", out)
        if err:
            logging.warning("Pandoc stderr:\n%s", err)
        if code != 0:
            logging.error("Pandoc failed with exit code %s", code)
            log_file = os.path.join(out_dir, f"pandoc_error_{run_timestamp}.log")
            with open(log_file, "w", encoding="utf-8") as lf:
                lf.write(err)
            logging.error("Pandoc errors logged to %s", log_file)
            sys.exit(code)
        logging.info("PDF generated: %s", pdf_output)

    # Run quality checks based on flags
    if args.export_sources:
        logging.info("export-sources started")
        try:
            extract_sources(
                md_files,
                os.path.join(current_dir, f"sources_{run_timestamp}.csv"),
            )
            logging.info("export-sources done")
        except Exception as e:
            logging.error("export-sources failed: %s", e)
            logger.error("Error exporting sources: %s", e)
    if args.check_links:
        logging.info("check-links started")
        try:
            check_links(
                md_files,
                os.path.join(current_dir, f"report_check_links_{run_timestamp}.csv"),
            )
            logging.info("check-links done")
        except Exception as e:
            logging.error("check-links failed: %s", e)
            logger.error("Error checking links: %s", e)
    if args.markdownlint:
        logging.info("markdownlint started")
        try:
            lint_out, _ = lint_markdown(clone_dir)
            logger.info(lint_out)
            logging.info("markdownlint done")
        except Exception as e:
            logging.error("markdownlint failed: %s", e)
            logger.error("Error running markdownlint: %s", e)
    if args.check_images:
        logging.info("check-images started")
        try:
            missing_imgs = check_images(md_files)
            for mi in missing_imgs:
                logger.info("Missing image: %s", mi)
            logging.info("check-images done")
        except Exception as e:
            logging.error("check-images failed: %s", e)
            logger.error("Error checking images: %s", e)
    if args.readability:
        logging.info("readability started")
        try:
            scores = readability_report(md_files)
            for sc in scores:
                logger.info("Readability: %s", sc)
            logging.info("readability done")
        except Exception as e:
            logging.error("readability failed: %s", e)
            logger.error("Error generating readability report: %s", e)
    if args.metadata:
        logging.info("metadata started")
        try:
            meta_issues = validate_metadata(md_files)
            for mi in meta_issues:
                logger.info("Metadata issue: %s", mi)
            logging.info("metadata done")
        except Exception as e:
            logging.error("metadata failed: %s", e)
            logger.error("Error validating metadata: %s", e)
    if args.duplicate_headings:
        logging.info("duplicate-headings started")
        try:
            duplicates = check_duplicate_headings(md_files)
            for dup in duplicates:
                logger.info("Duplicate heading: %s", dup)
            logging.info("duplicate-headings done")
        except Exception as e:
            logging.error("duplicate-headings failed: %s", e)
            logger.error("Error checking duplicate headings: %s", e)
    if args.citations:
        logging.info("citations started")
        try:
            citation_gaps = check_citation_numbering(md_files)
            for gap in citation_gaps:
                logger.info("Citation gaps: %s", gap)
            logging.info("citations done")
        except Exception as e:
            logging.error("citations failed: %s", e)
            logger.error("Error checking citations: %s", e)
    if args.todos:
        logging.info("todos started")
        try:
            todos = list_todos(md_files)
            for todo in todos:
                logger.info("TODO/FIXME: %s", todo)
            logging.info("todos done")
        except Exception as e:
            logging.error("todos failed: %s", e)
            logger.error("Error listing TODOs: %s", e)
    if args.spellcheck:
        logging.info("spellcheck started")
        try:
            spell_out, _ = spellcheck(clone_dir)
            logger.info(spell_out)
            logging.info("spellcheck done")
        except Exception as e:
            logging.error("spellcheck failed: %s", e)
            logger.error("Error running spellcheck: %s", e)
    if args.emoji_report:
        logging.info("emoji-report started")
        try:
            counts, table_md = emoji_report(combined_md)
            for name, count in counts.items():
                logger.info("Emoji %s: %s", name, count)
            report_filename = os.path.join(out_dir, f"emoji_report_{run_timestamp}.md")
            with open(report_filename, "w", encoding="utf-8") as rf:
                rf.write("# Emoji Report\n\n")
                rf.write(table_md + "\n")
            logger.info("Emoji report written to %s", report_filename)
            logging.info("emoji-report done")
        except Exception as e:
            logging.error("emoji-report failed: %s", e)
            logger.error("Error generating emoji report: %s", e)
    if args.fix_internal_links:
        logging.info("fix-internal-links started")
        try:
            summary_md = os.path.join(clone_dir, "SUMMARY.md")
            if not os.path.isfile(summary_md):
                raise FileNotFoundError(f"SUMMARY.md not found at {summary_md}")
            report = proof_and_repair_internal_references(md_files, summary_md)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = os.path.join(
                out_dir, f"internal_link_proof_and_repair_report_{timestamp}.md"
            )
            with open(report_filename, "w", encoding="utf-8") as rf:
                rf.write(
                    f"# Internal Link Proof and Repair Report\nGenerated: {datetime.now().isoformat()}\n\n"
                )
                for e in report:
                    rf.write(f"- Action: {e['action']}\n")
                    if "file" in e:
                        rf.write(f"  - File: {e['file']}\n")
                    if "target" in e:
                        rf.write(f"  - Target: {e['target']}\n")
                    if "title" in e:
                        rf.write(f"  - Title: {e['title']}\n")
                    if "link" in e:
                        rf.write(f"  - Link: {e['link']}\n")
                    if "index" in e:
                        rf.write(f"  - Index: {e['index']}\n")
                    if "orig" in e:
                        rf.write(f"  - Original: {e['orig']}\n")
                    if "new" in e:
                        rf.write(f"  - New: {e['new']}\n")
                    rf.write("\n")
            logger.info("Report generated: %s", report_filename)
            logging.info(
                "Internal link proof and repair report generated: %s", report_filename
            )
            logging.info("fix-internal-links done")
        except Exception as e:
            logging.error("fix-internal-links failed: %s", e)
            logger.error("Error fixing internal links: %s", e)
    if args.fix_external_references:
        logging.info("fix-external-references started")
        try:
            report = proof_and_repair_external_references(
                md_files,
                prompt=args.ai_prompt_reference,
                ai_url=args.ai_url,
                ai_api_key=args.ai_api_key,
                ai_provider=args.ai_provider,
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = os.path.join(
                out_dir, f"external_reference_proof_and_repair_report_{timestamp}.md"
            )
            with open(report_filename, "w", encoding="utf-8") as rf:
                rf.write(
                    f"# External Reference Proof and Repair Report\nGenerated: {datetime.now().isoformat()}\n\n"
                )
                for e in report:
                    rf.write(f"- Action: {e['action']}\n")
                    rf.write(f"  - File: {e['file']}\n")
                    rf.write(f"  - Line Number: {e['lineno']}\n")
                    if "orig" in e:
                        rf.write(f"  - Original: {e['orig']}\n")
                    if "error" in e:
                        rf.write(f"  - Error: {e['error']}\n")
                    if "new" in e:
                        rf.write(f"  - New: {e['new']}\n")
                    rf.write("\n")
            logger.info("Report generated: %s", report_filename)
            logging.info(
                "External reference proof and repair report generated: %s",
                report_filename,
            )
            logging.info("fix-external-references done")
        except Exception as e:
            logging.error("fix-external-references failed: %s", e)
            logger.error("Error fixing external references: %s", e)

    logging.info("All quality checks completed.")


if __name__ == "__main__":
    main()

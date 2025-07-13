import csv
import logging
import os
import re
from typing import List

import requests
import tqdm


def check_links(md_files: List[str], report_csv: str):
    """Check HTTP links in markdown files and write a CSV report."""
    try:
        with open(report_csv, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["GO", "File", "Link", "Line#", "Line", "Status Code", "Error"])
            broken = []
            good = []
            link_pattern = re.compile(r"\[.*?\]\((https?://[^)]+)\)")
            logging.info("Starting external link check...")
            for md in tqdm.tqdm(md_files, desc=" Files", unit=" File"):
                try:
                    with open(md, encoding="utf-8") as f:
                        for lineno, line in enumerate(f, 1):
                            for url in link_pattern.findall(line):
                                finding = None
                                try:
                                    response = requests.head(url, timeout=5)
                                    if response.status_code >= 400:
                                        finding = ("❌", md, url, lineno, line, response.status_code, response.reason)
                                    else:
                                        g_finding = ("✅", md, url, lineno, line, response.status_code, "OK")
                                        good.append(g_finding)
                                        writer.writerow(g_finding)
                                        logging.info("✅ Good link found in %s: %s (Line %s)", md, url, lineno)
                                except Exception as e:
                                    finding = ("💥❌", md, url, lineno, line, "unknown", str(e))
                                if finding:
                                    broken.append(finding)
                                    writer.writerow(finding)
                                    logging.info("❌ Broken link found in %s: %s (Line %s)", md, url, lineno)
                except Exception as e:
                    logging.warning("Failed to open %s for link check: %s", md, e)
            logging.info("--- Final Report: %s broken links, %s good links ---", len(broken), len(good))
    except Exception as e:
        logging.error("Failed to check links and write report to CSV: %s", e)
        raise


def check_images(md_files: List[str]):
    """Check if images (local or remote) referenced in markdown exist."""
    missing = []
    img_pattern = re.compile(r"!\[.*?\]\((.*?)\)")
    for md in md_files:
        try:
            with open(md, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    for path in img_pattern.findall(line):
                        if path.startswith("http"):
                            try:
                                response = requests.head(path, timeout=5)
                                if response.status_code >= 400:
                                    missing.append((md, lineno, path, response.status_code))
                            except Exception as e:
                                missing.append((md, lineno, path, str(e)))
                        else:
                            full_path = os.path.join(os.path.dirname(md), path)
                            if not os.path.exists(full_path):
                                missing.append((md, lineno, full_path, "Not found"))
        except Exception as e:
            logging.warning("Failed to open %s for image check: %s", md, e)
    return missing


def check_duplicate_headings(md_files: List[str]):
    """Detect duplicate headings across markdown files."""
    seen = {}
    duplicates = []
    header_pattern = re.compile(r"^(#{1,6})\s*(.+)")
    for md in md_files:
        try:
            with open(md, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    match = header_pattern.match(line)
                    if match:
                        title = match.group(2).strip().lower()
                        ref = f"{md}:{lineno}"
                        if title in seen:
                            duplicates.append((md, lineno, title, seen[title]))
                        else:
                            seen[title] = ref
        except Exception as e:
            logging.warning("Failed to open %s for heading check: %s", md, e)
    return duplicates


def check_citation_numbering(md_files: List[str]):
    """Ensure numbered citations run consecutively without gaps."""
    gaps = []
    num_pattern = re.compile(r"^\s*([0-9]+)\.\s")
    for md in md_files:
        nums = []
        try:
            with open(md, encoding="utf-8") as f:
                for line in f:
                    match = num_pattern.match(line)
                    if match:
                        nums.append(int(match.group(1)))
            if nums:
                expected = set(range(1, max(nums) + 1))
                missing = expected - set(nums)
                if missing:
                    gaps.append((md, sorted(missing)))
        except Exception as e:
            logging.warning("Failed to open %s for citation check: %s", md, e)
    return gaps


def list_todos(md_files: List[str]):
    """List all TODO and FIXME comments in markdown files."""
    todos = []
    markers = re.compile(r"\b(TODO|FIXME)\b")
    for md in md_files:
        try:
            with open(md, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if markers.search(line):
                        todos.append((md, lineno, line.strip()))
        except Exception as e:
            logging.warning("Failed to open %s for TODO check: %s", md, e)
    return todos

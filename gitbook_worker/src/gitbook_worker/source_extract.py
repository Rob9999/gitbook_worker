import csv
import logging
import os
import re
from typing import Any, Dict, List


def get_extract_multiline_list_items_pattern() -> re.Pattern:
    """Return regex pattern to extract multiline list items."""
    return re.compile(
        r"^(?:\s*)(?:\d+[\.\)-]|[a-zA-Z][\.\)-]|[*\-+])\s+.*(?:\n(?!\s*(?:\d+[\.\)-]|[a-zA-Z][\.\)-]|[*\-+])\s).*)*",
        re.MULTILINE,
    )


def extract_multiline_list_items(text: str) -> List[str]:
    pattern = get_extract_multiline_list_items_pattern()
    if not isinstance(text, str):
        raise ValueError("Input text must be a string.")
    return pattern.findall(text)


def get_language_dependent_header_pattern_for_sources(
    language: str = "de", max_level: int = 6
) -> re.Pattern:
    """Return a regex that matches source section headers like '# 1.1 Quellen', '### 2. Quelle', etc."""
    lang = (language or "").lower()
    patterns = {
        "de": ["Quelle", "Quellen", "Quellen & Verweise", "Quellen und Verweise"],
        "en": ["Source", "Sources", "References", "Sources & References"],
    }

    # Alle Begriffe sammeln + Duplikate entfernen
    words = patterns.get(lang, []) + patterns["de"] + patterns["en"]
    seen = set()
    words = [w for w in words if not (w in seen or seen.add(w))]

    # Escape für Regex
    regex = "|".join(re.escape(w) for w in words)

    # Regex für dezimale Nummerierungen vor dem Quellenbegriff
    numbering = r"(?:\d+(?:\.\d+)*\.?)?"

    # Kompilieren
    return re.compile(
        rf"^(#{{1,{max_level}}})\s*{numbering}\s*(?:{regex})",
        re.IGNORECASE,
    )


def extract_sources_of_a_md_file_to_dict(
    md_file: str,
) -> Dict[str, List[Dict[str, Dict[str, Any]]]]:
    sources: Dict[str, List[Dict[str, Dict[str, Any]]]] = {}
    header_pattern = get_language_dependent_header_pattern_for_sources()
    list_pattern = get_extract_multiline_list_items_pattern()
    if md_file:
        try:
            with open(md_file, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logging.warning("Cannot open %s: %s", md_file, e)
            return {}
        in_section = False
        level = None
        sources[str(md_file)] = []
        for lineno, line in enumerate(lines, 1):
            header = header_pattern.match(line)
            if header:
                in_section = True
                level = len(header.group(1))
                continue
            if in_section and line.startswith("#"):
                current = len(line) - len(line.lstrip("#"))
                if current <= level:
                    break
            if in_section and list_pattern.match(line):
                entry = {
                    "numbering": None,
                    "link": None,
                    "comment": None,
                    "lineno": lineno,
                    "line": line.strip(),
                    "kind": "external",
                }
                match = list_pattern.match(line)
                if match:
                    entry["numbering"] = match.group(0).strip()
                name_match = re.search(r"^\s*([0-9a-z\*]+[\.) ]|[-*+])\s+(.*)", line)
                if name_match:
                    name = name_match.group(2).strip()
                    name = re.sub(r"^[0-9a-z\*]+[\.) ]\s*", "", name)
                    name = re.sub(r'^"(.*)"$', r"\1", name)
                    name = re.sub(r"\[.*?\]\(.*?\)", "", name).strip()
                else:
                    name = ""
                link_match = re.search(r"\[.*?\]\((.*?)\)", line)
                if link_match:
                    entry["link"] = link_match.group(1)
                if link_match and not name:
                    name = link_match.group(0).split("]")[0].strip()
                comment_match = re.search(r"\((.*?)\)", line)
                if comment_match:
                    entry["comment"] = comment_match.group(1)
                if not name:
                    name = "Referenz zu Zeile " + str(lineno)
                sources[str(md_file)].append({name: entry})
    return sources


def extract_sources_to_dict(
    md_files: List[str],
) -> Dict[str, List[Dict[str, Dict[str, Any]]]]:
    sources: Dict[str, List[Dict[str, Dict[str, Any]]]] = {}
    for md in md_files:
        if not os.path.isfile(md):
            logging.warning("Skipping missing file: %s", md)
            continue
        src = extract_sources_of_a_md_file_to_dict(md)
        tag = str(md)
        if tag in sources:
            if isinstance(sources[tag], list):
                sources[tag].append(src[tag])
            else:
                sources[tag] = src[tag]
        else:
            sources[tag] = src[tag]
    return sources


def extract_sources(md_files: List[str], output_csv: str) -> None:
    sources = extract_sources_to_dict(md_files)
    if not sources:
        logging.warning("No sources found in markdown files.")
        return
    try:
        with open(output_csv, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "File",
                    "Name",
                    "Link",
                    "Numbering",
                    "Comment",
                    "Kind",
                    "LineNo",
                    "Line",
                ]
            )
            for md_file, entries in sources.items():
                for entry in entries:
                    for name, reference in entry.items():
                        if not reference:
                            continue
                        name = re.sub(r"^[0-9a-z\*]+[\.) ]\s*", "", name)
                        writer.writerow(
                            [
                                md_file,
                                name,
                                reference.get("link", ""),
                                reference.get("numbering", ""),
                                reference.get("comment", ""),
                                reference.get("kind", ""),
                                reference.get("lineno", ""),
                                reference.get("line", ""),
                            ]
                        )
        logging.info("Sources extracted to %s", output_csv)
    except Exception as e:
        logging.error("Failed to write sources CSV: %s", e)
        raise

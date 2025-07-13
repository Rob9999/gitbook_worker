import ast
import json
import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Tuple

import tqdm

import requests

from .source_extract import extract_sources_of_a_md_file_to_dict


def extract_json_from_ai_output(generated_text: str) -> Tuple[bool, Any]:
    text = generated_text.strip()
    if text.startswith("```json"):
        text = text[7:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    text = text.strip().strip("'").strip('"')
    try:
        return True, json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        unescaped = ast.literal_eval(text)
        unescaped = ast.literal_eval(unescaped)
        return True, json.loads(unescaped)
    except Exception:
        logging.warning("JSON parsing failed for AI response. Returning raw text.")
    return False, generated_text


def ask_ai(prompt: str, ai_url: str, ai_api_key: str, ai_provider: str, retry_count: int = 0, max_retries: int = 3) -> Tuple[bool, str]:
    headers = {"Authorization": f"Bearer {ai_api_key}", "Content-Type": "application/json"}
    if ai_provider.lower() == "openai":
        payload = {"model": "gpt-4", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
        try:
            response = requests.post(ai_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return True, result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return False, f"[OpenAI] Fehler: {e}"
    elif ai_provider.lower() == "genai":
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        url_with_key = f"{ai_url}?key={ai_api_key}"
        try:
            response = requests.post(url_with_key, headers={"Content-Type": "application/json"}, json=payload)
            response.raise_for_status()
            result = response.json()
            generated_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            return extract_json_from_ai_output(generated_text)
        except requests.exceptions.RequestException as e:
            if getattr(e.response, 'status_code', None) == 429 and retry_count < max_retries:
                wait_time = random.randint(1, 8)
                logging.warning("[GenAI] Zu viele Anfragen. Warte %s Sekunden", wait_time)
                time.sleep(wait_time)
                return ask_ai(prompt, ai_url, ai_api_key, ai_provider, retry_count + 1)
            return False, f"[GenAI] Fehler: {e}"
        except Exception as e:
            return False, f"[GenAI] Fehler: {e}"
    else:
        return False, f"Unbekannter AI-Provider: '{ai_provider}'"


def proof_and_repair_internal_references(md_files: List[str], summary_md: str) -> List[Dict[str, Any]]:
    summary_map = {}
    link_re = re.compile(r"\*+\s*\[(?P<title>[^\]]+)\]\((?P<link>[^)]+\.md)\)")
    with open(summary_md, encoding="utf-8") as sf:
        for line in sf:
            m = link_re.search(line)
            if m:
                summary_map[m.group("title")] = m.group("link")

    report = []
    for file in md_files:
        sources = extract_sources_of_a_md_file_to_dict(file).get(str(file), [])
        if not sources:
            continue
        with open(file, encoding="utf-8") as f:
            lines = f.read().splitlines()
        for entry in sources:
            for name, ref in entry.items():
                idx = ref.get("lineno", 1) - 1
                if idx < len(lines):
                    lines.insert(idx, name)
                else:
                    lines.append(name)
        with open(file, "w", encoding="utf-8") as wf:
            wf.write("\n".join(lines) + "\n")
        report.append({"action": "footnote_added", "file": file})
    return report


def proof_and_repair_external_reference(
    reference_as_line: str,
    footnote_index: int,
    prompt: str,
    ai_url: str,
    ai_api_key: str,
    ai_provider: str,
) -> Tuple[bool, str]:
    """Send a prompt for a single reference to the chosen AI service.

    The AI should validate and, if necessary, correct the citation.  The
    response is expected to be a JSON string matching ``json_hint`` below.
    """

    structured_schema = """
    {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Zitationspr\u00fcfungsergebnis",
  "type": "object",
  "properties": {
    "success": {
      "type": "boolean",
      "description": "Ob die Zitation erfolgreich validiert und ggf. korrigiert wurde"
    },
    "org": {
      "type": "string",
      "description": "Die original eingegebene (ungepr\u00fcfte) Quellenangabe"
    },
    "new": {
      "type": "string",
      "description": "Die neue, wissenschaftlich korrekte Zitationszeile im gew\u00fcnschten Format (optional)",
      "nullable": true
    },
    "error": {
      "type": "string",
      "description": "Fehlermeldung, falls die Zitation nicht erstellt werden konnte (optional)",
      "nullable": true
    },
    "hint": {
      "type": "string",
      "description": "Hilfestellung zur Verbesserung oder Vervollst\u00e4ndigung der Quelle (optional)",
      "nullable": true
    },
    "validation_date": {
      "type": "string",
      "format": "date",
      "description": "Das Datum der Pr\u00fcfung und ggf. der URL-Validierung (today)"
    },
    "type": {
      "type": "string",
      "description": "Kategorisierung der Quelle: 'internal reference', 'external url', 'external reference' oder '?'",
      "enum": ["internal reference", "external url", "external reference", "?"]
    }
  },
  "required": ["success", "org", "validation_date", "type"]
}
    """

    json_hint = """
    {
        "success": true|false,
        "org": "<Originalquelle>",
        "new": "<neue Zitationszeile oder null>",
        "error": "<Fehlermeldung oder null>",
        "hint": "<Hinweis oder null>",
        "validation_date": "YYYY-MM-DD",
        "type": "internal reference" | "external url" | "external reference" | "?"
    }
    """

    full_prompt = (
        f"{prompt}\n\nQuelle [{footnote_index}]: {reference_as_line}\n\n\n\n"
        f"Generate a structured JSON according:\n{json_hint}"
    )

    return ask_ai(full_prompt, ai_url, ai_api_key, ai_provider)


def proof_and_repair_external_references(
    md_files: List[str], prompt: str, ai_url: str, ai_api_key: str, ai_provider: str
) -> List[Dict[str, Any]]:
    """Proof and repair external references in markdown files."""

    report = []
    block_start = None
    block_end = None
    block_level = None

    for file in tqdm.tqdm(md_files, desc="\uf709 Files", unit=" File"):
        existing_sources = extract_sources_of_a_md_file_to_dict(file)
        repaired_references = []

        if existing_sources:
            for _, entries in existing_sources.items():
                if not entries:
                    continue
                for entry in entries:
                    for name, reference in entry.items():
                        if not reference:
                            continue

                        block_start = (
                            min(block_start, reference.get("lineno")) if block_start else reference.get("lineno")
                        )
                        block_end = (
                            max(block_end, reference.get("lineno")) if block_end else reference.get("lineno")
                        )
                        block_level = reference.get("level")

                        try:
                            numbering = reference.get("numbering", "").strip()
                            if numbering.isdigit():
                                footnote_index = int(numbering)
                            else:
                                match = re.match(r"(\d+)", numbering)
                                footnote_index = int(match.group(1)) if match else -1
                        except Exception:
                            footnote_index = -1

                        success, result = proof_and_repair_external_reference(
                            reference_as_line=reference.get("line"),
                            footnote_index=footnote_index,
                            prompt=prompt,
                            ai_url=ai_url,
                            ai_api_key=ai_api_key,
                            ai_provider=ai_provider,
                        )

                        has_json = isinstance(result, dict)
                        repaired_references.append(
                            {
                                "line": reference.get("line"),
                                "lineno": reference.get("lineno"),
                                "success": success and has_json and result.get("success"),
                                "new": result.get("new") if has_json else None,
                                "error": result.get("error") if has_json else f"ai response data error: {result}",
                                "hint": result.get("hint") if has_json else "repair prompt, details in error",
                                "validation_date": result.get("validation_date") if has_json else None,
                                "type": result.get("type") if has_json else None,
                            }
                        )

            with open(file, encoding="utf-8") as rf:
                lines = rf.readlines()

            for repaired_reference in repaired_references:
                if repaired_reference["success"] and repaired_reference["new"]:
                    lineno = repaired_reference["lineno"]
                    lines[lineno - 1] = (
                        lines[lineno - 1].replace(
                            repaired_reference["line"], repaired_reference["new"]
                        )
                        + "\n"
                    )
                    report.append(
                        {
                            "action": "link_repaired",
                            "file": file,
                            "lineno": repaired_reference["lineno"],
                            "orig": repaired_reference["line"],
                            "new": repaired_reference["new"],
                            "validation_date": repaired_reference["validation_date"],
                            "type": repaired_reference["type"],
                            "hint": repaired_reference["hint"],
                        }
                    )
                    logging.info(
                        "Repaired reference: %s -> %s, file: %s",
                        repaired_reference["line"],
                        repaired_reference["new"],
                        file,
                    )
                elif repaired_reference["success"]:
                    report.append(
                        {
                            "action": "link_check_succeeded",
                            "file": file,
                            "lineno": repaired_reference["lineno"],
                            "orig": repaired_reference["line"],
                            "validation_date": repaired_reference["validation_date"],
                            "type": repaired_reference["type"],
                            "hint": repaired_reference["hint"],
                        }
                    )
                    logging.info(
                        "Reference already ok: %s, file: %s",
                        repaired_reference["line"],
                        file,
                    )
                else:
                    report.append(
                        {
                            "action": "link_repair_failed",
                            "file": file,
                            "lineno": repaired_reference["lineno"],
                            "orig": repaired_reference["line"],
                            "error": repaired_reference["error"],
                            "validation_date": repaired_reference["validation_date"],
                            "type": repaired_reference["type"],
                            "hint": repaired_reference["hint"],
                        }
                    )
                    logging.warning(
                        "Failed to repair reference: %s, file: %s, error: %s",
                        repaired_reference["line"],
                        file,
                        repaired_reference["error"],
                    )

            with open(file, "w", encoding="utf-8") as wf:
                wf.writelines(lines)
    return report

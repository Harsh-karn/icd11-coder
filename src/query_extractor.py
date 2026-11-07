"""Conservative explicit-negation handling; not a clinical NLP parser."""
import re

WORD = r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ-]*"
NEGATION = re.compile(
    rf"\b(?:no evidence of|no history of|negative for|denies|without)\s+({WORD}(?:\s+{WORD}){{0,2}})(?=[,;.!\n]|$)"
    rf"|\b({WORD})\s+(?:excluded|ruled out|unlikely)\b", re.I)

def excluded_terms(text):
    return {" ".join((match.group(1) or match.group(2)).lower().split())
            for match in NEGATION.finditer(text)}

def extract_diagnostic_query(text):
    clean = NEGATION.sub(" ", text)
    # Explicit diagnosis takes priority over symptoms, tests and treatment.
    sections = re.findall(
        r"(?:\b(?:Dx|Diagnosis|Diagnostic|Diagnóstico|Assessment|Impression)|(?:^|\n)A)\s*[:.-]\s*([^\n;]+)",
        clean, re.I)
    if sections:
        return " ".join(sections + sections)
    return clean

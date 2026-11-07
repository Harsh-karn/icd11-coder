import re

# Negation patterns to down-weight ruled-out conditions
NEGATION_PATTERNS = [
    re.compile(r"(\b[a-zA-Z\s]+?)\s+(?:excluded|ruled\s+out|neg|negative|unlikely)\b", re.IGNORECASE),
    re.compile(r"\b(?:no\s+evidence\s+of|negative\s+for|rules\s+out|not)\s+([a-zA-Z\s]+)", re.IGNORECASE),
]

def extract_diagnostic_query(text: str) -> str:
    """Extract the primary diagnostic focus from a clinical note."""
    lines = text.split("\n")
    diag_lines = []
    
    # 1. Direct Assessment / Impression / Diagnosis fields
    for line in lines:
        l = line.strip()
        if re.match(r"^(?:A|Dx|Assessment|Impression|Diag)\s*[:\-\.]", l, re.IGNORECASE):
            diag_lines.append(l)
        elif "Dx:" in l or "dx:" in l or "Dx " in l or "A:" in l:
            diag_lines.append(l)

    # 2. Key doctor statements in ambient consultations
    for line in lines:
        l = line.strip()
        if l.lower().startswith("doctor:"):
            # Check for conclusive clinical statements
            if any(k in l.lower() for k in [
                "this is", "have an", "diagnosed with", "sounds like", "attack",
                "malaria", "pneumonia", "asthma", "bronchitis", "tonsillitis",
                "chickenpox", "shingles", "measles", "gastroenteritis", "infection",
                "abscess", "ulcer", "fracture", "hypertension", "diabetes", "nebs", "inhaler"
            ]):
                diag_lines.append(l)

    if diag_lines:
        # Give higher weight to diagnosis lines by repeating them
        combined = " ".join(diag_lines) + " " + " ".join(diag_lines) + " " + text
        return combined

    return text

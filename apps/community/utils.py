import re


def format_clean_name(name: str) -> str:
    """Format student full name to ensure clean spacing, proper capitalization, and readable layout.

    Fixes names without spaces (e.g. 'Ameenulhashimh', 'Anshadrazikp', 'ArjunRadhakrishnan').
    """
    if not name:
        return ""

    s = name.strip()

    # Insert space before inner uppercase letters: "ArjunRadhakrishnan" -> "Arjun Radhakrishnan"
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)

    # Handle dot separators: "Minshida.p" -> "Minshida P"
    if "." in s:
        s = s.replace(".", " ")

    # Normalize multiple spaces
    parts = [p for p in s.split() if p]

    # Re-assemble & capitalize each word cleanly
    formatted_parts = []
    for p in parts:
        if len(p) <= 3 and p.isupper():
            formatted_parts.append(p)
        else:
            formatted_parts.append(p.capitalize())

    return " ".join(formatted_parts)

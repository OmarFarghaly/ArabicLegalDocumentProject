from bidi.algorithm import get_display


def fix_arabic(text: str) -> str:
    if not text:
        return ""

    fixed_lines = []

    for line in text.splitlines():
        fixed_lines.append(get_display(line))

    return "\n".join(fixed_lines).strip()
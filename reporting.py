from collections import defaultdict


def _contact(username: str | None, phone: str | None) -> str:
    if phone:
        return phone
    if username:
        return f"@{username}"
    return ""


def build_missing_report_all(rows: list[tuple[str, str, str | None, str | None]]) -> str:
    if not rows:
        return "Все курсанты доложили."

    groups: dict[str, list[tuple[str, str | None, str | None]]] = defaultdict(list)
    for group_code, full_name, username, phone in rows:
        groups[group_code].append((full_name, username, phone))

    lines = ["Неотметившиеся курсанты", ""]
    total = 0
    for group_code in sorted(groups.keys()):
        lines.append(f"{group_code} учебная группа:")
        for i, (name, username, phone) in enumerate(groups[group_code], start=1):
            c = _contact(username, phone)
            lines.append(f"{i}. {name}" + (f" ({c})" if c else ""))
        lines.append("")
        total += len(groups[group_code])

    lines.append(f"Всего неотметившихся: {total}")
    return "\n".join(lines)


def build_missing_report_one_group(group_code: str, rows: list[tuple[str, str | None, str | None]]) -> str:
    lines = ["Неотметившиеся курсанты", "", f"{group_code} учебная группа:"]
    for i, (name, username, phone) in enumerate(rows, start=1):
        c = _contact(username, phone)
        lines.append(f"{i}. {name}" + (f" ({c})" if c else ""))
    lines.append("")
    lines.append(f"Всего неотметившихся: {len(rows)}")
    return "\n".join(lines)

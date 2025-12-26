from collections import defaultdict

def build_missing_report_all(rows: list[tuple[str, str]]) -> str:
    if not rows:
        return "Неотметившиеся курсанты\n\nВсе отметились.\n\nВсего неотметившихся: 0"

    groups = defaultdict(list)
    for group_code, full_name in rows:
        groups[group_code].append(full_name)

    lines = ["Неотметившиеся курсанты", ""]
    total = 0
    for group_code in sorted(groups.keys()):
        lines.append(f"{group_code} учебная группа:")
        for i, name in enumerate(groups[group_code], start=1):
            lines.append(f"{i}. {name}")
        lines.append("")
        total += len(groups[group_code])

    lines.append(f"Всего неотметившихся: {total}")
    return "\n".join(lines)

def build_missing_report_one_group(group_code: str, names: list[str]) -> str:
    lines = ["Неотметившиеся курсанты", "", f"{group_code} учебная группа:"]
    for i, name in enumerate(names, start=1):
        lines.append(f"{i}. {name}")
    lines.append("")
    lines.append(f"Всего неотметившихся: {len(names)}")
    return "\n".join(lines)

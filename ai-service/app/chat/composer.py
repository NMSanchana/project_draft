"""Compose plain-text answers. Every number comes from the executor / ML module output, never from an LLM.

The ChatWidget renders plain text, so: no markdown, no tables, at most ~6 short lines.
"""

from __future__ import annotations

import re

from .executor import ExecResult

MAX_LINES = 6
MAX_LINE = 320


def fmt(value: float | None, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "money":
        return f"${value:,.2f}"
    if kind == "pct":
        return f"{value:,.1f}%"
    return f"{value:,.0f}"


def plain(text: str) -> str:
    """Strip markdown/HTML artefacts and enforce the line/length caps."""
    t = re.sub(r"```.*?```", "", text, flags=re.S)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"(\*\*|__|`|^#{1,6}\s*)", "", t, flags=re.M)
    t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.M)
    lines = [re.sub(r"\s*\|\s*", " ", ln).strip() for ln in t.splitlines() if ln.strip() and not re.fullmatch(r"[\s|:-]+", ln)]
    lines = [ln if len(ln) <= MAX_LINE else ln[: MAX_LINE - 1].rstrip() + "…" for ln in lines]
    if len(lines) > MAX_LINES:
        lines = lines[: MAX_LINES - 1] + [lines[MAX_LINES - 1]]
    return "\n".join(lines)


def data_answer(res: ExecResult) -> str:
    if not res.ok:
        return res.error or "I couldn't calculate that."
    p, label, kind = res.plan, res.label, res.kind
    scope = f" for {res.scope}" if res.scope and not res.scope.startswith("in ") else (f" {res.scope}" if res.scope else "")
    cap = label[0].upper() + label[1:]
    if p.operation == "compare":
        d = res.detail
        diff = (res.value or 0) - (res.previous or 0)
        pct = f" ({100 * diff / res.previous:+.1f}%)" if res.previous else ""
        sign = "+" if diff >= 0 else "-"
        diff_txt = f"{sign}{fmt(abs(diff), kind)}" if kind != "pct" else f"{diff:+.1f} points"
        who = ", ".join(f.value for f in p.filters)
        who = f" for {who}" if who else ""
        return (
            f"{cap}{who}: {d['current_label']} {fmt(res.value, kind)} vs {d['previous_label']} {fmt(res.previous, kind)}.\n"
            f"Change: {diff_txt}{pct if kind != 'pct' else ''}."
        )
    if res.rows:
        by = p.group_by
        n = len(res.rows)
        if by in ("month", "week", "day", "weekday"):
            shown = res.rows if n <= 8 else res.rows[-8:]
            head = f"{cap} by {by}{scope}" + (f" (last 8 of {n})" if n > 8 else "") + ":"
            peak = max(res.rows, key=lambda r: r["value"])
            return (
                head
                + "\n"
                + ", ".join(f"{r['label']} {fmt(r['value'], kind)}" for r in shown)
                + f".\nPeak: {peak['label']} ({fmt(peak['value'], kind)})."
            )
        total = res.detail.get("groups_total", n)
        order = "lowest" if p.sort == "asc" else "top"
        head = f"{cap} by {by}{scope} ({order} {n}" + (f" of {total}" if total > n else "") + "):"
        lines = [f"{i}. {r['label']}: {fmt(r['value'], kind)}" for i, r in enumerate(res.rows[:5], 1)]
        if n > 5:
            lines.append(f"...and {n - 5} more.")
        return head + "\n" + "\n".join(lines)
    return f"{cap}{scope}: {fmt(res.value, kind)}."

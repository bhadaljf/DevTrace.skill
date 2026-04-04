from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "assets" / "templates"
KNOWN_CURRENT_SECTIONS = ["当前主线", "当前问题", "当前 blocker", "下一步", "最近变化"]
DEFAULT_SESSION_STATUSES = ["active", "blocked", "confirmed"]
IMPORTANCE_RANK = {"high": 3, "medium": 2, "low": 1}
STATUS_RANK = {
    "blocked": 5,
    "active": 4,
    "confirmed": 4,
    "done": 3,
    "candidate": 2,
    "superseded": 0,
}
STOPWORD_TOKENS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "have",
    "has",
    "will",
    "继续",
    "当前",
    "后续",
    "准备",
    "这个",
    "那个",
    "然后",
    "需要",
    "已经",
    "问题",
    "事件",
    "系统",
    "项目",
    "模块",
    "方案",
}
CONTINUATION_HINTS = [
    "继续",
    "延续",
    "沿着",
    "跟进",
    "承接",
    "接着",
    "后续",
    "同一个事件",
    "继续推进",
    "补充",
    "更新状态",
]


def slugify(value: str) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"\s+", "-", lowered)
    lowered = re.sub(r"[^\w\u4e00-\u9fff-]", "", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return lowered or "trace-unit"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_yaml(path: Path, payload: OrderedDict | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(dict(payload), allow_unicode=True, sort_keys=False, default_flow_style=False)
    path.write_text(text, encoding="utf-8")


def read_input_text(input_path: str | None, *, allow_stdin: bool = False) -> tuple[Path | None, str]:
    if input_path:
        path = Path(input_path).resolve()
        return path, read_text(path)
    if allow_stdin:
        data = sys.stdin.read()
        return None, data
    raise ValueError("必须提供 --input，或启用 allow_stdin。")


def _quote_list_scalar_line(line: str) -> str:
    match = re.match(r"^(\s*-\s+)(.*)$", line)
    if not match:
        return line
    prefix, value = match.groups()
    stripped = value.strip()
    if not stripped:
        return line
    if stripped.startswith(("'", '"', "[", "{")):
        return line
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{prefix}"{escaped}"'


def safe_load_yaml_object(text: str, path: Path) -> dict:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        sanitized = "\n".join(_quote_list_scalar_line(line) for line in text.splitlines())
        data = yaml.safe_load(sanitized) or {}
    if not isinstance(data, dict):
        raise ValueError(f"TraceUnit 文件不是对象结构: {path}")
    return data


def ensure_project_layout(project_dir: Path) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "trace").mkdir(exist_ok=True)
    for name in ["00_INDEX.md", "01_CURRENT.md"]:
        target = project_dir / name
        if not target.exists():
            shutil.copyfile(TEMPLATES_DIR / name, target)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def normalize_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def merge_unique_list(*groups) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in normalize_list(group):
            if item not in seen:
                merged.append(item)
                seen.add(item)
    return merged


def detect_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
        return stripped[:80]
    return fallback


def detect_summary(content: str, fallback: str) -> str:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", content) if block.strip()]
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and all(line.startswith("#") for line in lines):
            continue
        if len(lines) >= 2 and lines[0].startswith("#"):
            without_heading = normalize_inline_text(" ".join(lines[1:]))
            if without_heading:
                return without_heading[:180]
        cleaned = re.sub(r"^#+\s*", "", block).strip()
        if cleaned:
            single_line = re.sub(r"\s+", " ", cleaned)
            if len(blocks) > 1 and single_line == fallback:
                continue
            return single_line[:180]
    return fallback


def detect_evidence(content: str) -> list[str]:
    lines: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(re.sub(r"\s+", " ", stripped))
        if len(lines) >= 2:
            break
    return lines


def normalize_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return heading
    return None


def split_paragraph_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def strip_fenced_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text or "", flags=re.DOTALL)


def split_embedded_heading_blocks(block: str) -> list[str]:
    lines = block.splitlines()
    if not lines:
        return []
    parts: list[str] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") and current and any(item.strip() for item in current):
            parts.append("\n".join(current).strip())
            current = [line]
            continue
        current.append(line)
    if current and any(item.strip() for item in current):
        parts.append("\n".join(current).strip())
    return parts


def starts_with_list_block(block: str) -> bool:
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return bool(re.match(r"^([-*+]|\d+[.)])\s+", stripped))
    return False


def ends_with_intro_line(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return False
    last = lines[-1]
    return last.endswith(("：", ":")) or "告诉 AI 和用户" in last


def is_heading_block(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return bool(lines) and all(line.startswith("#") for line in lines)


def has_boundary_signal(text: str) -> bool:
    lowered = text.lower()
    patterns = [
        "问题",
        "现象",
        "尝试",
        "失败",
        "报错",
        "决策",
        "决定",
        "转向",
        "切换",
        "blocker",
        "下一步",
        "接下来",
        "结论",
        "结果",
        "done",
        "todo",
        "decision",
        "failure",
        "attempt",
        "next step",
    ]
    return any(pattern in lowered for pattern in patterns)


def infer_thread(text: str, default_thread: str | None) -> str:
    if default_thread:
        return default_thread
    lowered = text.lower()
    candidates = [
        "baseline",
        "evaluation",
        "scaling",
        "data-cleaning",
        "skill-core",
        "repository",
        "experiment",
    ]
    switch_patterns = [
        r"(?:switch to|focus on|move to|切换到|转向|转到)\s*([a-z][a-z0-9-]+)",
        r"(?:主线从|从)\s*[a-z][a-z0-9-]*\s*(?:切换到|转到)\s*([a-z][a-z0-9-]+)",
    ]
    for pattern in switch_patterns:
        match = re.search(pattern, lowered)
        if match and match.group(1) in candidates:
            return match.group(1)
    for candidate in candidates:
        if candidate in lowered:
            return candidate
    return default_thread or "general"


def infer_unit_type(text: str) -> str:
    lowered = text.lower()
    documentation_context_markers = [
        "设计原则",
        "核心概念",
        "架构说明",
        "版本定位",
        "推荐类型",
        "默认顺序",
        "筛选条件",
        "输出目标",
        "格式",
        "建议结构",
        "最小字段",
        "粒度目标",
        "对比",
        "说明",
        "规则",
        "规范",
        "入口",
        "作用",
        "特征",
        "本质",
        "情况",
    ]
    if "当前实现状态" in lowered or ("已完成" in lowered and "待实现" in lowered):
        return "result"
    if "|" in text and text.count("|") >= 6:
        return "context"
    if any(marker in text for marker in documentation_context_markers):
        return "context"
    known_types = [
        "context",
        "problem",
        "attempt",
        "failure",
        "decision",
        "direction-shift",
        "result",
        "blocker",
        "next-step",
        "review",
    ]
    if sum(1 for item in known_types if item in lowered) >= 3:
        return "context"
    if any(key in lowered for key in ["方向切换", "转向", "切换", "不再是主线", "focus ", "switch to", "direction-shift"]):
        return "direction-shift"
    if any(key in lowered for key in ["决定", "决策", "确定", "选定", "decision"]):
        return "decision"
    if any(key in lowered for key in ["blocker", "阻塞", "卡住", "无法继续", "待解决"]):
        return "blocker"
    if any(key in lowered for key in ["失败", "报错", "未生效", "没有生效", "不行", "error", "failed"]):
        return "failure"
    if any(key in lowered for key in ["下一步", "接下来", "todo", "后续", "next step"]):
        return "next-step"
    if any(key in lowered for key in ["完成", "已完成", "落地", "成功", "实现了", "result"]):
        return "result"
    if any(key in lowered for key in ["尝试", "试了", "验证", "实验", "attempt", "try "]):
        return "attempt"
    if any(key in lowered for key in ["问题", "现象", "目标", "why", "problem"]):
        return "problem"
    return "context"


def infer_unit_type_from_heading(heading: str | None) -> str | None:
    if not heading:
        return None
    normalized = normalize_inline_text(heading).lower()
    mapping = {
        "背景": "context",
        "上下文": "context",
        "问题": "problem",
        "核心问题": "problem",
        "尝试": "attempt",
        "失败": "failure",
        "报错": "failure",
        "决策": "decision",
        "决定": "decision",
        "转向": "direction-shift",
        "方向切换": "direction-shift",
        "结果": "result",
        "结论": "result",
        "blocker": "blocker",
        "阻塞": "blocker",
        "下一步": "next-step",
        "后续": "next-step",
        "复盘": "review",
        "review": "review",
    }
    if normalized in mapping:
        return mapping[normalized]
    for marker, mapped_type in mapping.items():
        if marker in normalized:
            return mapped_type
    return None


def infer_status(unit_type: str, text: str) -> str:
    lowered = text.lower()
    if unit_type == "blocker":
        return "blocked"
    if unit_type in {"decision", "direction-shift"}:
        return "confirmed"
    if unit_type == "result":
        return "done"
    if unit_type == "next-step":
        return "active"
    if unit_type == "failure" and any(key in lowered for key in ["仍未", "尚未", "无法", "卡住"]):
        return "blocked"
    return "candidate"


def infer_affects_current(unit_type: str, text: str) -> bool:
    lowered = text.lower()
    if unit_type in {"direction-shift", "blocker", "next-step", "decision", "result"}:
        return True
    return any(key in lowered for key in ["当前", "主线"])


def infer_tags(text: str, unit_type: str, base_tags: list[str]) -> list[str]:
    tags = list(base_tags)
    mapping = {
        "meeting": ["会议", "meeting"],
        "experiment": ["实验", "experiment"],
        "debug": ["报错", "调试", "debug", "error"],
        "review": ["复盘", "review"],
        "documentation": ["readme", "文档", "documentation"],
        "automation": ["automation", "自动化"],
        "design": ["design", "设计"],
        "loader": ["loader", "session loader", "加载"],
    }
    lowered = text.lower()
    for tag, keywords in mapping.items():
        if any(keyword in lowered for keyword in keywords):
            tags.append(tag)
    normalized = []
    seen: set[str] = set()
    for tag in tags:
        value = str(tag).strip().lstrip("#")
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def build_segment_groups(text: str) -> list[str]:
    paragraph_blocks = split_paragraph_blocks(strip_fenced_code_blocks(text))
    if not paragraph_blocks:
        return []
    raw_blocks: list[str] = []
    for block in paragraph_blocks:
        raw_blocks.extend(split_embedded_heading_blocks(block))
    blocks: list[str] = []
    idx = 0
    while idx < len(raw_blocks):
        block = raw_blocks[idx]
        if is_heading_block(block) and idx + 1 < len(raw_blocks):
            next_block = raw_blocks[idx + 1]
            if is_heading_block(next_block):
                idx += 1
                continue
            blocks.append(f"{block}\n\n{raw_blocks[idx + 1]}".strip())
            idx += 2
            continue
        if is_heading_block(block):
            idx += 1
            continue
        blocks.append(block)
        idx += 1
    groups: list[list[str]] = []
    current: list[str] = []
    for block in blocks:
        boundary = is_heading_block(block) or (has_boundary_signal(block) and current)
        if boundary and current:
            groups.append(current)
            current = [block]
        else:
            current.append(block)
    if current:
        groups.append(current)

    merged: list[str] = []
    for group in groups:
        text_block = "\n\n".join(group).strip()
        if merged and starts_with_list_block(text_block) and ends_with_intro_line(merged[-1]):
            merged[-1] = (merged[-1] + "\n\n" + text_block).strip()
            continue
        if merged and len(normalize_inline_text(text_block)) < 80 and not has_boundary_signal(text_block):
            merged[-1] = (merged[-1] + "\n\n" + text_block).strip()
        else:
            merged.append(text_block)
    return merged
def is_placeholder_summary(text: str) -> bool:
    normalized = normalize_inline_text(text)
    if not normalized:
        return True
    if normalized in {"-", "--", "—", "暂无", "none", "n/a"}:
        return True
    cleaned = re.sub(r"[-—•*#`|:\s]+", "", normalized)
    return not cleaned


def build_unit_payload(
    *,
    project_name: str,
    source_path: Path | None,
    source_type: str,
    date_str: str,
    trace_id: str,
    block_text: str,
    title: str,
    summary: str,
    thread: str,
    unit_type: str,
    tags: list[str],
    status: str,
    affects_current: bool,
    confidence: float,
) -> OrderedDict:
    source_ref = str(source_path).replace("\\", "/") if source_path else ""
    raw_refs = [source_ref] if source_ref else []
    return OrderedDict(
        [
            ("id", trace_id),
            ("project", project_name),
            ("date", date_str),
            ("title", title),
            ("source_type", source_type),
            ("source_ref", source_ref),
            ("raw_refs", raw_refs),
            ("unit_type", unit_type),
            ("thread", thread),
            ("tags", tags),
            ("summary", summary),
            ("details", block_text[:4000]),
            ("evidence", detect_evidence(block_text)),
            ("status", status),
            ("affects_current", affects_current),
            ("importance", "high" if affects_current else "medium"),
            ("confidence", round(confidence, 2)),
            ("prev", []),
            ("next", []),
            ("related", []),
            ("supersedes", []),
        ]
    )


def dump_unit_payload(unit: dict) -> OrderedDict:
    return OrderedDict(
        [
            ("id", str(unit.get("id", ""))),
            ("project", str(unit.get("project", ""))),
            ("date", str(unit.get("date", ""))),
            ("title", str(unit.get("title", ""))),
            ("source_type", str(unit.get("source_type", ""))),
            ("source_ref", str(unit.get("source_ref", ""))),
            ("raw_refs", normalize_list(unit.get("raw_refs"))),
            ("unit_type", str(unit.get("unit_type", ""))),
            ("thread", str(unit.get("thread", ""))),
            ("tags", normalize_list(unit.get("tags"))),
            ("summary", str(unit.get("summary", ""))),
            ("details", str(unit.get("details", ""))),
            ("evidence", normalize_list(unit.get("evidence"))),
            ("status", str(unit.get("status", "candidate") or "candidate")),
            ("affects_current", bool(unit.get("affects_current", False))),
            ("importance", str(unit.get("importance", "medium") or "medium")),
            ("confidence", round(float(unit.get("confidence", 0.0) or 0.0), 2)),
            ("prev", normalize_list(unit.get("prev"))),
            ("next", normalize_list(unit.get("next"))),
            ("related", normalize_list(unit.get("related"))),
            ("supersedes", normalize_list(unit.get("supersedes"))),
        ]
    )


def append_detail_section(existing: str, incoming: str, *, date_str: str) -> str:
    existing_text = (existing or "").rstrip()
    incoming_text = (incoming or "").strip()
    if not incoming_text:
        return existing_text
    section = f"[续写 {date_str}]\n{incoming_text}"
    if not existing_text:
        return section
    return f"{existing_text}\n\n{section}"


def extract_match_tokens(text: str) -> set[str]:
    normalized = normalize_inline_text((text or "").lower())
    if not normalized:
        return set()
    pieces = re.split(r"[^\w\u4e00-\u9fff-]+", normalized)
    tokens: set[str] = set()
    for piece in pieces:
        value = piece.strip("-_")
        if not value or value in STOPWORD_TOKENS:
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", value):
            if 2 <= len(value) <= 12:
                tokens.add(value)
            if len(value) >= 3:
                upper = min(4, len(value))
                for size in range(3, upper + 1):
                    for idx in range(0, len(value) - size + 1):
                        fragment = value[idx : idx + size]
                        if fragment not in STOPWORD_TOKENS:
                            tokens.add(fragment)
            continue
        if len(value) >= 3:
            tokens.add(value)
    return tokens


def has_continuation_hint(text: str) -> bool:
    normalized = normalize_inline_text((text or "").lower())
    return any(hint in normalized for hint in CONTINUATION_HINTS)


def texts_related(left: str, right: str) -> bool:
    left_tokens = extract_match_tokens(left)
    right_tokens = extract_match_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shared = left_tokens & right_tokens
    return any(len(token) >= 3 for token in shared)


def front_merge_items(new_items: list[str], existing_items: list[str], *, limit: int = 3, drop_related_to: str | None = None) -> list[str]:
    filtered_existing = list(existing_items)
    if drop_related_to:
        filtered_existing = [item for item in filtered_existing if not texts_related(item, drop_related_to)]
    merged = merge_unique_list(new_items, filtered_existing)
    return merged[:limit]


def prepare_units_from_text(
    project_dir: Path,
    *,
    input_text: str,
    source_path: Path | None,
    source_type: str,
    date_str: str,
    project_name: str,
    base_tags: list[str],
    default_thread: str | None,
    force_single_unit: bool = False,
) -> list[OrderedDict]:
    normalized_input = (input_text or "").strip()
    if force_single_unit and normalized_input:
        split_items = [{"block": normalized_input}]
    else:
        split_items = [{"block": block} for block in build_segment_groups(input_text)]
    if not split_items:
        return []

    pending_units: list[dict] = []
    source_stem = source_path.stem if source_path else "current-session"
    for idx, item in enumerate(split_items, start=1):
        block = str(item["block"])
        heading = extract_heading(block)
        title = str(item.get("title") or heading or detect_title(block, fallback=f"{source_stem}-{idx:02d}"))
        summary = str(item.get("summary") or detect_summary(block, fallback=title))
        if is_placeholder_summary(summary):
            continue
        classification_text = f"{title}\n{summary}"
        preset_unit_type = str(item.get("unit_type") or "").strip() or None
        pending_units.append(
            {
                "block": block,
                "title": title,
                "summary": summary,
                "classification_text": classification_text,
                "thread": infer_thread(classification_text, default_thread),
                "unit_type": preset_unit_type or infer_unit_type_from_heading(heading or title) or infer_unit_type(classification_text),
                "confidence": 0.82 if heading else 0.68,
            }
        )

    trace_ids = allocate_trace_ids(project_dir, date_str, len(pending_units))
    created: list[OrderedDict] = []
    for item, trace_id in zip(pending_units, trace_ids):
        unit_type = str(item["unit_type"])
        classification_text = str(item["classification_text"])
        tags = infer_tags(str(item["block"]), unit_type, base_tags)
        status = infer_status(unit_type, classification_text)
        affects_current = infer_affects_current(unit_type, classification_text)
        payload = build_unit_payload(
            project_name=project_name,
            source_path=source_path,
            source_type=source_type,
            date_str=date_str,
            trace_id=trace_id,
            block_text=str(item["block"]),
            title=str(item["title"]),
            summary=str(item.get("summary") or detect_summary(str(item["block"]), fallback=str(item["title"]))),
            thread=str(item["thread"]),
            unit_type=unit_type,
            tags=tags,
            status=status,
            affects_current=affects_current,
            confidence=float(item["confidence"]),
        )
        created.append(payload)

    for prev_unit, next_unit in zip(created, created[1:]):
        prev_unit["next"] = [next_unit["id"]]
        next_unit["prev"] = [prev_unit["id"]]
    return created


def summarize_current_updates(
    payloads: list[dict],
    *,
    date_str: str,
) -> tuple[str | None, list[str], list[str], list[str], str | None]:
    latest_thread: str | None = None
    current_problem: list[str] = []
    current_blocker: list[str] = []
    next_step: list[str] = []
    recent_change: str | None = None
    recent_change_rank = -1
    recent_change_priority = {
        "direction-shift": 5,
        "decision": 4,
        "blocker": 4,
        "result": 3,
        "problem": 2,
        "next-step": 1,
    }

    for payload in payloads:
        if payload.get("affects_current"):
            latest_thread = str(payload.get("thread", "") or latest_thread or "")
            payload_rank = recent_change_priority.get(str(payload.get("unit_type", "")), 0)
            if payload_rank >= recent_change_rank:
                recent_change = f"{date_str}：{payload.get('title', '')}"
                recent_change_rank = payload_rank
        if payload.get("unit_type") == "problem":
            current_problem.append(str(payload.get("summary", "")))
        if payload.get("unit_type") == "blocker" or payload.get("status") == "blocked":
            current_blocker.append(str(payload.get("summary", "")))
        if payload.get("unit_type") == "next-step":
            next_step.append(str(payload.get("summary", "")))

    return latest_thread, current_problem[:3], current_blocker[:3], next_step[:3], recent_change


def derive_current_sections(
    existing_sections: OrderedDict[str, list[str]],
    *,
    payloads: list[dict],
    date_str: str,
) -> OrderedDict[str, list[str]]:
    sections: OrderedDict[str, list[str]] = OrderedDict(
        (name, list(items)) for name, items in existing_sections.items()
    )

    for payload in payloads:
        unit_type = str(payload.get("unit_type", "") or "")
        status = str(payload.get("status", "") or "")
        thread = str(payload.get("thread", "") or "")
        title = str(payload.get("title", "") or "")
        summary = str(payload.get("summary", "") or title)
        basis_text = f"{title} {summary}".strip()

        if payload.get("affects_current") and thread:
            sections["当前主线"] = [thread]

        if unit_type == "problem":
            sections["当前问题"] = front_merge_items([summary], sections["当前问题"], limit=3)

        if unit_type == "blocker" or status == "blocked":
            sections["当前 blocker"] = front_merge_items(
                [summary],
                sections["当前 blocker"],
                limit=3,
                drop_related_to=basis_text,
            )
        elif unit_type in {"result", "decision", "direction-shift"} or status in {"done", "confirmed"}:
            sections["当前 blocker"] = [
                item for item in sections["当前 blocker"] if not texts_related(item, basis_text)
            ][:3]

        if unit_type == "next-step":
            sections["下一步"] = [summary]
        elif unit_type in {"result", "decision", "direction-shift"} or status == "done":
            sections["下一步"] = [
                item for item in sections["下一步"] if not texts_related(item, basis_text)
            ][:3]

        if unit_type in {"decision", "direction-shift", "result"} and payload.get("affects_current"):
            sections["当前问题"] = [
                item for item in sections["当前问题"] if not texts_related(item, basis_text)
            ][:3]

        recent_change = f"{date_str}：{title or summary}"
        existing_recent = [item for item in sections["最近变化"] if item != recent_change]
        sections["最近变化"] = [recent_change] + existing_recent[:4]

    return sections


def apply_current_updates(
    project_dir: Path,
    *,
    payloads: list[dict],
    date_str: str,
    current_thread: str | None = None,
    current_problem: list[str] | None = None,
    current_blocker: list[str] | None = None,
    next_step: list[str] | None = None,
    recent_change: str | None = None,
) -> OrderedDict[str, list[str]]:
    sections = derive_current_sections(
        parse_current(project_dir),
        payloads=payloads,
        date_str=date_str,
    )
    if current_thread:
        sections["当前主线"] = [current_thread]
    if current_problem:
        sections["当前问题"] = current_problem[:3]
    if current_blocker:
        sections["当前 blocker"] = current_blocker[:3]
    if next_step:
        sections["下一步"] = next_step[:3]
    if recent_change:
        existing_recent = [item for item in sections["最近变化"] if item != recent_change]
        sections["最近变化"] = [recent_change] + existing_recent[:4]
    write_current(project_dir, sections)
    return sections


def write_created_units(
    project_dir: Path,
    *,
    date_str: str,
    created: list[OrderedDict],
    update_current_flag: bool,
) -> tuple[str | None, list[str], list[str], list[str], str | None]:
    final_thread, final_problem, final_blocker, final_next_step, final_recent_change = summarize_current_updates(
        created,
        date_str=date_str,
    )
    recent_change_rank = -1
    recent_change_priority = {
        "direction-shift": 5,
        "decision": 4,
        "blocker": 4,
        "result": 3,
        "problem": 2,
        "next-step": 1,
    }
    latest_thread: str | None = None

    for payload in created:
        title = str(payload["title"])
        slug = slugify(title)
        trace_filename = f"{date_str}-{slug}.yaml"
        trace_relpath = f"trace/{trace_filename}"
        trace_path = project_dir / "trace" / trace_filename

        suffix = 2
        while trace_path.exists():
            trace_filename = f"{date_str}-{slug}-{suffix}.yaml"
            trace_relpath = f"trace/{trace_filename}"
            trace_path = project_dir / "trace" / trace_filename
            suffix += 1

        write_yaml(trace_path, payload)

        if payload["affects_current"]:
            latest_thread = str(payload["thread"])
            payload_rank = recent_change_priority.get(str(payload["unit_type"]), 0)
            if payload_rank >= recent_change_rank:
                final_recent_change = f"{date_str}：{title}"
                recent_change_rank = payload_rank
    final_thread = latest_thread or final_thread

    if update_current_flag and any([final_thread, final_problem, final_blocker, final_next_step, final_recent_change]):
        apply_current_updates(
            project_dir,
            payloads=list(created),
            date_str=date_str,
            current_thread=final_thread,
            current_problem=final_problem,
            current_blocker=final_blocker,
            next_step=final_next_step,
            recent_change=final_recent_change,
        )
        print(f"[OK] Updated current: {project_dir / '01_CURRENT.md'}")

    return final_thread, final_problem, final_blocker, final_next_step, final_recent_change


def load_index(project_dir: Path) -> str:
    index_path = project_dir / "00_INDEX.md"
    if not index_path.exists():
        return ""
    return read_text(index_path)


INDEX_RECORD_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \[([^\]]+)\] (.+?)\s*$")
INDEX_TAG_RE = re.compile(r"(?:^|\s)#([\w-]+)")


def normalize_index_path(project_dir: Path, target: Path | str) -> str:
    path = Path(target).resolve() if isinstance(target, Path) else Path(str(target)).resolve()
    try:
        return path.relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_index_tags(tags: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags or []:
        value = str(tag).strip().lstrip("#")
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def parse_index_record_line(line: str) -> dict | None:
    stripped = line.strip()
    match = INDEX_RECORD_RE.match(stripped)
    if not match:
        return None
    date_str, path_text, tail = match.groups()
    tags = INDEX_TAG_RE.findall(tail)
    summary = re.sub(r"(?:\s+#[-\w]+)+\s*$", "", tail).strip()
    if not summary:
        summary = "未命名记录"
    return {
        "date": date_str,
        "path": path_text.strip(),
        "summary": summary,
        "tags": normalize_index_tags(tags),
    }


def format_index_record(record: dict) -> str:
    tags = normalize_index_tags(record.get("tags"))
    tag_suffix = f" {' '.join('#' + tag for tag in tags)}" if tags else ""
    return f"- {record['date']} [{record['path']}] {record['summary']}{tag_suffix}"


def load_index_records(project_dir: Path) -> list[dict]:
    records: list[dict] = []
    seen_paths: set[str] = set()
    for line in load_index(project_dir).splitlines():
        record = parse_index_record_line(line)
        if not record:
            continue
        if record["path"] in seen_paths:
            continue
        seen_paths.add(record["path"])
        records.append(record)
    records.sort(key=lambda item: (item["date"], item["path"]))
    return records


def render_index(records: list[dict]) -> str:
    lines = ["# 00_INDEX", ""]
    if not records:
        return "\n".join(lines).rstrip() + "\n"

    years = sorted({record["date"][:4] for record in records})
    months_by_year: OrderedDict[str, list[str]] = OrderedDict()
    for year in years:
        months = sorted({record["date"][:7] for record in records if record["date"].startswith(year)})
        months_by_year[year] = months

    for year in years:
        lines.append(f"- [{year}年](#{year}年)")
        for month in months_by_year[year]:
            lines.append(f"  - [{month}](#{month})")
    lines.append("")

    for year_idx, year in enumerate(years):
        lines.append(f"## {year}年")
        lines.append("")
        for month_idx, month in enumerate(months_by_year[year]):
            lines.append(f"### {month}")
            lines.append("")
            month_records = [record for record in records if record["date"].startswith(month)]
            month_records.sort(key=lambda item: (item["date"], item["path"]), reverse=True)
            for record in month_records:
                lines.append(format_index_record(record))
            if month_idx != len(months_by_year[year]) - 1:
                lines.append("")
        if year_idx != len(years) - 1:
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_index_records(project_dir: Path, records: list[dict]) -> None:
    index_path = project_dir / "00_INDEX.md"
    write_text(index_path, render_index(records))


def append_index_record(
    project_dir: Path,
    *,
    date_str: str,
    record_path: str,
    summary: str,
    tags: list[str] | None = None,
) -> None:
    record = {
        "date": date_str,
        "path": str(record_path).replace("\\", "/"),
        "summary": normalize_inline_text(summary) or "未命名记录",
        "tags": normalize_index_tags(tags),
    }
    records = load_index_records(project_dir)
    updated = False
    for idx, existing in enumerate(records):
        if existing["path"] == record["path"]:
            records[idx] = record
            updated = True
            break
    if not updated:
        records.append(record)
    records.sort(key=lambda item: (item["date"], item["path"]))
    write_index_records(project_dir, records)


def read_index_entries(project_dir: Path, limit: int = 10, tags: list[str] | None = None) -> list[str]:
    records = load_index_records(project_dir)
    filter_tags = set(normalize_index_tags(tags))
    if filter_tags:
        filtered = [record for record in records if filter_tags.intersection(record.get("tags", []))]
        if filtered:
            records = filtered
    records.sort(key=lambda item: (item["date"], item["path"]), reverse=True)
    return [format_index_record(record) for record in records[:limit]]


def build_session_index_summary(*, thread: str | None, tags: list[str] | None, days: int) -> str:
    parts: list[str] = []
    if thread:
        parts.append(f"聚焦 {thread} 主线")
    normalized_tags = normalize_index_tags(tags)
    if normalized_tags:
        parts.append(f"关注 {' '.join('#' + tag for tag in normalized_tags)}")
    scope = "，".join(parts)
    prefix = f"会话整理：{scope}，" if scope else "会话整理："
    return f"{prefix}汇总最近 {days} 天的当前状态、生成记录与建议补读内容。"


def build_review_index_summary(*, period: str, title: str | None = None) -> str:
    if period == "daily":
        return "今日日报：汇总当日关键推进、当前状态与下一步。"
    if period == "weekly":
        return "本周回顾：汇总本周期关键推进、当前状态与下一步。"
    if period == "monthly":
        return "本月回顾：汇总本周期关键推进、当前状态与下一步。"
    if title:
        return f"阶段回顾：{normalize_inline_text(title)}"
    return "阶段回顾：汇总当前时间范围内的关键推进、当前状态与下一步。"


def parse_current(project_dir: Path) -> OrderedDict[str, list[str]]:
    sections: OrderedDict[str, list[str]] = OrderedDict((name, []) for name in KNOWN_CURRENT_SECTIONS)
    current_path = project_dir / "01_CURRENT.md"
    if not current_path.exists():
        return sections
    content = read_text(current_path)
    current_key = ""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "# 01_CURRENT":
            continue
        if stripped.startswith("## "):
            name = stripped[3:].strip()
            current_key = name if name in sections else ""
            continue
        if current_key and stripped.startswith("- "):
            value = stripped[2:].strip()
            if value:
                sections[current_key].append(value)
    return sections


def write_current(project_dir: Path, sections: OrderedDict[str, list[str]]) -> None:
    lines = ["# 01_CURRENT", ""]
    for name, items in sections.items():
        lines.append(f"## {name}")
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- ")
        lines.append("")
    write_text(project_dir / "01_CURRENT.md", "\n".join(lines))


def update_current(
    project_dir: Path,
    *,
    current_thread: str | None,
    current_problem: list[str],
    current_blocker: list[str],
    next_step: list[str],
    recent_change: str | None,
) -> None:
    sections = parse_current(project_dir)
    if current_thread:
        sections["当前主线"] = [current_thread]
    if current_problem:
        sections["当前问题"] = current_problem
    if current_blocker:
        sections["当前 blocker"] = current_blocker
    if next_step:
        sections["下一步"] = next_step
    if recent_change:
        existing = [item for item in sections["最近变化"] if item != recent_change]
        sections["最近变化"] = [recent_change] + existing[:4]
    write_current(project_dir, sections)


def load_trace_unit(path: Path) -> dict:
    data = safe_load_yaml_object(read_text(path), path)
    unit = dict(data)
    unit["tags"] = normalize_list(unit.get("tags"))
    unit["raw_refs"] = normalize_list(unit.get("raw_refs"))
    unit["evidence"] = normalize_list(unit.get("evidence"))
    unit["prev"] = normalize_list(unit.get("prev"))
    unit["next"] = normalize_list(unit.get("next"))
    unit["related"] = normalize_list(unit.get("related"))
    unit["supersedes"] = normalize_list(unit.get("supersedes"))
    unit["status"] = str(unit.get("status", "candidate") or "candidate")
    unit["thread"] = str(unit.get("thread", "") or "")
    unit["unit_type"] = str(unit.get("unit_type", "") or "")
    unit["summary"] = str(unit.get("summary", "") or "")
    unit["details"] = str(unit.get("details", "") or "")
    unit["title"] = str(unit.get("title", path.stem) or path.stem)
    unit["source_ref"] = str(unit.get("source_ref", "") or "")
    unit["date"] = str(unit.get("date", "") or "")
    unit["importance"] = str(unit.get("importance", "medium") or "medium")
    try:
        unit["confidence"] = float(unit.get("confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        unit["confidence"] = 0.0
    unit["affects_current"] = bool(unit.get("affects_current", False))
    unit["_path"] = path
    unit["_relpath"] = f"trace/{path.name}"
    unit["_date"] = parse_date(unit.get("date"))
    return unit


def load_trace_units(project_dir: Path) -> list[dict]:
    trace_dir = project_dir / "trace"
    if not trace_dir.exists():
        return []
    units = [load_trace_unit(path) for path in trace_dir.glob("*.yaml")]
    units.sort(key=lambda item: (item.get("_date") or date.min, str(item.get("id", ""))), reverse=True)
    return units


def resolve_trace_unit(project_dir: Path, trace_ref: str) -> dict:
    ref = (trace_ref or "").strip()
    if not ref:
        raise ValueError("必须提供要续写的 TraceUnit。")

    direct_candidates = [
        Path(ref),
        project_dir / ref,
        project_dir / "trace" / ref,
        project_dir / "trace" / f"{ref}.yaml",
    ]
    for candidate in direct_candidates:
        if candidate.exists() and candidate.is_file():
            return load_trace_unit(candidate.resolve())

    units = load_trace_units(project_dir)
    exact_matches = [
        unit
        for unit in units
        if ref in {str(unit.get("id", "")).strip(), str(unit.get("title", "")).strip(), unit.get("_path").stem, unit.get("_relpath")}
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(f"找到多个匹配的 TraceUnit，请改用 ID 或文件名明确指定：{ref}")

    stem_matches = [unit for unit in units if ref == unit.get("_path").stem]
    if len(stem_matches) == 1:
        return stem_matches[0]

    raise ValueError(f"未找到 TraceUnit：{ref}")


def score_continuation_candidate(
    unit: dict,
    *,
    payload: dict,
    current_sections: OrderedDict[str, list[str]],
    target_date: date | None,
) -> tuple[int, list[str], dict]:
    score = 0
    reasons: list[str] = []
    unit_status = str(unit.get("status", "") or "")
    unit_thread = str(unit.get("thread", "") or "")
    payload_thread = str(payload.get("thread", "") or "")
    current_thread = current_sections["当前主线"][0] if current_sections["当前主线"] else ""

    if unit_status == "superseded":
        return -999, ["已被覆盖"], {"explicit_thread_match": False, "shared_tags": 0, "shared_tokens": 0, "continuation_hint": False}
    if unit_status in {"active", "blocked", "confirmed"}:
        score += 3
        reasons.append(f"状态仍活跃({unit_status})")
    elif unit_status == "done":
        score += 1
        reasons.append("近期已完成")

    explicit_thread_match = bool(payload_thread and payload_thread != "general" and unit_thread == payload_thread)
    if explicit_thread_match:
        score += 4
        reasons.append("与本轮 thread 一致")
    elif current_thread and unit_thread == current_thread:
        score += 3
        reasons.append("与当前主线一致")

    if unit.get("affects_current"):
        score += 2
        reasons.append("旧事件仍影响 current")

    if target_date and unit.get("_date"):
        delta_days = abs((target_date - unit["_date"]).days)
        if delta_days <= 7:
            score += 2
            reasons.append("时间上非常接近")
        elif delta_days <= 21:
            score += 1
            reasons.append("时间上较接近")

    shared_tags = sorted(set(normalize_list(unit.get("tags"))) & set(normalize_list(payload.get("tags"))))
    if shared_tags:
        tag_score = min(len(shared_tags) * 2, 4)
        score += tag_score
        reasons.append(f"共享标签: {', '.join(shared_tags[:3])}")

    unit_tokens = extract_match_tokens(f"{unit.get('title', '')} {unit.get('summary', '')}")
    payload_tokens = extract_match_tokens(f"{payload.get('title', '')} {payload.get('summary', '')}")
    shared_tokens = sorted(unit_tokens & payload_tokens)
    if shared_tokens:
        token_score = min(len(shared_tokens), 4)
        score += token_score
        reasons.append(f"共享关键词: {', '.join(shared_tokens[:4])}")

    continuation_hint = has_continuation_hint(f"{payload.get('title', '')} {payload.get('summary', '')}")
    if continuation_hint:
        score += 2
        reasons.append("当前会话带有延续信号")

    if str(unit.get("unit_type", "")) == str(payload.get("unit_type", "")):
        score += 1
        reasons.append("事件类型相近")

    return score, reasons, {
        "explicit_thread_match": explicit_thread_match,
        "shared_tags": len(shared_tags),
        "shared_tokens": len(shared_tokens),
        "continuation_hint": continuation_hint,
    }


def detect_independent_state_boundary(unit: dict, payload: dict) -> list[str]:
    existing_type = str(unit.get("unit_type", "") or "")
    payload_type = str(payload.get("unit_type", "") or "")
    existing_status = str(unit.get("status", "") or "")
    payload_affects_current = bool(payload.get("affects_current"))

    if not payload_type or payload_type == existing_type:
        return []

    reasons: list[str] = []
    open_state_types = {"context", "problem", "attempt", "failure", "blocker"}
    decisive_state_types = {"decision", "direction-shift", "result", "next-step"}

    if payload_affects_current and existing_type in open_state_types and payload_type in decisive_state_types:
        reasons.append("本轮形成了独立新状态，默认应新开 TraceUnit")

    if existing_status == "blocked" and payload_type == "next-step":
        reasons.append("旧 blocker 还在，但已经形成明确下一步")

    if existing_status in {"blocked", "active", "confirmed"} and payload_type == "result":
        reasons.append("当前进展更像对旧状态的结果落地，不应自动并回旧事件")

    if payload_type in {"decision", "direction-shift"} and existing_type not in {"decision", "direction-shift"}:
        reasons.append("当前进展已经构成新的决策/转向节点")

    return merge_unique_list(reasons)


def choose_continuation_candidate(
    project_dir: Path,
    *,
    payload: dict,
    date_str: str,
) -> tuple[dict | None, list[str], int]:
    units = load_trace_units(project_dir)
    if not units:
        return None, [], 0

    current_sections = parse_current(project_dir)
    target_date = parse_date(date_str)
    ranked: list[tuple[int, dict, list[str], dict]] = []
    for unit in units:
        score, reasons, signals = score_continuation_candidate(
            unit,
            payload=payload,
            current_sections=current_sections,
            target_date=target_date,
        )
        if score > 0:
            ranked.append((score, unit, reasons, signals))

    if not ranked:
        return None, [], 0

    ranked.sort(key=lambda item: (item[0], item[1].get("_date") or date.min, str(item[1].get("id", ""))), reverse=True)
    best_score, best_unit, best_reasons, best_signals = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else -999
    if best_score < 7:
        return None, best_reasons, best_score
    if best_score - second_score < 2:
        return None, best_reasons, best_score
    if not (
        best_signals["explicit_thread_match"]
        or best_signals["shared_tags"] > 0
        or best_signals["shared_tokens"] > 0
        or best_signals["continuation_hint"]
    ):
        return None, best_reasons, best_score
    boundary_reasons = detect_independent_state_boundary(best_unit, payload)
    if boundary_reasons:
        return None, merge_unique_list(best_reasons, boundary_reasons), best_score
    return best_unit, best_reasons, best_score


def next_trace_id(project_dir: Path, date_str: str) -> str:
    trace_dir = project_dir / "trace"
    prefix = f"TU-{date_str}-"
    max_suffix = 0
    for path in trace_dir.glob("*.yaml"):
        data = load_trace_unit(path)
        value = str(data.get("id", ""))
        match = re.fullmatch(rf"{re.escape(prefix)}(\d{{3}})", value)
        if match:
            max_suffix = max(max_suffix, int(match.group(1)))
    return f"{prefix}{max_suffix + 1:03d}"


def allocate_trace_ids(project_dir: Path, date_str: str, count: int) -> list[str]:
    if count <= 0:
        return []
    first_id = next_trace_id(project_dir, date_str)
    match = re.fullmatch(rf"TU-{re.escape(date_str)}-(\d{{3}})", first_id)
    if not match:
        raise ValueError(f"无法解析 TraceUnit 起始 ID: {first_id}")
    start = int(match.group(1))
    prefix = f"TU-{date_str}-"
    return [f"{prefix}{start + offset:03d}" for offset in range(count)]


def filter_units(
    units: list[dict],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    thread: str | None = None,
    tags: list[str] | None = None,
    statuses: list[str] | None = None,
) -> list[dict]:
    tags = [tag.strip().lstrip("#") for tag in (tags or []) if tag.strip()]
    statuses = [status.strip() for status in (statuses or []) if status.strip()]
    results: list[dict] = []
    for unit in units:
        unit_date = unit.get("_date")
        if start_date and unit_date and unit_date < start_date:
            continue
        if end_date and unit_date and unit_date > end_date:
            continue
        if thread and unit.get("thread") != thread:
            continue
        if tags and not any(tag in unit.get("tags", []) for tag in tags):
            continue
        if statuses and unit.get("status") not in statuses:
            continue
        results.append(unit)
    return results


def score_session_unit(unit: dict, *, current_thread: str | None, tags: list[str], statuses: list[str]) -> tuple:
    unit_tags = unit.get("tags", [])
    status = unit.get("status", "candidate")
    unit_date = unit.get("_date") or date.min
    return (
        1 if unit.get("affects_current") else 0,
        1 if current_thread and unit.get("thread") == current_thread else 0,
        1 if tags and any(tag in unit_tags for tag in tags) else 0,
        1 if status in statuses else 0,
        STATUS_RANK.get(status, 1),
        IMPORTANCE_RANK.get(str(unit.get("importance", "medium")), 1),
        unit_date.toordinal(),
    )


def render_current_sections(sections: OrderedDict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for name, items in sections.items():
        lines.append(f"### {name}")
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- 暂无")
        lines.append("")
    return lines


def infer_session_task_mode(
    *,
    requested_thread: str | None,
    tags: list[str],
    current_sections: OrderedDict[str, list[str]],
) -> str:
    if requested_thread:
        return "继续当前主线"
    if tags:
        review_tags = {"review", "weekly", "daily", "monthly"}
        if any(tag in review_tags for tag in tags):
            return "阶段复盘 / review"
        return "查看某个主题"
    if current_sections["当前主线"]:
        return "新 session 接手 / 继续当前主线"
    return "新 session 接手"


def build_session_filter_summary(
    *,
    task_mode: str,
    current_thread: str | None,
    tags: list[str],
    days: int,
) -> list[str]:
    lines = [f"- 当前任务类型：{task_mode}"]
    if current_thread:
        lines.append(f"- 主线筛选：`{current_thread}`")
    if tags:
        lines.append(f"- 主题筛选：{' '.join('#' + tag for tag in tags)}")
    lines.append(f"- 时间筛选：最近 {days} 天")
    lines.append("- 状态优先：active / blocked / confirmed")
    lines.append("- current 优先：affects_current = true")
    return lines


def build_session_expand_advice(*, task_mode: str, selected_units: list[dict], current_sections: OrderedDict[str, list[str]]) -> list[str]:
    needs_context = False
    if current_sections["当前 blocker"] and not any(
        unit.get("status") == "blocked" or unit.get("unit_type") == "blocker" for unit in selected_units
    ):
        needs_context = True
    if current_sections["下一步"] and not any(unit.get("unit_type") == "next-step" for unit in selected_units):
        needs_context = True

    if task_mode in {"阶段复盘 / review", "追某个具体事件"}:
        return [
            "- 当前任务天然允许扩读；如已读 unit 仍不能解释事件来源，可继续扩大时间窗或补读同 thread / 同 tag 的 unit。"
        ]
    if needs_context:
        return [
            "- 当前推荐条目还不足以解释 current；优先继续补读同主线、同时间窗内的 blocker / next-step / decision 相关 unit。"
        ]
    return [
        "- 当前推荐条目通常已足够继续工作；除非用户要求回顾全貌，否则不要默认扩读很多历史 unit。"
    ]


def build_session_markdown(
    project_dir: Path,
    *,
    selected_units: list[dict],
    requested_thread: str | None,
    tags: list[str],
    days: int,
) -> str:
    current_sections = parse_current(project_dir)
    current_thread = requested_thread or (current_sections["当前主线"][0] if current_sections["当前主线"] else None)
    task_mode = infer_session_task_mode(
        requested_thread=requested_thread,
        tags=tags,
        current_sections=current_sections,
    )
    lines = ["# DevTrace Session Context Pack", ""]
    lines.append(f"- 项目目录：`{project_dir}`")
    lines.append(f"- 时间窗口：最近 {days} 天")
    if current_thread:
        lines.append(f"- 当前主线：`{current_thread}`")
    if tags:
        lines.append(f"- 标签过滤：{' '.join('#' + tag for tag in tags)}")
    lines.append("")

    lines.append("## 当前状态")
    lines.append("")
    lines.extend(render_current_sections(current_sections))

    lines.append("## 最近生成记录")
    lines.append("")
    index_entries = read_index_entries(project_dir, limit=8, tags=tags)
    if index_entries:
        lines.extend(index_entries)
    else:
        lines.append("- 暂无生成记录")
    lines.append("")

    lines.append("## 本轮筛选口径")
    lines.append("")
    lines.extend(build_session_filter_summary(
        task_mode=task_mode,
        current_thread=current_thread,
        tags=tags,
        days=days,
    ))
    lines.append("")

    lines.append("## 建议继续读取")
    lines.append("")
    lines.append("- 先从上面的相关生成记录进入；如果仍缺细节，再继续读取下列相关 TraceUnit。")
    lines.append("")
    if not selected_units:
        lines.append("- 在当前筛选条件下未找到合适的事件单元。")
        lines.append("")
        lines.append("## 是否需要继续扩读")
        lines.append("")
        lines.append("- 建议先放宽 thread / tag / 时间窗，再重新生成 session pack。")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    lines.append("### 相关 TraceUnit")
    lines.append("")
    for idx, unit in enumerate(selected_units, start=1):
        lines.append(f"#### {idx}. {unit.get('title')} ({unit.get('id', 'NO-ID')})")
        lines.append(f"- 日期：{unit.get('date') or '未知'}")
        lines.append(f"- 主线：{unit.get('thread') or '未标注'}")
        lines.append(f"- 类型：{unit.get('unit_type') or '未标注'}")
        lines.append(f"- 状态：{unit.get('status') or '未标注'}")
        lines.append(f"- 影响 current：{'是' if unit.get('affects_current') else '否'}")
        lines.append(f"- 标签：{' '.join('#' + tag for tag in unit.get('tags', [])) if unit.get('tags') else '无'}")
        lines.append(f"- 摘要：{unit.get('summary') or '无摘要'}")
        if unit.get("source_ref"):
            lines.append(f"- 来源：`{unit.get('source_ref')}`")
        lines.append(f"- 文件：`{unit.get('_path')}`")
        lines.append("")

    lines.append("## 是否需要继续扩读")
    lines.append("")
    lines.extend(build_session_expand_advice(
        task_mode=task_mode,
        selected_units=selected_units,
        current_sections=current_sections,
    ))
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_session_pack(
    project_dir: Path,
    *,
    days: int = 7,
    limit: int = 5,
    thread: str | None = None,
    tags: list[str] | None = None,
    status: list[str] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    units = load_trace_units(project_dir)
    tags = [tag.strip().lstrip("#") for tag in (tags or []) if tag.strip()]
    statuses = status or DEFAULT_SESSION_STATUSES
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=max(int(days) - 1, 0)))

    filtered = filter_units(
        units,
        start_date=start_date,
        end_date=end_date,
        thread=thread,
        tags=tags,
    )
    current_sections = parse_current(project_dir)
    current_thread = thread or (current_sections["当前主线"][0] if current_sections["当前主线"] else None)
    selected = sorted(
        filtered,
        key=lambda unit: score_session_unit(
            unit,
            current_thread=current_thread,
            tags=tags,
            statuses=statuses,
        ),
        reverse=True,
    )[:limit]

    return build_session_markdown(
        project_dir,
        selected_units=selected,
        requested_thread=thread,
        tags=tags,
        days=int(days),
    )


def maybe_write_session_output(
    *,
    project_dir: Path,
    output: str | None,
    days: int,
    limit: int,
    thread: str | None = None,
    tags: list[str] | None = None,
    date_str: str | None = None,
) -> Path | None:
    if not output:
        return None
    target = Path(output).resolve()
    normalized_tags = normalize_index_tags(tags)
    markdown = generate_session_pack(
        project_dir,
        days=days,
        limit=limit,
        thread=thread,
        tags=normalized_tags,
    )
    write_text(target, markdown)
    append_index_record(
        project_dir,
        date_str=date_str or date.today().isoformat(),
        record_path=normalize_index_path(project_dir, target),
        summary=build_session_index_summary(thread=thread, tags=normalized_tags, days=days),
        tags=merge_unique_list(normalized_tags, ["session-summary"]),
    )
    return target


def build_review_markdown(
    project_dir: Path,
    *,
    review_title: str,
    start_date: date | None,
    end_date: date | None,
    units: list[dict],
) -> str:
    current_sections = parse_current(project_dir)
    lines = [f"# {review_title}", ""]
    if start_date and end_date:
        lines.append(f"- 覆盖时间：{start_date.isoformat()} ~ {end_date.isoformat()}")
    lines.append(f"- 统计条目：{len(units)}")
    lines.append(f"- 项目目录：`{project_dir}`")
    lines.append("")

    lines.append("## 当前状态背景")
    lines.append("")
    thread_counter = Counter(unit.get("thread") or "未标注" for unit in units)
    if thread_counter:
        top_threads = ", ".join(f"{name}({count})" for name, count in thread_counter.most_common(4))
        lines.append(f"- 本周期主要主线：{top_threads}")
    else:
        lines.append("- 本周期主要主线：暂无")
    if current_sections["当前主线"]:
        lines.append(f"- 当前主线：{current_sections['当前主线'][0]}")
    if current_sections["当前 blocker"]:
        lines.append(f"- 当前 blocker：{'; '.join(current_sections['当前 blocker'])}")
    if current_sections["下一步"]:
        lines.append(f"- 当前下一步：{'; '.join(current_sections['下一步'])}")
    lines.append("")

    highlights = [
        unit
        for unit in units
        if unit.get("affects_current")
        or unit.get("unit_type") in {"decision", "direction-shift", "result", "blocker", "next-step"}
        or str(unit.get("importance", "medium")) == "high"
    ]
    if not highlights:
        highlights = units[: min(6, len(units))]

    lines.append("## 本周期关键推进")
    lines.append("")
    if highlights:
        for unit in highlights[:8]:
            lines.append(
                f"- {unit.get('date') or '未知'}｜[{unit.get('thread') or '未标注'} / {unit.get('unit_type') or '未标注'}] "
                f"{unit.get('title')}：{unit.get('summary') or '无摘要'}"
            )
    else:
        lines.append("- 本周期暂无关键推进")
    lines.append("")

    decisions = [unit for unit in units if unit.get("unit_type") in {"decision", "direction-shift"}]
    lines.append("## 关键决策与转向")
    lines.append("")
    if decisions:
        for unit in decisions[:6]:
            lines.append(f"- {unit.get('title')}：{unit.get('summary') or '无摘要'}")
    else:
        lines.append("- 本周期没有明确记录到新的决策或方向切换")
    lines.append("")

    blockers = [unit for unit in units if unit.get("unit_type") == "blocker" or unit.get("status") == "blocked"]
    lines.append("## 风险与 blocker")
    lines.append("")
    if blockers:
        for unit in blockers[:6]:
            lines.append(f"- {unit.get('title')}：{unit.get('summary') or '无摘要'}")
    else:
        lines.append("- 本周期未记录新的 blocker")
    lines.append("")

    next_steps = [unit for unit in units if unit.get("unit_type") == "next-step"]
    lines.append("## 下一步建议")
    lines.append("")
    if next_steps:
        for unit in next_steps[:6]:
            lines.append(f"- {unit.get('summary') or unit.get('title')}")
    elif current_sections["下一步"]:
        for item in current_sections["下一步"]:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无明确下一步")
    lines.append("")

    lines.append("## 参考 TraceUnit")
    lines.append("")
    if units:
        for unit in units[:12]:
            lines.append(
                f"- `{unit.get('id', 'NO-ID')}` [{unit.get('thread') or '未标注'} / {unit.get('unit_type') or '未标注'}] "
                f"`{unit.get('_path')}`"
            )
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 复盘口径说明")
    lines.append("")
    lines.append("- 本 review 优先基于时间窗内的高价值 TraceUnit 组织。")
    lines.append("- 若要继续工作，先回到当前主线，再优先读取 affects_current 且状态仍活跃的 unit。")
    lines.append("- 若要回看某个事件全貌，再围绕该事件锚点继续扩读同 thread / 同 tag 的 unit。")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def command_init(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    ensure_project_layout(project_dir)
    print(f"[OK] Initialized DevTrace project context at: {project_dir}")
    return 0


def extend_unit_with_payload(
    project_dir: Path,
    *,
    unit: dict,
    payload: dict,
    date_str: str,
    update_current_flag: bool,
) -> tuple[str | None, list[str], list[str], list[str], str | None]:
    unit["details"] = append_detail_section(str(unit.get("details", "")), str(payload.get("details", "")), date_str=date_str)
    unit["evidence"] = merge_unique_list(unit.get("evidence"), payload.get("evidence"))
    unit["tags"] = merge_unique_list(unit.get("tags"), payload.get("tags"))
    unit["raw_refs"] = merge_unique_list(unit.get("raw_refs"), payload.get("raw_refs"))
    if payload.get("source_ref"):
        unit["source_ref"] = str(payload.get("source_ref"))
    if not unit.get("thread") and payload.get("thread"):
        unit["thread"] = str(payload.get("thread"))
    if payload.get("affects_current"):
        unit["affects_current"] = True
        unit["importance"] = "high"
    if STATUS_RANK.get(str(payload.get("status", "")), 0) >= STATUS_RANK.get(str(unit.get("status", "")), 0):
        unit["status"] = str(payload.get("status", unit.get("status", "candidate")))
    if float(payload.get("confidence", 0.0) or 0.0) > float(unit.get("confidence", 0.0) or 0.0):
        unit["confidence"] = round(float(payload.get("confidence", 0.0) or 0.0), 2)
    for field_name in ["prev", "next", "related", "supersedes"]:
        unit[field_name] = merge_unique_list(unit.get(field_name), payload.get(field_name))

    write_yaml(Path(unit["_path"]), dump_unit_payload(unit))

    payload_for_current = dict(payload)
    payload_for_current["thread"] = str(unit.get("thread", payload.get("thread", "")))
    _, current_problem, current_blocker, next_step, recent_change = summarize_current_updates(
        [payload_for_current],
        date_str=date_str,
    )
    if (payload.get("affects_current") or unit.get("affects_current")) and not recent_change:
        recent_change = f"{date_str}：续写 {unit.get('title', '')}"
    final_thread = payload_for_current.get("thread") if payload_for_current.get("affects_current") else None
    if update_current_flag and any([final_thread, current_problem, current_blocker, next_step, recent_change]):
        apply_current_updates(
            project_dir,
            payloads=[payload_for_current],
            date_str=date_str,
            current_thread=str(final_thread) if final_thread else None,
            current_problem=current_problem,
            current_blocker=current_blocker,
            next_step=next_step,
            recent_change=recent_change,
        )

    return (
        str(final_thread or "") or None,
        current_problem,
        current_blocker,
        next_step,
        recent_change,
    )


def command_add(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    ensure_project_layout(project_dir)

    input_path = Path(args.input).resolve() if args.input else None
    input_text = read_text(input_path) if input_path else ""

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    title = args.title or detect_title(input_text, fallback=(input_path.stem if input_path else "untitled"))
    summary = args.summary or detect_summary(input_text, fallback=title)
    details = args.details or input_text[:4000] or summary
    evidence = args.evidence or detect_evidence(input_text)
    source_ref = args.source_ref or (str(input_path).replace("\\", "/") if input_path else "")
    raw_refs = [str(input_path).replace("\\", "/")] if input_path else []
    tags = [item.strip().lstrip("#") for item in (args.tags or []) if item.strip()]

    trace_id = next_trace_id(project_dir, date_str)
    slug = args.slug or slugify(title)
    trace_filename = f"{date_str}-{slug}.yaml"
    trace_relpath = f"trace/{trace_filename}"
    trace_path = project_dir / "trace" / trace_filename

    payload = OrderedDict(
        [
            ("id", trace_id),
            ("project", args.project or project_dir.name),
            ("date", date_str),
            ("title", title),
            ("source_type", args.source_type),
            ("source_ref", source_ref),
            ("raw_refs", raw_refs),
            ("unit_type", args.unit_type),
            ("thread", args.thread),
            ("tags", tags),
            ("summary", summary),
            ("details", details),
            ("evidence", evidence),
            ("status", args.status),
            ("affects_current", bool(args.affects_current)),
            ("importance", args.importance),
            ("confidence", round(float(args.confidence), 2)),
            ("prev", args.prev or []),
            ("next", args.next or []),
            ("related", args.related or []),
            ("supersedes", args.supersedes or []),
        ]
    )
    write_yaml(trace_path, payload)

    recent_change = args.recent_change
    if args.affects_current and not recent_change:
        recent_change = f"{date_str}：{title}"
    if any([args.current_thread, args.current_problem, args.current_blocker, args.next_step, recent_change]):
        apply_current_updates(
            project_dir,
            payloads=[payload],
            date_str=date_str,
            current_thread=args.current_thread or (args.thread if args.affects_current else None),
            current_problem=args.current_problem or [],
            current_blocker=args.current_blocker or [],
            next_step=args.next_step or [],
            recent_change=recent_change,
        )

    print(f"[OK] Wrote TraceUnit: {trace_path}")
    if any([args.current_thread, args.current_problem, args.current_blocker, args.next_step, recent_change]):
        print(f"[OK] Updated current: {project_dir / '01_CURRENT.md'}")
    session_output = maybe_write_session_output(
        project_dir=project_dir,
        output=args.session_output,
        days=int(args.session_days),
        limit=int(args.session_limit),
        thread=args.session_thread or args.thread or args.current_thread,
        tags=args.session_tags or args.tags or [],
        date_str=date_str,
    )
    if session_output:
        print(f"[OK] Refreshed session context pack: {session_output}")
        print(f"[OK] Updated index: {project_dir / '00_INDEX.md'}")
    return 0


def command_extend(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    ensure_project_layout(project_dir)

    unit = resolve_trace_unit(project_dir, args.target)
    input_path = Path(args.input).resolve() if args.input else None
    input_text = read_text(input_path) if input_path else ""
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    incoming_details = args.details or input_text
    if incoming_details:
        unit["details"] = append_detail_section(str(unit.get("details", "")), incoming_details, date_str=date_str)

    extra_evidence = args.evidence or detect_evidence(input_text)
    if extra_evidence:
        unit["evidence"] = merge_unique_list(unit.get("evidence"), extra_evidence)

    tags = [item.strip().lstrip("#") for item in (args.tags or []) if item.strip()]
    if tags:
        unit["tags"] = merge_unique_list(unit.get("tags"), tags)

    if args.summary:
        unit["summary"] = args.summary
    if args.thread:
        unit["thread"] = args.thread
    if args.status:
        unit["status"] = args.status
    if args.unit_type:
        unit["unit_type"] = args.unit_type
    if args.source_type:
        unit["source_type"] = args.source_type
    if args.affects_current:
        unit["affects_current"] = True
        unit["importance"] = "high"
    if args.importance:
        unit["importance"] = args.importance
    if args.confidence is not None:
        unit["confidence"] = round(float(args.confidence), 2)

    source_ref = args.source_ref or (str(input_path).replace("\\", "/") if input_path else "")
    if source_ref:
        unit["source_ref"] = source_ref
        unit["raw_refs"] = merge_unique_list(unit.get("raw_refs"), [source_ref])

    for field_name, values in {
        "prev": args.prev or [],
        "next": args.next or [],
        "related": args.related or [],
        "supersedes": args.supersedes or [],
    }.items():
        if values:
            unit[field_name] = merge_unique_list(unit.get(field_name), values)

    write_yaml(Path(unit["_path"]), dump_unit_payload(unit))

    recent_change = args.recent_change
    if (args.affects_current or unit.get("affects_current")) and not recent_change:
        recent_change = f"{date_str}：续写 {unit.get('title', '')}"

    current_payload = dict(unit)
    current_payload["title"] = str(unit.get("title", ""))
    current_payload["summary"] = args.summary or str(unit.get("summary", ""))
    current_payload["details"] = incoming_details or str(unit.get("details", ""))
    current_payload["status"] = args.status or str(unit.get("status", "candidate"))
    current_payload["unit_type"] = args.unit_type or str(unit.get("unit_type", "context"))
    current_payload["thread"] = args.thread or str(unit.get("thread", ""))
    current_payload["affects_current"] = bool(args.affects_current or unit.get("affects_current"))

    if any([args.current_thread, args.current_problem, args.current_blocker, args.next_step, recent_change]):
        apply_current_updates(
            project_dir,
            payloads=[current_payload],
            date_str=date_str,
            current_thread=args.current_thread or (str(unit.get("thread", "")) if (args.affects_current or unit.get("affects_current")) else None),
            current_problem=args.current_problem or [],
            current_blocker=args.current_blocker or [],
            next_step=args.next_step or [],
            recent_change=recent_change,
        )

    print(f"[OK] Extended TraceUnit: {unit['_path']}")
    if any([args.current_thread, args.current_problem, args.current_blocker, args.next_step, recent_change]):
        print(f"[OK] Updated current: {project_dir / '01_CURRENT.md'}")

    session_output = maybe_write_session_output(
        project_dir=project_dir,
        output=args.session_output,
        days=int(args.session_days),
        limit=int(args.session_limit),
        thread=args.session_thread or args.thread or args.current_thread or str(unit.get("thread", "")),
        tags=args.session_tags or args.tags or list(unit.get("tags", [])),
        date_str=date_str,
    )
    if session_output:
        print(f"[OK] Refreshed session context pack: {session_output}")
        print(f"[OK] Updated index: {project_dir / '00_INDEX.md'}")
    return 0


def command_split_material(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    ensure_project_layout(project_dir)

    input_path, input_text = read_input_text(args.input)
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    source_type = args.source_type
    base_tags = [item.strip().lstrip("#") for item in (args.tags or []) if item.strip()]
    created = prepare_units_from_text(
        project_dir,
        input_text=input_text,
        source_path=input_path,
        source_type=source_type,
        date_str=date_str,
        project_name=args.project or project_dir.name,
        base_tags=base_tags,
        default_thread=args.thread,
    )
    if not created:
        print("[WARN] 未从原始材料中切分出有效片段。")
        return 0

    if args.dry_run:
        print(f"# Split Preview: {input_path.name}\n")
        print(f"- 片段数：{len(created)}")
        print(f"- 日期：{date_str}\n")
        for idx, payload in enumerate(created, start=1):
            print(f"## {idx}. {payload['title']}")
            print(f"- id: {payload['id']}")
            print(f"- thread: {payload['thread']}")
            print(f"- unit_type: {payload['unit_type']}")
            print(f"- status: {payload['status']}")
            print(f"- affects_current: {payload['affects_current']}")
            print(f"- tags: {' '.join('#' + tag for tag in payload['tags'])}")
            print(f"- summary: {payload['summary']}")
            print()
        return 0

    latest_thread, _, _, _, _ = write_created_units(
        project_dir,
        date_str=date_str,
        created=created,
        update_current_flag=bool(args.update_current),
    )
    session_output = maybe_write_session_output(
        project_dir=project_dir,
        output=args.session_output,
        days=int(args.session_days),
        limit=int(args.session_limit),
        thread=args.session_thread or args.thread or latest_thread,
        tags=args.session_tags or args.tags or [],
        date_str=date_str,
    )
    if session_output:
        print(f"[OK] Refreshed session context pack: {session_output}")
        print(f"[OK] Updated index: {project_dir / '00_INDEX.md'}")

    print(f"[OK] Split material into {len(created)} TraceUnit(s) from: {input_path}")
    for payload in created:
        print(f"- {payload['id']} | {payload['unit_type']} | {payload['thread']} | {payload['title']}")
    return 0


def command_capture_session(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    ensure_project_layout(project_dir)

    if not args.input and not args.stdin:
        raise ValueError("capture-session 需要提供 --input，或通过 --stdin 传入当前会话文本。")

    input_path, input_text = read_input_text(args.input, allow_stdin=bool(args.stdin))
    if not input_text.strip():
        print("[WARN] 当前会话输入为空，未生成 TraceUnit。")
        return 0

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    source_ref = args.source_ref or "conversation://current-session"
    source_type = args.source_type or "session"
    default_thread = args.thread
    base_tags = [item.strip().lstrip("#") for item in (args.tags or []) if item.strip()]
    pseudo_source_path = input_path
    if pseudo_source_path is None:
        pseudo_source_path = Path(source_ref)

    created = prepare_units_from_text(
        project_dir,
        input_text=input_text,
        source_path=pseudo_source_path,
        source_type=source_type,
        date_str=date_str,
        project_name=args.project or project_dir.name,
        base_tags=base_tags,
        default_thread=default_thread,
        force_single_unit=not bool(args.allow_multi_units),
    )
    if not created:
        print("[WARN] 当前会话未识别出可沉淀的有效状态片段。")
        return 0

    for payload in created:
        payload["source_ref"] = source_ref
        payload["raw_refs"] = [source_ref]

    explicit_target = getattr(args, "extend_target", None)
    force_new_unit = bool(getattr(args, "force_new_unit", False))
    auto_candidate: dict | None = None
    auto_reasons: list[str] = []
    auto_score = 0
    should_extend_existing = False

    if explicit_target:
        if len(created) != 1:
            raise ValueError("显式指定续写目标时，当前会话应只沉淀为一个 TraceUnit。")
        auto_candidate = resolve_trace_unit(project_dir, explicit_target)
        auto_reasons = ["用户显式指定续写目标"]
        should_extend_existing = True
    elif not force_new_unit and len(created) == 1 and not bool(args.allow_multi_units):
        auto_candidate, auto_reasons, auto_score = choose_continuation_candidate(
            project_dir,
            payload=created[0],
            date_str=date_str,
        )
        should_extend_existing = auto_candidate is not None

    if args.dry_run:
        print("# Session Capture Preview\n")
        print(f"- 片段数：{len(created)}")
        print(f"- 日期：{date_str}")
        print(f"- 来源：{source_ref}\n")
        for idx, payload in enumerate(created, start=1):
            print(f"## {idx}. {payload['title']}")
            print(f"- id: {payload['id']}")
            print(f"- thread: {payload['thread']}")
            print(f"- unit_type: {payload['unit_type']}")
            print(f"- status: {payload['status']}")
            print(f"- affects_current: {payload['affects_current']}")
            print(f"- tags: {' '.join('#' + tag for tag in payload['tags'])}")
            print(f"- summary: {payload['summary']}")
            if idx == 1 and explicit_target:
                print(f"- 写回决策：续写已有事件 -> {auto_candidate.get('id')} ({auto_candidate.get('title')})")
            elif idx == 1 and should_extend_existing and auto_candidate:
                print(f"- 写回决策：自动续写已有事件 -> {auto_candidate.get('id')} ({auto_candidate.get('title')})")
                print(f"- 判断分数：{auto_score}")
                print(f"- 判断依据：{'；'.join(auto_reasons)}")
            elif idx == 1 and force_new_unit:
                print("- 写回决策：强制新建事件")
            elif idx == 1 and len(created) == 1 and not bool(args.allow_multi_units):
                print("- 写回决策：新建事件")
                if auto_reasons:
                    print(f"- 保持新建的依据：{'；'.join(auto_reasons)}")
            print()
        return 0

    if should_extend_existing and auto_candidate:
        latest_thread, _, _, _, _ = extend_unit_with_payload(
            project_dir,
            unit=auto_candidate,
            payload=created[0],
            date_str=date_str,
            update_current_flag=not bool(args.skip_current),
        )
        session_output = maybe_write_session_output(
            project_dir=project_dir,
            output=args.session_output,
            days=int(args.session_days),
            limit=int(args.session_limit),
            thread=args.session_thread or latest_thread or args.thread or str(auto_candidate.get("thread", "")),
            tags=args.session_tags or args.tags or list(created[0].get("tags", [])),
            date_str=date_str,
        )
        if session_output:
            print(f"[OK] Refreshed session context pack: {session_output}")
            print(f"[OK] Updated index: {project_dir / '00_INDEX.md'}")
        if explicit_target:
            print(f"[OK] Captured session by extending TraceUnit: {auto_candidate.get('id')} | {auto_candidate.get('title')}")
        else:
            print(f"[OK] Captured session by auto-extending TraceUnit: {auto_candidate.get('id')} | {auto_candidate.get('title')}")
            if auto_reasons:
                print(f"[OK] Reason: {'；'.join(auto_reasons)}")
        return 0

    latest_thread, _, _, _, _ = write_created_units(
        project_dir,
        date_str=date_str,
        created=created,
        update_current_flag=not bool(args.skip_current),
    )
    session_output = maybe_write_session_output(
        project_dir=project_dir,
        output=args.session_output,
        days=int(args.session_days),
        limit=int(args.session_limit),
        thread=args.session_thread or args.thread or latest_thread,
        tags=args.session_tags or args.tags or [],
        date_str=date_str,
    )
    if session_output:
        print(f"[OK] Refreshed session context pack: {session_output}")
        print(f"[OK] Updated index: {project_dir / '00_INDEX.md'}")

    print(f"[OK] Captured session into {len(created)} TraceUnit(s).")
    if len(created) == 1 and auto_reasons and not should_extend_existing and not force_new_unit and not bool(args.allow_multi_units):
        print(f"[OK] 保持为新 TraceUnit：{'；'.join(auto_reasons)}")
    for payload in created:
        print(f"- {payload['id']} | {payload['unit_type']} | {payload['thread']} | {payload['title']}")
    return 0


def command_load_session(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    end_date = parse_date(args.end_date) or date.today()
    start_date = parse_date(args.start_date)
    if start_date is None:
        start_date = end_date - timedelta(days=max(int(args.days) - 1, 0))
    markdown = generate_session_pack(
        project_dir,
        days=int(args.days),
        limit=int(args.limit),
        thread=args.thread,
        tags=args.tags or [],
        status=args.status or DEFAULT_SESSION_STATUSES,
        start_date=start_date,
        end_date=end_date,
    )
    if args.output:
        output_path = Path(args.output).resolve()
        write_text(output_path, markdown)
        append_index_record(
            project_dir,
            date_str=date.today().isoformat(),
            record_path=normalize_index_path(project_dir, output_path),
            summary=build_session_index_summary(thread=args.thread, tags=args.tags or [], days=int(args.days)),
            tags=merge_unique_list(args.tags or [], ["session-summary"]),
        )
        print(f"[OK] Wrote session context pack: {output_path}")
        print(f"[OK] Updated index: {project_dir / '00_INDEX.md'}")
    else:
        print(markdown, end="")
    return 0


def command_generate_review(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    period = args.period
    end_date = parse_date(args.end_date) or date.today()
    start_date = parse_date(args.start_date)
    if start_date is None:
        default_days = {"daily": 1, "weekly": 7, "monthly": 30, "custom": int(args.days or 7)}
        span = int(args.days or default_days[period])
        start_date = end_date - timedelta(days=max(span - 1, 0))
    if start_date is None:
        raise ValueError("无法解析 review 开始日期。")

    units = load_trace_units(project_dir)
    filtered = filter_units(
        units,
        start_date=start_date,
        end_date=end_date,
        thread=args.thread,
        tags=args.tags or [],
        statuses=args.status or [],
    )
    filtered.sort(key=lambda item: (item.get("_date") or date.min, str(item.get("id", ""))), reverse=True)

    title = args.title or f"DevTrace {period.capitalize()} Review"
    markdown = build_review_markdown(
        project_dir,
        review_title=title,
        start_date=start_date,
        end_date=end_date,
        units=filtered[: args.limit] if args.limit else filtered,
    )
    if args.output:
        output_path = Path(args.output).resolve()
        write_text(output_path, markdown)
        review_tags = list(args.tags or [])
        if period in {"daily", "weekly", "monthly"}:
            review_tags = merge_unique_list(review_tags, ["review", period])
        else:
            review_tags = merge_unique_list(review_tags, ["review"])
        append_index_record(
            project_dir,
            date_str=date.today().isoformat(),
            record_path=normalize_index_path(project_dir, output_path),
            summary=build_review_index_summary(period=period, title=args.title),
            tags=review_tags,
        )
        print(f"[OK] Wrote review: {output_path}")
        print(f"[OK] Updated index: {project_dir / '00_INDEX.md'}")
    else:
        print(markdown, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize DevTrace project context, write TraceUnit entries, load session context, and generate reviews."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init-project", help="Create 00_INDEX.md, 01_CURRENT.md and trace/ directory.")
    init_parser.add_argument("--project-dir", required=True, help="Target project context directory.")
    init_parser.set_defaults(func=command_init)

    add_parser = sub.add_parser("add-unit", help="Write a TraceUnit and optionally update 01_CURRENT.md.")
    add_parser.add_argument("--project-dir", required=True, help="Target project context directory.")
    add_parser.add_argument("--input", help="Raw material file path.")
    add_parser.add_argument("--project", help="Project name. Defaults to project directory name.")
    add_parser.add_argument("--date", help="Date in YYYY-MM-DD format. Defaults to today.")
    add_parser.add_argument("--title", help="TraceUnit title.")
    add_parser.add_argument("--slug", help="Trace file slug.")
    add_parser.add_argument("--source-type", default="note", help="Source type such as chat/meeting/experiment/note/code/review/mixed.")
    add_parser.add_argument("--source-ref", help="Primary source reference.")
    add_parser.add_argument("--unit-type", required=True, help="Trace unit type.")
    add_parser.add_argument("--thread", required=True, help="Primary thread name.")
    add_parser.add_argument("--tags", nargs="*", default=[], help="Tags for this trace unit.")
    add_parser.add_argument("--summary", help="Summary override.")
    add_parser.add_argument("--details", help="Details override.")
    add_parser.add_argument("--evidence", nargs="*", default=[], help="Evidence lines.")
    add_parser.add_argument("--status", default="candidate", help="Status value.")
    add_parser.add_argument("--affects-current", action="store_true", help="Whether this unit affects current project state.")
    add_parser.add_argument("--importance", default="medium", help="Importance level.")
    add_parser.add_argument("--confidence", default=0.70, type=float, help="Confidence between 0 and 1.")
    add_parser.add_argument("--prev", nargs="*", default=[], help="Previous related TraceUnit ids.")
    add_parser.add_argument("--next", nargs="*", default=[], help="Next related TraceUnit ids.")
    add_parser.add_argument("--related", nargs="*", default=[], help="Related TraceUnit ids.")
    add_parser.add_argument("--supersedes", nargs="*", default=[], help="Superseded TraceUnit ids.")
    add_parser.add_argument("--current-thread", help="Update 当前主线.")
    add_parser.add_argument("--current-problem", nargs="*", default=[], help="Replace 当前问题 list.")
    add_parser.add_argument("--current-blocker", nargs="*", default=[], help="Replace 当前 blocker list.")
    add_parser.add_argument("--next-step", nargs="*", default=[], help="Replace 下一步 list.")
    add_parser.add_argument("--recent-change", help="Recent change line for 01_CURRENT.md.")
    add_parser.add_argument("--session-output", help="Optional output path to refresh session context pack after writeback.")
    add_parser.add_argument("--session-days", type=int, default=7, help="Day window used when refreshing session context pack.")
    add_parser.add_argument("--session-limit", type=int, default=5, help="TraceUnit limit used when refreshing session context pack.")
    add_parser.add_argument("--session-thread", help="Optional thread filter for refreshed session context pack.")
    add_parser.add_argument("--session-tags", nargs="*", default=[], help="Optional tag filters for refreshed session context pack.")
    add_parser.set_defaults(func=command_add)

    extend_parser = sub.add_parser("extend-unit", help="Append new progress into an existing TraceUnit and optionally update 01_CURRENT.md.")
    extend_parser.add_argument("--project-dir", required=True, help="Target project context directory.")
    extend_parser.add_argument("--target", required=True, help="TraceUnit id, file name, or path to extend.")
    extend_parser.add_argument("--input", help="Optional raw material file path.")
    extend_parser.add_argument("--date", help="Writeback date in YYYY-MM-DD format. Defaults to today.")
    extend_parser.add_argument("--source-type", help="Optional source type override.")
    extend_parser.add_argument("--source-ref", help="Optional logical source reference for this continuation.")
    extend_parser.add_argument("--unit-type", help="Optional unit type override.")
    extend_parser.add_argument("--thread", help="Optional thread override.")
    extend_parser.add_argument("--tags", nargs="*", default=[], help="Extra tags to merge into the existing TraceUnit.")
    extend_parser.add_argument("--summary", help="Optional summary replacement after this continuation.")
    extend_parser.add_argument("--details", help="Details text to append. Defaults to --input content.")
    extend_parser.add_argument("--evidence", nargs="*", default=[], help="Evidence lines to merge.")
    extend_parser.add_argument("--status", help="Optional status override.")
    extend_parser.add_argument("--affects-current", action="store_true", help="Mark the continued TraceUnit as affecting current state.")
    extend_parser.add_argument("--importance", help="Optional importance override.")
    extend_parser.add_argument("--confidence", type=float, help="Optional confidence override.")
    extend_parser.add_argument("--prev", nargs="*", default=[], help="Previous related TraceUnit ids to merge.")
    extend_parser.add_argument("--next", nargs="*", default=[], help="Next related TraceUnit ids to merge.")
    extend_parser.add_argument("--related", nargs="*", default=[], help="Related TraceUnit ids to merge.")
    extend_parser.add_argument("--supersedes", nargs="*", default=[], help="Superseded TraceUnit ids to merge.")
    extend_parser.add_argument("--current-thread", help="Update 当前主线.")
    extend_parser.add_argument("--current-problem", nargs="*", default=[], help="Replace 当前问题 list.")
    extend_parser.add_argument("--current-blocker", nargs="*", default=[], help="Replace 当前 blocker list.")
    extend_parser.add_argument("--next-step", nargs="*", default=[], help="Replace 下一步 list.")
    extend_parser.add_argument("--recent-change", help="Recent change line for 01_CURRENT.md.")
    extend_parser.add_argument("--session-output", help="Optional output path to refresh session context pack after writeback.")
    extend_parser.add_argument("--session-days", type=int, default=7, help="Day window used when refreshing session context pack.")
    extend_parser.add_argument("--session-limit", type=int, default=5, help="TraceUnit limit used when refreshing session context pack.")
    extend_parser.add_argument("--session-thread", help="Optional thread filter for refreshed session context pack.")
    extend_parser.add_argument("--session-tags", nargs="*", default=[], help="Optional tag filters for refreshed session context pack.")
    extend_parser.set_defaults(func=command_extend)

    split_parser = sub.add_parser("split-material", help="Split one raw material file into multiple TraceUnit entries.")
    split_parser.add_argument("--project-dir", required=True, help="Target project context directory.")
    split_parser.add_argument("--input", required=True, help="Raw material file path.")
    split_parser.add_argument("--project", help="Project name. Defaults to project directory name.")
    split_parser.add_argument("--date", help="Date in YYYY-MM-DD format. Defaults to today.")
    split_parser.add_argument("--source-type", default="note", help="Source type such as chat/meeting/experiment/note/code/review/mixed.")
    split_parser.add_argument("--thread", help="Default thread when auto inference misses.")
    split_parser.add_argument("--tags", nargs="*", default=[], help="Base tags applied to all generated TraceUnit.")
    split_parser.add_argument("--update-current", action="store_true", help="Update 01_CURRENT.md from generated high-value units.")
    split_parser.add_argument("--dry-run", action="store_true", help="Preview split result without writing files.")
    split_parser.add_argument("--session-output", help="Optional output path to refresh session context pack after writeback.")
    split_parser.add_argument("--session-days", type=int, default=7, help="Day window used when refreshing session context pack.")
    split_parser.add_argument("--session-limit", type=int, default=5, help="TraceUnit limit used when refreshing session context pack.")
    split_parser.add_argument("--session-thread", help="Optional thread filter for refreshed session context pack.")
    split_parser.add_argument("--session-tags", nargs="*", default=[], help="Optional tag filters for refreshed session context pack.")
    split_parser.set_defaults(func=command_split_material)

    session_capture_parser = sub.add_parser(
        "capture-session",
        help="Capture the current conversation text into TraceUnit and optionally refresh current / session output.",
    )
    session_capture_parser.add_argument("--project-dir", required=True, help="Target project context directory.")
    session_capture_parser.add_argument("--input", help="Optional current-session text file path.")
    session_capture_parser.add_argument("--stdin", action="store_true", help="Read current-session text from stdin.")
    session_capture_parser.add_argument("--project", help="Project name. Defaults to project directory name.")
    session_capture_parser.add_argument("--date", help="Date in YYYY-MM-DD format. Defaults to today.")
    session_capture_parser.add_argument(
        "--source-type",
        default=None,
        help="Source type for current-session capture. Defaults to session.",
    )
    session_capture_parser.add_argument(
        "--source-ref",
        help="Logical source reference. Defaults to conversation://current-session.",
    )
    session_capture_parser.add_argument("--thread", help="Default thread when auto inference misses.")
    session_capture_parser.add_argument("--tags", nargs="*", default=[], help="Base tags applied to all generated TraceUnit.")
    session_capture_parser.add_argument("--extend-target", help="Explicitly continue one existing TraceUnit instead of auto deciding.")
    session_capture_parser.add_argument("--force-new-unit", action="store_true", help="Always create a new TraceUnit and skip auto continuation matching.")
    session_capture_parser.add_argument("--allow-multi-units", action="store_true", help="Allow one current session to split into multiple TraceUnit.")
    session_capture_parser.add_argument("--dry-run", action="store_true", help="Preview session capture result without writing files.")
    session_capture_parser.add_argument("--skip-current", action="store_true", help="Do not update 01_CURRENT.md.")
    session_capture_parser.add_argument("--session-output", help="Optional output path to refresh session context pack after writeback.")
    session_capture_parser.add_argument("--session-days", type=int, default=7, help="Day window used when refreshing session context pack.")
    session_capture_parser.add_argument("--session-limit", type=int, default=5, help="TraceUnit limit used when refreshing session context pack.")
    session_capture_parser.add_argument("--session-thread", help="Optional thread filter for refreshed session context pack.")
    session_capture_parser.add_argument("--session-tags", nargs="*", default=[], help="Optional tag filters for refreshed session context pack.")
    session_capture_parser.set_defaults(func=command_capture_session)

    load_parser = sub.add_parser("load-session", help="Build a session context pack from current/index/TraceUnit.")
    load_parser.add_argument("--project-dir", required=True, help="Target project context directory.")
    load_parser.add_argument("--days", type=int, default=7, help="Recent day window. Defaults to 7.")
    load_parser.add_argument("--start-date", help="Custom start date in YYYY-MM-DD.")
    load_parser.add_argument("--end-date", help="Custom end date in YYYY-MM-DD. Defaults to today.")
    load_parser.add_argument("--thread", help="Restrict to one thread.")
    load_parser.add_argument("--tags", nargs="*", default=[], help="Optional tag filters.")
    load_parser.add_argument("--status", nargs="*", default=DEFAULT_SESSION_STATUSES, help="Preferred statuses for ranking.")
    load_parser.add_argument("--limit", type=int, default=5, help="Maximum recommended TraceUnit count.")
    load_parser.add_argument("--output", help="Optional markdown output path.")
    load_parser.set_defaults(func=command_load_session)

    review_parser = sub.add_parser("generate-review", help="Generate a daily/weekly/monthly review from TraceUnit.")
    review_parser.add_argument("--project-dir", required=True, help="Target project context directory.")
    review_parser.add_argument("--period", choices=["daily", "weekly", "monthly", "custom"], default="weekly", help="Review period.")
    review_parser.add_argument("--days", type=int, help="Custom day span. Defaults depend on period.")
    review_parser.add_argument("--start-date", help="Custom start date in YYYY-MM-DD.")
    review_parser.add_argument("--end-date", help="Custom end date in YYYY-MM-DD. Defaults to today.")
    review_parser.add_argument("--thread", help="Restrict to one thread.")
    review_parser.add_argument("--tags", nargs="*", default=[], help="Optional tag filters.")
    review_parser.add_argument("--status", nargs="*", default=[], help="Optional status filters.")
    review_parser.add_argument("--limit", type=int, default=20, help="Maximum TraceUnit count to include.")
    review_parser.add_argument("--title", help="Custom review title.")
    review_parser.add_argument("--output", help="Optional markdown output path.")
    review_parser.set_defaults(func=command_generate_review)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

"""SkillHub → 记忆中枢 回写草稿卡生成。

对齐中枢 ingest 契约(sync.ingest):
- 草稿必须写在 <root>/.sync/drafts/<platform>_draft/ 根目录(ingest 只 glob 根, 放
  candidates/ 子目录不会被提升) → 这里必须写根。
- 卡 frontmatter 须过 validate_card: type ∈ TYPE_DIR 键、tags、updated 齐备。
- 仅白名单低风险卡型(exp/note/project)可生成自动提升草稿; rule/methodology 等
  禁直写权威区 → 拒绝(rule 由人工走 pending 流程, 不在此自动落)。
- 幂等: 同名草稿若已存在且内容一致, 不重复落档(覆盖为幂等操作)。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import yaml

from bridge.config import HubConfig

# 默认回写平台名(承接 hub.config.yaml 语义, 可被调用方覆盖)
DEFAULT_PLATFORM = "trae"


class CardKind(str, Enum):
    """中枢卡型(与 sync.TYPE_DIR 键对齐)。"""

    EXP = "exp"
    NOTE = "note"
    PROJECT = "project"

    @classmethod
    def in_whitelist(cls, kind: str, whitelist: list[str]) -> bool:
        """kind 是否命中白名单. 空白名单视为全部允许(由 config 决定)."""
        if not whitelist:
            return True
        return kind in whitelist


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _slug(name: str) -> str:
    """文件名安全化: 去空格/非法字符, 转小写连字."""
    s = re.sub(r"[^\w\-]+", "-", name.strip().lower())
    return s.strip("-") or "card"


def _render_frontmatter(card_type: str, tags: list[str], body: str) -> str:
    """渲染带 frontmatter 的卡文本(直接 yaml dump, 保证合规)."""
    meta = {
        "type": card_type,
        "tags": list(tags),
        "updated": _today_iso(),
        "status": "candidate",
        "reuse_count": 0,
    }
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{fm}\n---\n\n{body.rstrip()}\n"


def writeback_card(
    cfg: HubConfig,
    *,
    platform: str = DEFAULT_PLATFORM,
    hub_root: str | Path,
    name: str,
    card_type: str,
    body: str,
    tags: list[str] | None = None,
) -> Path:
    """生成一张合规草稿卡, 写到中枢 draft 根目录。

    返回草稿路径 .md。触白名单外卡型抛 ValueError(拒绝越权直写权威区)。
    """
    if not CardKind.in_whitelist(card_type, cfg.candidate_type_whitelist):
        raise ValueError(
            f"卡型 {card_type!r} 不在回写白名单 {cfg.candidate_type_whitelist}, "
            f"禁直写权威区(rule/methodology 走 pending/人工)"
        )
    root = Path(hub_root)
    ddir = root / ".sync" / "drafts" / f"{platform}_draft"
    ddir.mkdir(parents=True, exist_ok=True)
    dest = ddir / f"{_slug(name)}.md"
    text = _render_frontmatter(card_type, tags or [], body)
    dest.write_text(text, encoding="utf-8")
    return dest

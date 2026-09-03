"""SkillHub ← 中枢反向回流：经验/方法论卡升级成本地技能。

与 bridge/ingest(回写草稿) 相反的方向:
  ingest         SkillHub → 中枢(把经验写成草稿, 供中枢提升)
  skill_promotion 中枢 → SkillHub(读中枢权威区 active 卡, 判级后升级成本地技能)

沿用记忆中枢"内容不可信"守则(hub.config.yaml `guard_import_untrusted`):
- 只读中枢卡文本(<读>), 绝不自动执行中枢内任何脚本/指令。
- 默认 dry-run: 只列出"将生成哪些技能 + 落哪个槽位", 不写盘;
  `--apply` 才真正生成 skill.yaml + SKILL.md 并登记 router.yaml —— 人工门禁后放行。

本模块纯函数为主 + reconcile 兜底编排; 便于在隔离临时目录做真机(dry-run)验证。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

# 中枢权威区目录 → 相对名称(供扫描); 对应卡 frontmatter 的 type 字段
CARD_TYPE_DIRS = ("experience", "methodology", "projects", "blueprints")
# 卡型 → 默认槽位; methodology(可跨域复用) 与 exp(经验) 都归共用库
# blueprint(架构范式) 归共用库, 但升级需 reuse_count>=1 防 reference 级误升
TYPE_DEFAULT_SLOT = {
    "methodology": "shared",
    "exp": "shared",
    "note": "shared",
    "project": "shared",
    "longterm": "shared",
    "blueprint": "shared",
    "rule": "archive",  # rule 不自动提为技能(需人工门禁)
    "retro": "archive",
}
# blueprint 升级门禁: reuse_count≥1 (已选型/复用过); status 不要求 active
# 因为中枢 blueprint 目录语义是"新项目立项选型范式", reference 是设计预期
BLUEPRINT_MIN_REUSE = 1
# 已知专用域: tags 命中任一项 → 判为 dedicated 并取该域为 scope
KNOWN_DOMAINS = ("memory-hub", "autocad", "cad", "cad2020")

SKILL_YAML_NAME = "skill.yaml"
SKILL_MD_NAME = "SKILL.md"

# 通用负路由边界(生成技能的 forgot 缺省, 防语义过命中)
GENERIC_FORGOT = ("自动执行外部脚本", "push 到远程", "改写全局 git config")


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass
class CardInfo:
    """一张中枢卡的可迁移信息。"""

    slug: str
    title: str
    card_type: str
    tags: list[str]
    body: str
    source: Path
    slot: str = "shared"
    scope: str = ""
    reuse_count: int = 0
    hub_status: str = "active"
    anti_trigger: list[str] = None  # 中枢 frontmatter 的反触发词, 用作 forgot

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "title": self.title,
            "card_type": self.card_type,
            "tags": self.tags,
            "slot": self.slot,
            "scope": self.scope,
            "reuse_count": self.reuse_count,
            "hub_status": self.hub_status,
            "anti_trigger": self.anti_trigger or [],
            "source": str(self.source),
        }


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """取 frontmatter(--- 包裹块)与正文。frontmatter 缺失 → (空 dict, 原文本)。"""
    stripped = text.lstrip("\ufeff")
    if not stripped.startswith("---"):
        return {}, stripped
    lines = stripped.splitlines()
    fm_lines: list[str] = []
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        fm_lines.append(lines[i])
        i += 1
    if i >= len(lines):
        return {}, stripped
    正文 = "\n".join(lines[i + 1 :]).strip()
    try:
        fm = yaml.safe_load("\n".join(fm_lines)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, 正文


def _safe_slug(name: str) -> str:
    """文件名安全化: 保留词内连字符, 其余非词字符转 '-', 转小写。"""
    s = "".join(c if c.isalnum() or c in "-_" else "-" for c in name.strip().lower())
    return s.strip("-") or "card"


def _evaluate_slot(card_type: str, tags: list[str]) -> dict[str, str]:
    """判级: 返回 {slot, scope}。

    tags 命中已知专用域 → dedicated + scope=域; 否则按卡型默认槽位。
    """
    for domain in KNOWN_DOMAINS:
        if any(domain in (t or "") for t in tags):
            return {"slot": "dedicated", "scope": domain}
    return {"slot": TYPE_DEFAULT_SLOT.get(card_type, "shared"), "scope": ""}


def scan_hub_cards(
    hub_root: str | Path,
    card_type_dirs: tuple[str, ...] = CARD_TYPE_DIRS,
) -> list[CardInfo]:
    """扫描中枢权威区卡, 产出可迁移候选(仅读, 不写盘)。

    过滤规则:
    - 只收 frontmatter type ∈ TYPE_DEFAULT_SLOT 的卡
    - 非 blueprint 卡要求 status=active(已验证)
    - blueprint 卡不要求 active(中枢 blueprint 目录=选型范式,
      reference 是设计预期), 但要求 reuse_count≥BLUEPRINT_MIN_REUSE
    """
    root = Path(hub_root)
    cards: list[CardInfo] = []
    for sub in card_type_dirs:
        d = root / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            fm, body = _parse_frontmatter(f.read_text(encoding="utf-8"))
            card_type = str(fm.get("type", ""))
            if card_type not in TYPE_DEFAULT_SLOT:
                continue  # 只处理目录对应的已知卡型
            status = str(fm.get("status", "")).lower()
            # blueprint 语义不同: 中枢 blueprint 目录 = "新项目立项选型范式"
            # status=reference 是设计预期(选型参考≠已验证技能), 不过滤
            if card_type != "blueprint" and status != "active":
                continue
            # blueprint 门禁: reuse_count≥1 (已选型/复用过至少一次)
            if card_type == "blueprint":
                rc = int(fm.get("reuse_count", 0) or 0)
                if rc < BLUEPRINT_MIN_REUSE:
                    continue
            # title 提取: 跳过中枢 blueprint 卡的通用首行(提炼自/来源:等)
            title = "(无标题)"
            for ln in body.splitlines():
                stripped = ln.lstrip("# ").strip()
                if len(stripped) >= 6 and not stripped.startswith(("提炼自", "来源:", "来源 ", "出处")):
                    title = stripped
                    break
            # slug 优先级: fm.name → f.stem(英文文件名) → title(中文描述)
            slug = _safe_slug(str(fm.get("name") or f.stem or title))
            tags = [str(t).strip() for t in (fm.get("tags") or []) if str(t).strip()]
            slot_info = _evaluate_slot(card_type, tags)
            reuse_count = int(fm.get("reuse_count", 0) or 0)
            # 中枢反触发词 → 用作 forgot; 没给时 fallback GENERIC_FORGOT
            anti_trigger = [
                str(a).strip() for a in (fm.get("anti_trigger") or []) if str(a).strip()
            ] or list(GENERIC_FORGOT)
            cards.append(
                CardInfo(
                    slug=slug,
                    title=title,
                    card_type=card_type,
                    tags=tags,
                    body=body,
                    source=f,
                    reuse_count=reuse_count,
                    hub_status=status,
                    anti_trigger=anti_trigger,
                    **slot_info,
                )
            )
    return cards


def _extract_headings(body: str) -> list[str]:
    """从卡正文提取一级(##)标题, 作为生成 SKILL.md 的参考 section 名。"""
    return [ln.lstrip("# ").strip() for ln in body.splitlines() if ln.startswith("## ")]


# 从中枢 methodology 卡提取的 SKILL 撰写检查清单（authoring best practices）
# 来源: build-iterated-agentic-loop / improve-claude-md-important-if /
#       design-control-loop / show-me-visuals / t1-iterative-verification
AUTHORING_CHECKLIST = {
    "build_iterated": [
        "scope 明确可改/只读边界",
        "validation 命令必须在提交前通过",
        "每 loop 限 1 个 open PR（PR bounding）",
        "agent-memory 携带两轮间稳定反馈",
        "skill/prompt/memory 单一来源, 不重复",
    ],
    "improve_claude": [
        "基础上下文裸放, 条件规则用 <important if> 包裹",
        "触发词窄而具体, 禁止宽泛条件",
        "Less is more: 删 linter 管辖/代码片段/含糊指令",
        "保留所有命令表",
    ],
    "design_control_loop": [
        "五要素完整: SetPoint→Sensor→Controller→Actuator→Disturbance",
        "传感器可稳定测量客观属性",
        "组件先本地跑通再接 CI",
        "人留在 loop 上(/iterate 评论反馈)",
    ],
    "show_me": [
        "按内容选最小视图: 逻辑→伪代码/控制流→调用树/UI→组件树",
        "视觉紧贴支撑短文本",
        "只保留回答问题所需信息",
    ],
    "verify_loop": [
        "静态 T0 通过(纯语法/结构断言, 零执行副作用)",
        "T1 迭代验证: 真实场景最小 demo 跑通, 不是一次性定论",
        "risk 分级执行: 低风险直接跑 / 中风险沙盒 / 高风险能沙盒先沙盒",
        "结果回写 skill.yaml verification 字段(status/t1_record/reuse_count)",
        "reference→active 需真跑通, 不是静态分析升级",
        "archived 永远不入候选, 大版本更新或有未覆盖功能才重入",
    ],
}


def render_skill_yaml(card: CardInfo) -> str:
    """渲染一张 skill.yaml(元数据), 对齐 skills/govern/skill.yaml.tmpl 契约。

    含 verification 字段(对齐中枢 T0→T1→active 链路),
    blueprint 卡额外标注 blueprint 证据等级。
    """
    is_blueprint = card.card_type == "blueprint"
    # verification: 对齐中枢卡的验证状态; 新升级默认 reference, 待真机试用转 active
    verification = {
        "status": "reference",
        "t1_record": "",
        "reuse_count": card.reuse_count,
        "last_verified": "",
    }
    fm = {
        "name": card.slug,
        "version": "0.1.0",
        "slot": card.slot,
        "scope": card.scope,
        "status": "reference",
        "reuse_count": 0,
        "updated": _today_iso(),
        "evidence": {"gate": "required", "grade": "pending"},
        "verification": verification,
        "invoke": "user",
        "description_model": card.title,
        "description_human": card.title,
        "trigger": [card.title.strip()] + card.tags,
        "forgot": list(card.anti_trigger or GENERIC_FORGOT),
        "instructions": SKILL_MD_NAME,
        "references": [str(card.source).replace("\\", "/")],
    }
    if is_blueprint:
        fm["blueprint_source"] = card.source.name
        fm["blueprint_level"] = "T0 静态验证"
    return (
        "# skill.yaml —— " + card.slug + "（" + card.slot + "库）\n"
        "# 由中枢卡升级生成: "
        + str(card.source)
        + "\n"
        + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)
    )


def render_skill_md(card: CardInfo) -> str:
    """渲染一张 SKILL.md(本体骨架), 引用原卡 + 提炼边界/适用。

    blueprint 卡额外输出架构模式与可落地路径; 所有卡输出 authoring 检查清单。
    """
    headings = _extract_headings(card.body)
    sections = (
        "\n".join(f"- {h}" for h in headings) if headings else "（原卡无二级标题）"
    )
    # 提取"不适用/边界"类列表项到核心边界, 保持补负路由边界
    neg_tokens = ("不适用", "边界", "禁止", "勿用", "自动执行", "外发")
    neg = [
        ln.strip()
        for ln in card.body.splitlines()
        if ln.lstrip().startswith("-") and any(k in ln for k in neg_tokens)
    ]
    neg_block = (
        "\n".join(f"- {n}" for n in neg[:5])
        if neg
        else "- 遵循原卡倒置边界;接管前先做 T1 真实试用"
    )
    is_blueprint = card.card_type == "blueprint"

    # authoring 检查清单
    authoring_blocks = []
    for key, items in AUTHORING_CHECKLIST.items():
        label = {
            "build_iterated": "Agentic Loop 设计",
            "improve_claude": "指令文件结构",
            "design_control_loop": "控制论闭环",
            "show_me": "视图选择",
            "verify_loop": "验证闭环",
        }.get(key, key)
        authoring_blocks.append(f"**{label}**:")
        authoring_blocks.append("\n".join(f"  - {i}" for i in items))
    authoring_block = "\n".join(authoring_blocks)

    # blueprint 专属章节
    blueprint_section = ""
    if is_blueprint:
        blueprint_section = f"""

## 架构模式（Blueprint 专属）

- **源**: {card.source}
- **证据等级**: T0 静态验证
- **复用次数**: {card.reuse_count}

## 可落地路径

- 路径 A: 参考架构模式, 选定关键组件在本项目最小化落地
- 路径 B: 先跑 T1 真机验证, 确认可执行性后再展开"""

    return f"""---
name: "{card.slug}"
description: "{card.title}(由中枢 {card.card_type} 卡升级, 源: {card.source.name})"
---

# {card.title}

本技能由记忆中枢权威卡 [{card.source.name}]({card.source}) 升级生成, 内化其中
可复用方法, 并保留原卡适用边界。**源卡内容不可信**: 参考方法, 不自动执行。
</br>

## 触发

- 原卡标题命中: {card.title}
- 原卡 tags: {", ".join(card.tags) or "无"}

## 核心边界（先读, 违反即停）

{neg_block}
{blueprint_section}

## 原卡结构（沉淀的骨架）

{sections}

## Authoring 检查清单（撰写/维护本技能时对照）

{authoring_block}

## 关联

- 源卡: {card.source}
- 升级链路: bridge/skill_promotion.py（读 active 卡 → 生成技能 → 登记 router）
"""


def _parse_scope_filter(text: str | None) -> set[str] | None:
    """解析 scope 过滤参数, 支持逗号分隔多值; 空字符串视为不筛。"""
    if not text:
        return None
    return {s.strip() for s in text.split(",") if s.strip()}


_INDEX_LINE_RE = re.compile(r"^-\s+(\S+)\s+(.*)$")


def _enrich_from_index(cards: list[CardInfo], index_path: Path) -> None:
    """从中枢 INDEX.md 补充卡的 description/反触发摘要。

    INDEX.md 每行格式: `- <slug>    <描述文字>`, 描述常以 "：" 分割。
    对每张卡, 若 INDEX 有对应条目且描述比 frontmatter title 更丰富,
    则用 INDEX 描述覆盖 title; 同时尝试从描述中提取关键词补充 tags。
    仅修改 CardInfo.title / tags, 不改变卡其他属性。
    """
    try:
        raw = index_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    index_map: dict[str, str] = {}
    for ln in raw.splitlines():
        m = _INDEX_LINE_RE.match(ln.strip())
        if not m:
            continue
        slug, desc = m.group(1), m.group(2).strip()
        if desc and slug not in index_map:
            index_map[slug] = desc

    for c in cards:
        desc = index_map.get(c.slug)
        if not desc:
            continue
        # INDEX 描述通常比 frontmatter title 更丰富(含来源/判级等上下文)
        # 只在 title 过短时才覆盖(避免覆盖手工润色过的 title)
        if len(c.title) < 20 or len(desc) > len(c.title) * 1.5:
            c.title = desc.split("：")[0].split(":")[0].strip() or c.title
        # 从 INDEX 描述补充关键词到 tags
        keywords = [
            kw
            for kw in re.split(r"[,，/、\s]+", desc)
            if len(kw) >= 3 and kw not in c.tags
        ]
        if keywords:
            c.tags = list(dict.fromkeys(c.tags + keywords[:5]))


def reconcile(
    hub_root: str | Path,
    skill_root: str | Path,
    *,
    apply: bool = False,
    router_path: str | Path | None = None,
    card_type_filter: str | None = None,  # 只处理指定卡型(blueprint/methodology/exp/project)
    hub_status_filter: str | None = None,  # 只处理指定中枢状态(active/reference)
    slug_filter: str | None = None,  # 只处理指定 slug(逗号多值, 精确匹配)
    scope_filter: str | None = None,  # 只处理指定 scope(逗号多值, 支持空 scope 用 '<empty>' 匹配)
    batch_size: int = 0,  # 分批大小, 0 表示不分批
    batch_index: int = 0,  # 分批索引, 从 0 开始
) -> list[dict]:
    """反向回流编排: 扫描 → 判级 → (apply) 生成技能文件 + 登记 router。

    返回动作清单(每项含 slug/action/目标路径); dry_run(default) 只列不写。
    幂等: 若技能目录存在或 router 已登记 → action=skip, 不重复生成。

    筛选参数(card_type_filter / hub_status_filter / slug_filter / scope_filter)
    均支持逗号分隔多值或 None(不筛), AND 叠加。

    分批: batch_size>0 时, 候选卡分批处理, batch_index 指定第几批。
    用于 175 张候选卡分批 reconcile, 避免 --apply 范围过大。

    中枢 INDEX.md 补充: 自动尝试读 INDEX.md 补充 description/反触发摘要。
    """
    config_path = Path(__file__).parent.parent / "hub.config.yaml"
    base = Path(skill_root)
    router = router_path or config_path.parent / "router" / "router.yaml"

    # 解析筛选参数
    type_filters = _parse_scope_filter(card_type_filter)
    status_filters = _parse_scope_filter(hub_status_filter)
    slug_filters = _parse_scope_filter(slug_filter)
    scope_filters = _parse_scope_filter(scope_filter)

    all_cards = scan_hub_cards(hub_root)
    # 应用筛选(四层 AND)
    if type_filters or status_filters or slug_filters or scope_filters:
        all_cards = [
            c
            for c in all_cards
            if (not type_filters or c.card_type in type_filters)
            and (not status_filters or c.hub_status in status_filters)
            and (not slug_filters or c.slug in slug_filters)
            and (
                not scope_filters
                or (c.scope or "<empty>") in scope_filters
            )
        ]

    # G3: 尝试读 INDEX.md 补充卡 description/反触发摘要
    hub = Path(hub_root)
    index_path = hub / "INDEX.md"
    if index_path.is_file():
        _enrich_from_index(all_cards, index_path)

    # 分批
    if batch_size > 0 and len(all_cards) > batch_size:
        start = batch_index * batch_size
        all_cards = all_cards[start : start + batch_size]
    actions: list[dict] = []
    if not apply:
        for card in all_cards:
            dest_dir = (
                base / card.slot / card.scope / card.slug
                if card.scope
                else base / card.slot / card.slug
            )
            actions.append(
                {
                    "slug": card.slug,
                    "card_type": card.card_type,
                    "slot": card.slot,
                    "scope": card.scope,
                    "hub_status": card.hub_status,
                    "action": "propose",
                    "target": str(dest_dir),
                    "source": str(card.source),
                }
            )
        return actions

    for card in all_cards:
        if card.scope:
            dest_dir = base / card.slot / card.scope / card.slug
        else:
            dest_dir = base / card.slot / card.slug

        skill_exists = (dest_dir / SKILL_YAML_NAME).exists()
        router_exists = _router_has_name(router, card.slug)

        if skill_exists and router_exists:
            # 完整已存在 → skip
            actions.append(
                {
                    "slug": card.slug,
                    "action": "skip",
                    "target": str(dest_dir),
                    "reason": "技能目录 + router 均已存在",
                }
            )
            continue

        # G2: 技能目录/路由登记不一致 → 提示并补全 router 或 跳过生成
        if not skill_exists and router_exists:
            actions.append(
                {
                    "slug": card.slug,
                    "action": "skip",
                    "target": str(dest_dir),
                    "reason": "⚠ router 已登记但技能目录不存在 — 可能之前 apply 被中断; 如需重建请先手动删除 router.yaml 条目",
                }
            )
            continue

        if skill_exists and not router_exists:
            # 补登记 router, 不覆盖已有技能文件
            _register_router(router, card)
            actions.append(
                {
                    "slug": card.slug,
                    "action": "patch-router",
                    "target": str(dest_dir),
                    "reason": "技能目录已存在但 router 缺失 — 补登记",
                }
            )
            continue

        # 正常: 两者都不存在 → 全量生成
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / SKILL_YAML_NAME).write_text(
            render_skill_yaml(card), encoding="utf-8"
        )
        (dest_dir / SKILL_MD_NAME).write_text(render_skill_md(card), encoding="utf-8")
        _register_router(router, card)
        actions.append(
            {
                "slug": card.slug,
                "action": "apply",
                "target": str(dest_dir),
                "reason": "生成技能 + 登记 router",
            }
        )
    return actions


def _router_has_name(router_path: str | Path, slug: str) -> bool:
    """检查 router.yaml 是否已登记指定 slug。"""
    try:
        p = Path(router_path)
        if not p.is_file():
            return False
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return any(s.get("name") == slug for s in data.get("skills", []))
    except (OSError, yaml.YAMLError):
        return False


def _register_router(router_path: str | Path, card: CardInfo) -> bool:
    """把技能登记进 router.yaml(skills 列表), 已存在同名则跳过(幂等)。

    触发/反触发从卡 title 与 GENERIC_FORGOT 派生, 与生成 skill.yaml 保持一致。
    """
    p = Path(router_path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    skills = data.setdefault("skills", [])
    if any(s.get("name") == card.slug for s in skills):
        return False
    skills.append(
        {
            "name": card.slug,
            "slot": card.slot,
            "scope": card.scope,
            "invoke": "user",
            "description_model": card.title,
            "description_human": card.title,
            "trigger": [card.title.strip()] + card.tags,
            "forgot": list(card.anti_trigger or GENERIC_FORGOT),
            "weight": 1.0,
        }
    )
    p.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return True

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""描述生成器：把 router.yaml 的 trigger/forgot 压缩进 SKILL.md description。

原理：Hermes 技能索引只读 SKILL.md frontmatter 的 description（首行 ~57 字符可见），
router.yaml 的双轨触发词在 Hermes 侧不生效。本脚本按 router.yaml 为唯一事实源，
将 trigger/forgot 编译进各平台可读的 description，实现"路由补偿"。

用法：
    python gen_descriptions.py                 # 处理全部 router 中有 SKILL.md 的技能
    python gen_descriptions.py --dry-run       # 只预览不写盘
    python gen_descriptions.py --name xxx      # 只处理单个技能

规则：
    - 新 description = 原描述 + " Use when <triggers 前3个>" + "；勿用于 <forgot 前2个>"
      （中文技能用中文连接词，英文技能用英文）
    - 只改 frontmatter 内 description 行，正文不动；写入前打印 diff 摘要。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml  # PyYAML；SkillHub venv 若无则 pip install pyyaml

HUB_ROOT = Path(r"d:/AIwork/20260821-Fan-SkillHub")
ROUTER_YAML = HUB_ROOT / "router" / "router.yaml"
SLOT_DIRS = {"shared": HUB_ROOT / "skills/shared", "dedicated": HUB_ROOT / "skills/dedicated"}

# description 硬上限（Hermes 索引截断 ~57 字符可见，但全文仍入库，控制总量即可）
MAX_DESC_LEN = 220


def find_skill_md(name: str) -> Path | None:
    """在 shared/dedicated 下定位 <name>/SKILL.md。"""
    for slot_dir in SLOT_DIRS.values():
        # 支持一层分类子目录（如 productivity/computer-use）
        hits = list(slot_dir.glob(f"**/{name}/SKILL.md"))
        if hits:
            return hits[0]
    return None


def is_cjk(text: str) -> bool:
    """按中文字符占比判断语言，决定连接词风格。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk > len(text) * 0.15


def build_description(old: str, triggers: list[str], forgot: list[str]) -> str:
    """压缩路由信息进描述：Use when + 负边界。"""
    use_part = "、".join(triggers[:3]) if is_cjk(old or "") else ", ".join(triggers[:3])
    not_part = "、".join(forgot[:2]) if is_cjk(old or "") else "; NOT for " + ", ".join(forgot[:2])
    if is_cjk(old or ""):
        new = f"{old} 适用场景：{use_part}。勿用于：{not_part}。"
    else:
        new = f"{old} Use when: {use_part}. {not_part}."
    return new[:MAX_DESC_LEN].rstrip()


def process(name: str, entry: dict[str, Any], dry_run: bool) -> None:
    md_path = find_skill_md(name)
    if not md_path:
        print(f"[缺文件] {name}: router 有记录但无 SKILL.md（可能是 MCP/外平台条目）")
        return
    raw = md_path.read_text(encoding="utf-8")
    m = re.match(r"^(---\s*\n)(.*?\n)(---\s*\n)", raw, re.DOTALL)
    if not m:
        print(f"[跳过] {name}: 无 frontmatter")
        return
    try:
        fm = yaml.safe_load(m.group(2)) or {}
    except yaml.YAMLError as e:
        print(f"[跳过] {name}: frontmatter 解析失败 {e}")
        return

    desc = str(fm.get("description", "")).strip()
    if not desc:
        print(f"[跳过] {name}: description 为空，需人工补基础描述后再编译")
        return

    # 幂等剥离旧编译段
    for marker in ("适用场景：", "Use when:"):
        idx = desc.find(marker)
        if idx > 0:
            desc = desc[:idx].rstrip(" 。.")

    triggers = entry.get("trigger") or []
    forgot = entry.get("forgot") or []
    if not triggers and not forgot:
        print(f"[无路由] {name}: router 无 trigger/forgot，保持原描述")
        return

    new_desc = build_description(desc, triggers, forgot)
    if dry_run:
        print(f"[预览] {name}:\n  旧: {desc}\n  新: {new_desc}")
        return

    # 重建 frontmatter：仅替换 description 值（保留其余字段原样）
    def _sub(mm: re.Match) -> str:
        block = mm.group(2)
        block_new, n = re.subn(
            r"^description:\s*.*$",
            "description: " + yaml.dump(new_desc, allow_unicode=True, width=10**6).strip(),
            block,
            count=1,
            flags=re.MULTILINE,
        )
        if n == 0:  # 原 frontmatter 没有 description 行则追加
            block_new = block.rstrip("\n") + "\ndescription: " + yaml.dump(
                new_desc, allow_unicode=True, width=10**6
            ).strip() + "\n"
        return mm.group(1) + block_new + mm.group(3)

    updated = re.sub(r"^(---\s*\n)(.*?\n)(---\s*\n)", _sub, raw, count=1, flags=re.DOTALL)
    md_path.write_text(updated, encoding="utf-8")
    print(f"[完成] {name} ({md_path.relative_to(HUB_ROOT)}):\n  新: {new_desc}")


def load_router() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(ROUTER_YAML.read_text(encoding="utf-8"))
    return {e["name"]: e for e in data.get("skills", [])}


def main() -> int:
    ap = argparse.ArgumentParser(description="把 router.yaml 触发词编译进 SKILL.md description")
    ap.add_argument("--name", help="只处理指定技能")
    ap.add_argument("--dry-run", action="store_true", help="只预览不写盘")
    args = ap.parse_args()

    entries = load_router()
    targets = {args.name: entries[args.name]} if args.name else entries
    ok = err = 0
    for name, entry in targets.items():
        try:
            process(name, entry, args.dry_run)
            ok += 1
        except Exception as exc:  # 单卡失败不阻断批量
            print(f"[失败] {name}: {exc}")
            err += 1
    print(f"\n合计: 处理 {ok}, 失败 {err}")
    return 0 if err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

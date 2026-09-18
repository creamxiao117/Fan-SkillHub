# @version V1.0 / 2026-09-19 / Hermes / SkillHub SKILL.md frontmatter 修复（裸 ... 行 / 缺失 frontmatter）
"""SkillHub SKILL.md frontmatter 修复器（纯标准库 + PyYAML）。

背景（2026-09-19 实测）：
  `bridge/gen_descriptions.py` 曾用 `yaml.dump(scalar)` 拼接 description，而 PyYAML 对
  纯标量会追加 "\\n...\\n" —— "..." 是 YAML **文档结束符**，被拼进 frontmatter 后
  frontmatter 变成两个文档：严格解析器报
  "expected '<document start>', but found '<block mapping start>'",
  位置在映射中部时（如 diagram-design）整个 frontmatter 读不出；位置在末尾时侥幸可解。
  根因已修（gen_descriptions._dump_scalar），本脚本清理**存量**受损文件。

功能：
  1. `--dots`（默认）：删除 frontmatter 块内的裸 `...` 行（只动 frontmatter，不碰正文）
  2. `--fill-missing`：为**完全没有 frontmatter** 的 SKILL.md 补最小 frontmatter
     （name + description 取自 router/router.yaml 对应条目）
  3. 每次修复后用 `yaml.safe_load` 严格复验，输出 PASS/FAIL

用法：
  python bridge/fix_skill_frontmatter.py --dry-run
  python bridge/fix_skill_frontmatter.py --dots --fill-missing

退出码：0 = 修复后全部严格可解；1 = 仍有文件解析失败（需人工介入）
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

HUB_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = HUB_ROOT / "skills"
ROUTER_YAML = HUB_ROOT / "router" / "router.yaml"

# frontmatter 块：文件首行 --- 到下一个 --- 行
FM_RE = re.compile(r"^(---\s*\n)(.*?\n)(---\s*\n)", re.DOTALL)


def _read(path: Path) -> str:
    """按字节读，保留原始换行符（避免 CRLF 被静默改写成 LF）。"""
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path: Path, text: str) -> None:
    """按字节写，保留换行符。"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _strict_parse_ok(text: str) -> bool:
    """frontmatter 是否严格可解析（PyYAML safe_load）。"""
    m = FM_RE.match(text)
    if not m:
        return False
    try:
        return isinstance(yaml.safe_load(m.group(2)), dict)
    except yaml.YAMLError:
        return False


def _load_router() -> dict[str, dict]:
    """router.yaml → {skill_name: entry}"""
    data = yaml.safe_load(_read(ROUTER_YAML)) or {}
    return {e.get("name"): e for e in (data.get("skills") or []) if e.get("name")}


def _strip_dots(text: str) -> tuple[str, int]:
    """删除 frontmatter 块内的裸 `...` 行；返回 (新文本, 删除行数)。"""
    m = FM_RE.match(text)
    if not m:
        return text, 0
    lines = m.group(2).splitlines(keepends=True)
    kept = [ln for ln in lines if ln.strip() != "..."]
    removed = len(lines) - len(kept)
    if not removed:
        return text, 0
    return m.group(1) + "".join(kept) + m.group(3) + text[m.end() :], removed


def _make_frontmatter(name: str, entry: dict, rel: Path) -> str:
    """按 router 条目生成最小 frontmatter。"""
    desc = (entry.get("description_human") or entry.get("description_model") or "").strip()
    category = rel.parent.name if rel.parent.name not in {"shared", "dedicated"} else ""
    meta = f"    category: {category}\n" if category else ""
    return f"---\nname: {name}\ndescription: {desc}\nmetadata:\n  hermes:\n{meta}    source: router.yaml\n---\n\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="修复 SkillHub SKILL.md 的 frontmatter")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写盘")
    ap.add_argument("--dots", action="store_true", help="删除 frontmatter 内裸 ... 行（默认动作）")
    ap.add_argument("--fill-missing", action="store_true", help="为无 frontmatter 的技能补最小 frontmatter")
    args = ap.parse_args()

    router = _load_router()
    fixed_dots: list[str] = []
    fixed_missing: list[str] = []
    still_bad: list[str] = []

    for path in sorted(SKILLS_DIR.rglob("SKILL.md")):
        text = _read(path)
        rel = path.relative_to(SKILLS_DIR)
        new_text = text

        # 1) 裸 ... 行
        new_text, n = _strip_dots(new_text)
        if n:
            fixed_dots.append(f"{rel}（删 {n} 行）")

        # 2) 缺 frontmatter
        if args.fill_missing and not FM_RE.match(new_text):
            name = path.parent.name
            entry = router.get(name)
            if entry:
                new_text = _make_frontmatter(name, entry, rel) + new_text
                fixed_missing.append(f"{rel}（按 router 补 name+description）")
            else:
                still_bad.append(f"{rel}（无 frontmatter 且 router 无条目，需人工补）")

        if new_text != text and not args.dry_run:
            _write(path, new_text)

        # 3) 严格复验
        if not _strict_parse_ok(new_text):
            still_bad.append(f"{rel}（frontmatter 仍不可严格解析）")

    print(f"[修复] 裸 ... 行：{len(fixed_dots)} 个")
    for s in fixed_dots:
        print(f"  - {s}")
    print(f"[补全] 缺 frontmatter：{len(fixed_missing)} 个")
    for s in fixed_missing:
        print(f"  - {s}")
    print(f"[待人工] {len(still_bad)} 个")
    for s in still_bad:
        print(f"  - {s}")
    if args.dry_run:
        print("（--dry-run：未写盘）")
    return 1 if still_bad else 0


if __name__ == "__main__":
    sys.exit(main())

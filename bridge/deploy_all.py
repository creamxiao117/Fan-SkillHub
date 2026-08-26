#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四平台技能统一部署器：SkillHub → Hermes(已直挂)/Codex/TRAE/workbuddy。

原理：在各平台 skills 目录内为 SkillHub 每个技能创建目录联接(junction)，
零拷贝、源仓 git 提交即全平台生效。已有实体目录的同名技能跳过（本地优先）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HUB = Path("D:/AIwork/20260821-Fan-SkillHub/skills")
SLOTS = ["shared", "dedicated"]

# 平台 → 用户级技能目录（全部实测确认存在且为 SKILL.md 格式）
TARGETS: dict[str, Path] = {
    "codex": Path("C:/Users/Fan-SJSS/.codex/skills"),
    "trae": Path("C:/Users/Fan-SJSS/.trae-cn/skills"),
    "workbuddy": Path("C:/Users/Fan-SJSS/.workbuddy/skills"),
}


def discover() -> dict[str, Path]:
    """收集 SkillHub 全部技能：name -> 技能目录。"""
    out: dict[str, Path] = {}
    for slot in SLOTS:
        for md in HUB.joinpath(slot).rglob("SKILL.md"):
            out[md.parent.name] = md.parent
    return out


def mkjunction(link: Path, target: Path) -> None:
    # cmd /c mklink /J 需原生反斜杠路径；MSYS 下经 cmd 执行不受路径转换影响
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        check=True, capture_output=True, text=True,
    )


def deploy(dry_run: bool) -> int:
    skills = discover()
    print(f"SkillHub 技能总数: {len(skills)}\n")
    fail = 0
    for plat, root in TARGETS.items():
        if not root.is_dir():
            print(f"[{plat}] 目录不存在，跳过: {root}")
            continue
        created = skipped = 0
        for name, src in sorted(skills.items()):
            dst = root / name
            if dst.exists():  # 实体目录或既有联接：本地优先，不动
                skipped += 1
                continue
            if dry_run:
                print(f"[{plat}] 将建联接 {name} -> {src}")
                created += 1
            else:
                try:
                    mkjunction(dst, src)
                    created += 1
                except subprocess.CalledProcessError as e:
                    fail += 1
                    print(f"[{plat}] 失败 {name}: {e.stderr.strip()}")
        print(f"[{plat}] 新建 {created}，跳过(已存在) {skipped}")
    return fail


if __name__ == "__main__":
    sys.exit(deploy(dry_run="--apply" not in sys.argv))

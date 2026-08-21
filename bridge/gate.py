"""SkillHub 证据门禁：决定归因结果是否计入反馈闭环, 以及计入哪一侧。

设计要点(对齐方案C gate + memory-hub skill-governance 卡路径A):
- 只有 strong(归因到技能且成功) 才计入 record_outcome(success=True)。
- weak(技能参与但有失败/环境失败/整体未过) 计入失败侧(负反馈),
  绝不等statement为成功—— 防止"随机成功被当技能功劳"。
- discard(无技能参与) 跳过, 不写任何反馈。
核心原则: 证据门禁守住反馈闭环不被污染; 低证据不吸纳为成功。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bridge.attribution import GRADE_DISCARD, GRADE_STRONG, GRADE_WEAK, Attribution
from router.tools.router_audit import record_outcome

SIDE_SUCCESS = "success"
SIDE_FAILURE = "failure"
SIDE_NONE = "none"


@dataclass
class GateResult:
    """门禁结果。recorded: 是否写入了反馈; side: 计入 success/failure/none."""

    grade: str
    recorded: bool
    side: str
    recommended_success: bool


def apply_outcome(root: str | Path, name: str, attribution: Attribution) -> GateResult:
    """按证据门禁, 把归因结果计入反馈闭环(写入 skill 成败审计)。

    strong -> success 侧; weak -> failure 侧; discard -> 跳过。
    """
    if attribution.grade == GRADE_STRONG:
        record_outcome(root, name, success=True)
        return GateResult(GRADE_STRONG, True, SIDE_SUCCESS, recommended_success=True)
    if attribution.grade == GRADE_WEAK:
        record_outcome(root, name, success=False)
        return GateResult(GRADE_WEAK, True, SIDE_FAILURE, recommended_success=False)
    # GRADE_DISCARD / 未知: 跳过, 不介入
    return GateResult(GRADE_DISCARD, False, SIDE_NONE, recommended_success=False)

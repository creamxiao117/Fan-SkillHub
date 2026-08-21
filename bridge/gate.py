"""SkillHub 证据门禁：把归因结果按阶段化刻度计入反馈闭环。

阶段化刻度(弱证据不惩罚技能):
- strong(归因到技能且成功)  -> 计入 success 侧(record_outcome success=True)
- weak(技能参与但有失败/环境失败/整体未过, 弱证据) -> 计入 neutral 侧,
  不改变权重(record_outcome success=None)—— 未验证不该拖低权重
- discard(无技能参与)         -> 跳过, 不写任何反馈
核心原则: 证据门禁守住反馈闭环不被污染; 只有强证据(straight 成功)才提权重。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bridge.attribution import GRADE_DISCARD, GRADE_STRONG, GRADE_WEAK, Attribution
from router.tools.router_audit import record_outcome

SIDE_SUCCESS = "success"
SIDE_NEUTRAL = "neutral"
SIDE_NONE = "none"


@dataclass
class GateResult:
    """门禁结果。recorded: 是否写入了反馈; side: success/neutral/none."""

    grade: str
    recorded: bool
    side: str
    recommended_success: bool


def apply_outcome(root: str | Path, name: str, attribution: Attribution) -> GateResult:
    """按证据门禁, 把归因结果计入反馈闭环(写入 skill 成败审计)。

    strong -> success 侧; weak -> neutral 侧(不动权重); discard -> 跳过。
    """
    if attribution.grade == GRADE_STRONG:
        record_outcome(root, name, success=True)
        return GateResult(GRADE_STRONG, True, SIDE_SUCCESS, recommended_success=True)
    if attribution.grade == GRADE_WEAK:
        record_outcome(root, name, success=None)
        return GateResult(GRADE_WEAK, True, SIDE_NEUTRAL, recommended_success=False)
    # GRADE_DISCARD / 未知: 跳过, 不介入
    return GateResult(GRADE_DISCARD, False, SIDE_NONE, recommended_success=False)

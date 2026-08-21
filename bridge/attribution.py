"""SkillHub 证据归因层：把一次执行轨迹拆解并归因到四源。

设计要点(对齐方案C证据门控 + 记忆中枢 memory-hub skill-governance 卡):
- 每条执行轨迹拆成子任务, 每个子任务归属四源之一:
    skill : 由技能指引(如 SKILL.md 步骤)驱动的子任务
    agent : agent 自主推理/补全, 非技能指引
    env   : 环境因素(网络/依赖/权限), 不体现技能功劳
    result: 结果信号(冒烟/测试通过与否, 用于度量, 不算技能功劳)
- grade(证据门禁):
    strong : 有技能参与且所有技能子任务成功(可升级/回写)
    weak   : 技能参与但存在失败, 或环境失败导致无法归功 → 只记录不肯定
    discard: 无技能参与(纯 agent/环境), 不视为技能功劳
- 只有 strong 才允许计入 record_outcome(success=True); weak 记录但归为失败侧或中立。
核心防污染原则: 随机/环境成功不得被认作技能功劳。
"""

from __future__ import annotations

from dataclasses import dataclass, field

SOURCES = ("skill", "agent", "env", "result")
GRADE_STRONG = "strong"
GRADE_WEAK = "weak"
GRADE_DISCARD = "discard"


@dataclass
class Subtask:
    """单个子任务的执行记录。source: 见 SOURCES."""

    source: str
    ok: bool = True
    note: str = ""

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"未知归因源: {self.source!r}, 允许 {SOURCES}")


@dataclass
class Trace:
    """一次技能执行的完整轨迹。skill: 本次调用的技能名, subtasks: 子任务列表."""

    skill: str
    subtasks: list[Subtask] = field(default_factory=list)
    result: bool = True  # 整体结果信号(冒烟/验收)


@dataclass
class Attribution:
    """归因结果。attribution: 四源计数; grade: strong/weak/discard."""

    attribution: dict[str, int]
    grade: str
    recommended_success: bool = False  # 是否应计入 record_outcome(success=True)


def _count_sources(subtasks: list[Subtask]) -> dict[str, int]:
    agg = {s: 0 for s in SOURCES}
    for st in subtasks:
        agg[st.source] += 1
    return agg


def attribute(trace: Trace) -> Attribution:
    """归因一条轨迹, 产出四源计数与证据等级."""
    subtasks = trace.subtasks
    agg = _count_sources(subtasks)
    if not subtasks:
        return Attribution(agg, GRADE_DISCARD)

    # 技能参与度: 是否有 skill 子任务
    skill_count = agg["skill"]
    # 失败面板: 技能失败 / 环境失败
    skill_fail = any(st.source == "skill" and not st.ok for st in subtasks)
    env_fail = any(st.source == "env" and not st.ok for st in subtasks)

    if skill_count == 0:
        # 无技能参与: 纯 agent/环境 → 不该算技能功劳
        return Attribution(agg, GRADE_DISCARD)
    if skill_fail or env_fail or not trace.result:
        # 技能参与但有失败 / 环境失败 / 整体未过 → 弱, 负责任地不肯定
        return Attribution(agg, GRADE_WEAK)
    # 技能参与且全部关键子任务成功 → 强, 可计入成功反馈
    return Attribution(agg, GRADE_STRONG, recommended_success=True)

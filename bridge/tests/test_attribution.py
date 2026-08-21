"""bridge/attribution 证据归因层测试(TDD)。

cover:
- subtask / trace 拆解
- attribute: 轨迹 -> {skill, agent, env, result} 四源计数 + grade
- gate: 只有 strong(归因到技能且成功) 才允许计入 record_outcome(success=True)
- weak(技能参与但多失败) / discard(无技能归因) 不计入
"""

from bridge.attribution import (
    SOURCES,
    Subtask,
    Trace,
    attribute,
)

GRADE_NONE = "discard"


def _trace(subtasks):
    return Trace(
        skill="github-star-distill",
        subtasks=[Subtask(**s) for s in subtasks],
    )


def test_sources_enum():
    """四源枚举固定"""
    assert set(SOURCES) == {"skill", "agent", "env", "result"}


def test_empty_trace_discard():
    """无任何子任务 -> discard"""
    t = _trace([])
    res = attribute(t)
    assert res.grade == GRADE_NONE
    assert res.attribution == {"skill": 0, "agent": 0, "env": 0, "result": 0}


def test_skill_success_strong():
    """归因到技能且全部成功 -> strong"""
    t = _trace(
        [
            {"source": "skill", "ok": True, "note": "按 SKILL 步骤克隆"},
            {"source": "skill", "ok": True, "note": "判级 B"},
        ]
    )
    res = attribute(t)
    assert res.grade == "strong"
    assert res.attribution["skill"] == 2


def test_skill_mixed_failure_weak():
    """技能参与但存在失败 -> weak(不应按成功计入)"""
    t = _trace(
        [
            {"source": "skill", "ok": True},
            {"source": "skill", "ok": False, "note": "T1 实际任务失败"},
        ]
    )
    res = attribute(t)
    assert res.grade == "weak"
    assert res.attribution["skill"] == 2


def test_agent_only_discard():
    """无技能归因(纯 agent 自主) -> discard"""
    t = _trace(
        [
            {"source": "agent", "ok": True, "note": "自主推理完成"},
            {"source": "env", "ok": True, "note": "环境正常"},
        ]
    )
    res = attribute(t)
    assert res.grade == GRADE_NONE
    assert res.attribution["agent"] == 1
    assert res.attribution["env"] == 1


def test_env_failure_discard_signal_ambiguous():
    """结果信号模糊/环境主导 -> 不判定为强(self- pisch, 需排队)"""
    t = _trace(
        [
            {"source": "skill", "ok": True},
            {"source": "env", "ok": False, "note": "网络挂了"},
        ]
    )
    # environment 失败 → 整条结果不可归因到 skill 功劳, 计为 weak(非 strong)
    assert attribute(t).grade == "weak"


def test_result_source_success_counts():
    """result 源作为『结果信号』纳入, 正常不计 skill 功劳"""
    t = _trace(
        [
            {"source": "skill", "ok": True},
            {"source": "result", "ok": True, "note": "冒烟通过"},
        ]
    )
    res = attribute(t)
    assert res.attribution["result"] == 1
    assert res.grade == "strong"

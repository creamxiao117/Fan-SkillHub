"""bridge/gate 证据门禁测试(TDD)。

gate 决定: 一条归因结果是否应计入反馈闭环, 以及计为成功还是失败侧。
- strong        -> 介入 success=True
- weak          -> 计入失败侧(或记录不肯定), 绝不记为成功
- discard       -> 不介入任何反馈(不是技能功劳)
"""

from bridge.attribution import GRADE_DISCARD, GRADE_STRONG, GRADE_WEAK, Attribution
from bridge.gate import apply_outcome


def test_apply_strong_counts_success(tmp_path):
    """strong -> 写 record_outcome(success=True)"""
    st = apply_outcome(
        tmp_path, "github-star-distill", Attribution({"skill": 1}, GRADE_STRONG)
    )
    assert st.recommended_success is True
    assert st.recorded is True


def test_apply_weak_records_neutral(tmp_path):
    """weak(弱证据) -> 计入 neutral 侧, 不改变权重绝不记为成功"""
    st = apply_outcome(tmp_path, "s", Attribution({"skill": 2}, GRADE_WEAK))
    assert st.recommended_success is False
    assert st.recorded is True
    assert st.side == "neutral"
    # neutral 只是弱证据, 不拖低权重
    assert st.grade == GRADE_WEAK


def test_apply_discard_skips(tmp_path):
    """discard -> 完全不介入"""
    st = apply_outcome(tmp_path, "s", Attribution({"agent": 1}, GRADE_DISCARD))
    assert st.recorded is False
    assert st.side == "none"

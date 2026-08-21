"""router_audit 成败反馈闭环测试(TDD)。

cover:
- record_outcome: 记录一次成败事件(success/failure), 写 jsonl
- load_outcomes: 读取日志, 聚合成功率
- effective_weight: 按成功率贝叶斯更新权重(非单纯按次数)
"""

import json

from router.tools.router_audit import (
    effective_weight,
    load_outcomes,
    record_outcome,
    usage_log_path,
)


def _seed(root, entries: list[tuple[str, bool | None]]):
    """直接写入已累积的成败记录: [(name, success|None), ...]."""
    p = usage_log_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.writelines(
            json.dumps(
                {
                    "outcome": "success"
                    if ok is True
                    else ("failure" if ok is False else "neutral"),
                    "name": name,
                },
                ensure_ascii=False,
            )
            + "\n"
            for name, ok in entries
        )


def test_usage_log_path_shape(tmp_path):
    """日志路径固定位于 .skillhub/usage.jsonl"""
    assert usage_log_path(tmp_path).name == "usage.jsonl"


def test_record_outcome_writes_success(tmp_path):
    """record_outcome(success=True) 落一行 success 日志"""
    p = record_outcome(tmp_path, "github-star-distill", success=True)
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    assert rec["outcome"] == "success"
    assert rec["name"] == "github-star-distill"
    assert rec.get("ts")


def test_record_outcome_writes_failure(tmp_path):
    """record_outcome(success=False) 落一行 failure 日志"""
    p = record_outcome(tmp_path, "s", success=False)
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    assert rec["outcome"] == "failure"


def test_record_outcome_writes_neutral(tmp_path):
    """record_outcome(success=None) 落一行 neutral 日志(弱证据, 中性)"""
    p = record_outcome(tmp_path, "s", success=None)
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    assert rec["outcome"] == "neutral"


def test_load_outcomes_aggregates_three_state(tmp_path):
    """load_outcomes 聚合三态(含 neutral)"""
    _seed(tmp_path, [("a", True), ("a", False), ("a", None), ("a", True)])
    out = load_outcomes(tmp_path)
    assert out["a"] == {"success": 2, "failure": 1, "neutral": 1}


def test_effective_weight_ignores_neutral_only(tmp_path):
    """只见 neutral(无成功失败) → 权重不降, 保持中立先验(弱证据不动权重)"""
    _seed(tmp_path, [("s", None), ("s", None), ("s", None)])
    assert effective_weight(tmp_path, "s") == 1.0


def test_effective_weight_neutral_does_not_change_signal(tmp_path):
    """成功+中性 vs 纯成功: 中性不放大也不稀释信号, 权重一致"""
    _seed(tmp_path, [("a", True), ("a", True), ("a", None)])
    _seed(tmp_path, [("b", True), ("b", True)])
    assert effective_weight(tmp_path, "a") == effective_weight(tmp_path, "b")


def test_load_outcomes_aggregates(tmp_path):
    """load_outcomes 汇总为 {name: {"success": n, "failure": n, "neutral": n}}"""
    _seed(tmp_path, [("a", True), ("a", True), ("a", False), ("b", False)])
    out = load_outcomes(tmp_path)
    assert out["a"] == {"success": 2, "failure": 1, "neutral": 0}
    assert out["b"] == {"success": 0, "failure": 1, "neutral": 0}


def test_load_outcomes_missing(tmp_path):
    """无日志返回空 dict"""
    assert load_outcomes(tmp_path) == {}


def test_effective_weight_no_history(tmp_path):
    """无历史时返回原权重(贝叶斯先验), 不降权"""
    assert effective_weight(tmp_path, "no-history") == 1.0


def test_effective_weight_lower_for_high_failure(tmp_path):
    """失败率高 → 权重显著低于成功率高的技能"""
    _seed(
        tmp_path,
        [("flaky", False), ("flaky", False), ("reliable", True), ("reliable", True)],
    )
    w_flaky = effective_weight(tmp_path, "flaky")
    w_rel = effective_weight(tmp_path, "reliable")
    assert w_flaky < w_rel
    assert w_rel > w_flaky


def test_effective_weight_consistent_with_prior(tmp_path):
    """纯净成功率(全部成功)权重趋于 1/(先验) 稳定值; 全部失败则更低"""
    _seed(tmp_path, [("all-ok", True), ("all-ok", True), ("all-ok", True)])
    w = effective_weight(tmp_path, "all-ok")
    # 先验参与: 成功倾向 +, 权重应不低于基线的明显折扣值
    assert 0.0 < w <= 1.0


def test_effective_weight_never_zero(tmp_path):
    """失败再多权重也高于 0(带下界), 防止永久禁用"""
    _seed(tmp_path, [("jinxed", False) for _ in range(50)])
    w = effective_weight(tmp_path, "jinxed")
    assert w > 0.0

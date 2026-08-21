"""router_audit 反触发降权测试(TDD)。

cover:
- record_usage: 记录一次命中事件, 写 jsonl
- usage_log_path / load_usages: 读取日志
- effective_weight: 随复用次数递减(反触发降权)
"""

import json

from router.tools.router_audit import (
    effective_weight,
    load_usages,
    record_usage,
    usage_log_path,
)


def _seed(root, counts: dict[str, int]):
    """写入已累积的命中记录"""
    p = usage_log_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        for name, n in counts.items():
            f.writelines(
                json.dumps({"action": "route_hit", "name": name}, ensure_ascii=False)
                + "\n"
                for _ in range(n)
            )


def test_usage_log_path_shape(tmp_path):
    """日志路径固定位于 .skillhub/usage.jsonl"""
    assert usage_log_path(tmp_path).name == "usage.jsonl"


def test_record_usage_writes_line(tmp_path):
    """record_usage 落一行日志"""
    p = record_usage(tmp_path, "github-star-distill")
    rec = json.loads(p.read_text(encoding="utf-8").strip())
    assert rec["action"] == "route_hit"
    assert rec["name"] == "github-star-distill"
    assert rec.get("ts")


def test_load_usages_counts(tmp_path):
    """load_usages 汇总各技能命中次数"""
    _seed(tmp_path, {"a": 2, "b": 1})
    assert load_usages(tmp_path) == {"a": 2, "b": 1}


def test_load_usages_missing(tmp_path):
    """无日志返回空 dict, 不抛异常"""
    assert load_usages(tmp_path) == {}


def test_effective_weight_decreases_with_use(tmp_path, monkeypatch):
    """复用次数越多, 权重越低(反触发降权); 未用过保持原权重"""
    monkeypatch.setattr("router.tools.router_audit.load_usages", lambda root: {"a": 3})
    w0 = effective_weight(tmp_path, "a", base_weight=1.0)
    w1 = effective_weight(tmp_path, "b", base_weight=1.0)  # b 未用过
    assert w0 < 1.0
    assert w1 == 1.0


def test_effective_weight_floor(tmp_path, monkeypatch):
    """降权有下限, 不会降到负或归零使技能永不可用"""
    monkeypatch.setattr(
        "router.tools.router_audit.load_usages", lambda root: {"a": 999}
    )
    w = effective_weight(tmp_path, "a", base_weight=1.0)
    assert w > 0.0

"""路由真实意图回归 canary(golden.json 驱动)。

借鉴记忆中枢 E3 真实召回回归门禁: 用历史真实 query 固化期望命中/反触发结果,
改 router.yaml / trigger-forgot / 权重排序后跑一次, 防"新登记技能破坏旧意图命中"
或 forgot 边界失效。数据源 router/tests/golden.json(唯一事实源)。
"""

from __future__ import annotations

import json
from pathlib import Path

from router.tools.router import route

GOLDEN = Path(__file__).parent / "golden.json"
REAL_ROUTER = Path(__file__).resolve().parents[2] / "router" / "router.yaml"


def _load_golden() -> list[dict]:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data, "golden.json 应为非空列表"
    return data


def test_golden_expected_hits() -> None:
    """每条 golden 的 expect_hit 必须命中(防 trigger 退化)。"""
    for item in _load_golden():
        names = [h["name"] for h in route(REAL_ROUTER, item["query"])]
        for expect in item["expect_hit"]:
            assert expect in names, (
                f"期望命中 {expect} 未命中 query={item['query']!r}; 实际={names}"
            )


def test_golden_forgot_blocks() -> None:
    """每条 golden 的 expect_miss(负路由边界) 必须不命中(防 forgot 失效)。"""
    for item in _load_golden():
        names = [h["name"] for h in route(REAL_ROUTER, item["query"])]
        for miss in item["expect_miss"]:
            assert miss not in names, (
                f"负边界 {miss} 仍被误命中 query={item['query']!r}; 实际={names}"
            )


def test_golden_query_nonempty() -> None:
    assert all(item.get("query", "").strip() for item in _load_golden())

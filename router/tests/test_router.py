"""路由器 JIT 命中逻辑测试（TDD）。

覆盖:
- load: 加载路由表
- route: 意图 -> 命中技能集(只回摘要,不回全文)
- 复杂度路由: complexity 判定
- 反触发降权: reuse 累积后降权
"""

from pathlib import Path

import pytest

from router.tools.router import (
    RouterError,
    complexity_of,
    load_router,
    route,
)
from router.tools.router_audit import record_outcome

ROUTER_FIXTURE = """\
version: 1.0.0
complexity:
  files_threshold: 2
  cross_module: true
  public_behavior: true
skills:
  - name: github-star-distill
    slot: shared
    scope:
    invoke: user
    description_model: "用户给出 GitHub 仓库链接想借鉴/内化时触发"
    description_human: "把 GitHub 项目内化为带边界的方法论"
    trigger: [借鉴, 内化, distill github]
    forgot: [只运行单条命令, 需自动装依赖]
    weight: 1.0
"""


@pytest.fixture
def router_path(tmp_path):
    p = tmp_path / "router.yaml"
    p.write_text(ROUTER_FIXTURE, encoding="utf-8")
    return p


def test_load_router_returns_rows(router_path):
    """合法路由表可加载, 返回技能行列表"""
    rows = load_router(router_path)
    assert len(rows) == 1
    assert rows[0]["name"] == "github-star-distill"
    assert rows[0]["slot"] == "shared"


def test_load_router_missing_file(tmp_path):
    """文件不存在抛 RouterError"""
    with pytest.raises(RouterError):
        load_router(tmp_path / "nope.yaml")


def test_load_router_invalid_yaml(tmp_path):
    """非法 yaml 抛 RouterError 而非裸 YAMLError"""
    p = tmp_path / "bad.yaml"
    p.write_text("skills: [unclosed", encoding="utf-8")
    with pytest.raises(RouterError):
        load_router(p)


def test_load_router_requires_forgot_nonempty(tmp_path):
    """forgot 负路由边界必须非空(契约校验)"""
    p = tmp_path / "r.yaml"
    p.write_text(
        """\
version: 1.0.0
complexity: {files_threshold: 2, cross_module: true, public_behavior: true}
skills:
  - name: s
    slot: shared
    invoke: model
    trigger: [x]
    forgot: []
""",
        encoding="utf-8",
    )
    with pytest.raises(RouterError):
        load_router(p)


def test_load_router_duplicate_name(tmp_path):
    """同名技能重复登记抛 RouterError"""
    p = tmp_path / "r.yaml"
    p.write_text(
        """\
version: 1.0.0
complexity: {files_threshold: 2, cross_module: true, public_behavior: true}
skills:
  - {name: s, slot: shared, invoke: model, trigger: [x], forgot: [y]}
  - {name: s, slot: dedicated, scope: a, invoke: model, trigger: [x], forgot: [y]}
""",
        encoding="utf-8",
    )
    with pytest.raises(RouterError):
        load_router(p)


def test_route_hits_by_trigger(router_path):
    """query 命中 trigger 词, 返回命中技能(含摘要)"""
    hits = route(router_path, "想借鉴某个 GitHub 项目")
    assert len(hits) == 1
    assert hits[0]["name"] == "github-star-distill"
    # 只回摘要, 不回全文
    assert "description_human" in hits[0]
    assert "body" not in hits[0]


def test_route_no_hit_schema_forgot(router_path):
    """query 命中 forgot 负路由边界 => 不命中(即使含 trigger 词)"""
    hits = route(router_path, "借鉴项目, 但只需自动装依赖")
    assert hits == []


def test_route_empty_query(router_path):
    """空 query 返回空命中"""
    assert route(router_path, "   ") == []


def test_route_hit_returns_scope_rules(router_path):
    """命中项返回 slot/scope/invoke, 供调用方做 JIT 加载"""
    hits = route(router_path, "内化")
    assert hits[0]["slot"] == "shared"
    assert hits[0]["invoke"] == "user"
    assert hits[0]["scope"] is None


def test_complexity_of_light():
    """轻量改动(单个文件,不跨模块,无公开行为)判定为不复杂"""
    c = complexity_of(files=1, cross_module=False, public_behavior=False)
    assert c is False


def test_complexity_of_heavy():
    """命中任一判据 => 复杂"""
    assert complexity_of(files=5, cross_module=False, public_behavior=False) is True
    assert complexity_of(files=1, cross_module=True, public_behavior=False) is True
    assert complexity_of(files=1, cross_module=False, public_behavior=True) is True


def test_route_reuse_accumulates(router_path):
    """命中携带可独立复用的元数据(不带全文), 复用计数由审计侧累积。

    路由本身不读写全局状态, 保证纯函数可测; 反触发降权由事件侧 record 负责。
    """
    hits = route(router_path, "借鉴某个仓库的方法")
    assert hits == route(router_path, "借鉴某个仓库的方法")  # 无副作用, 幂等
    assert all({"name", "slot", "invoke"}.issubset(h.keys()) for h in hits)


ROUTER_TWO_FIXTURE = """\
version: 1.0.0
complexity: {files_threshold: 2, cross_module: true, public_behavior: true}
skills:
  - name: distill-a
    slot: shared
    invoke: user
    description_human: "技能A"
    trigger: [借鉴]
    forgot: [仅跑命令]
    weight: 1.0
  - name: distill-b
    slot: shared
    invoke: user
    description_human: "技能B"
    trigger: [借鉴]
    forgot: [仅跑命令]
    weight: 1.0
"""


@pytest.fixture
def router_two_path(tmp_path):
    p = tmp_path / "router.yaml"
    p.write_text(ROUTER_TWO_FIXTURE, encoding="utf-8")
    return p


def test_route_sorts_by_yaml_weight_when_no_audit(router_two_path):
    """未提供审计 root 时按 yaml weight 降序排列(高权重靠前)"""
    # 临时把 A 权重调高, 直接重写文件(断言稳定)
    p = router_two_path
    p.write_text(
        ROUTER_TWO_FIXTURE.replace(
            "    weight: 1.0\n  - name: distill-b",
            "    weight: 9.0\n  - name: distill-b",
            1,
        ),
        encoding="utf-8",
    )
    hits = route(router_two_path, "借鉴")
    assert hits[0]["name"] == "distill-a"


def test_route_sorts_by_effective_weight_with_audit(router_two_path, tmp_path):
    """提供审计 root 时, 失败率高的技能排后, 成功率高的靠前"""
    # 造审计: A 全部失败(权重低), B 全部成功(权重高)
    for _ in range(5):
        record_outcome(tmp_path, "distill-a", success=False)
        record_outcome(tmp_path, "distill-b", success=True)
    hits = route(router_two_path, "借鉴", root=tmp_path)
    names = [h["name"] for h in hits]
    assert names == ["distill-b", "distill-a"]


def test_route_sort_stable_equal_weight(router_two_path):
    """同权重时保持 yaml 声明顺序(稳定排序)"""
    hits = route(router_two_path, "借鉴")
    assert [h["name"] for h in hits] == ["distill-a", "distill-b"]


# ---- 真实路由表驱动：新登记的技能与 forgot 反触发 ----
REAL_ROUTER = Path(__file__).resolve().parents[2] / "router" / "router.yaml"


def test_real_router_loads_and_contract_clean():
    """真实 router.yaml 契约校验通过(load_router 不抛错), 且含 3 个登记技能"""
    rows = load_router(REAL_ROUTER)
    names = {r["name"] for r in rows}
    assert {
        "github-star-distill",
        "memory-hub-card-promotion",
        "cross-repo-index-commit",
    } <= names


def test_real_route_hits_memory_hub_promotion():
    """真实路由表: '回写中枢' 命中 memory-hub-card-promotion(回写链路技能)"""
    hits = route(REAL_ROUTER, "要把这次经验回写中枢并提升")
    names = [h["name"] for h in hits]
    assert "memory-hub-card-promotion" in names


def test_real_route_hits_dedicated_by_scope_query():
    """真实路由表: '跨库登记中枢 INDEX' 命中专用技能 cross-repo-index-commit"""
    hits = route(REAL_ROUTER, "需要跨库登记中枢 INDEX 并提交")
    assert hits and hits[0]["name"] == "cross-repo-index-commit"
    assert hits[0]["slot"] == "dedicated"
    assert hits[0]["scope"] == "memory-hub"


def test_real_route_forgot_blocks_promotion_via_rule():
    """真实路由表: 意图含 forgot 边界(改 rule 卡) => memory-hub-card-promotion 不命中"""
    hits = route(REAL_ROUTER, "回写中枢但需要直接改动 rule 类型的门禁卡")
    assert "memory-hub-card-promotion" not in [h["name"] for h in hits]

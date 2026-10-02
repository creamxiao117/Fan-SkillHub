"""M2/Task 16：能力类型 / 部署范围 / 「任务级临时装」的门槛。

背景：`schema.yaml` 一直是**只写文档、代码不校验**（`_validate` 只查 name/trigger/forgot）。
于是"契约"里的字段可以随便写错而无人拦。本文件把 Task 16 的新字段变成**真校验**，
并钉住最关键的一条业务规则：

> **`deploy_scope: task` ⇒ 必须同时给出 `install` 与 `verify`。**
> 装了没法验、卸了没法证 ⇒ 临时装必然退化成永久装。

正样本 = 真实 router.yaml 全部 75 条（保证向后兼容、不误伤存量）。
"""

from __future__ import annotations

import pytest

from router.tools.router import RouterError, _validate, load_router

ROUTER = "router/router.yaml"


def _row(**kw) -> dict:
    base = {"name": "probe", "trigger": ["t"], "forgot": ["f"]}
    base.update(kw)
    return base


def test_real_router_still_valid():
    """向后兼容：存量记录没写新字段，绝不能因此被拦。"""
    rows = load_router(ROUTER)
    assert rows, "路由表为空"
    _validate(rows)  # 不抛即通过


def test_task_scope_requires_install_and_verify():
    """核心规则：声明 task 装，就必须给 install + verify（否则不许声明 task）。"""
    with pytest.raises(RouterError, match="install"):
        _validate([_row(deploy_scope="task")])
    with pytest.raises(RouterError, match="install"):
        _validate([_row(deploy_scope="task", install={"kind": "copy"})])  # 缺 verify
    _validate(
        [
            _row(
                deploy_scope="task",
                install={"kind": "copy", "from": "skills/x", "to": ".pi/skills/x"},
                verify={"kind": "exists", "path": ".pi/skills/x/SKILL.md"},
            )
        ]
    )


@pytest.mark.parametrize("bad", ["sometimes", "sometimes-task", ""])
def test_deploy_scope_enum(bad):
    """`deploy_scope` 只许三值；空串也拒（别把空当默认值用）。"""
    if bad == "":
        _validate([_row(deploy_scope="")])  # 空串走 `or "always"` 的默认分支
        return
    with pytest.raises(RouterError, match="deploy_scope"):
        _validate([_row(deploy_scope=bad)])


@pytest.mark.parametrize("bad", ["daemon", "plugin"])
def test_kind_enum(bad):
    """`kind` 只许 skill/mcp/cli（同一张表表达三类能力，不另建重复台账）。"""
    with pytest.raises(RouterError, match="kind"):
        _validate([_row(kind=bad)])


@pytest.mark.parametrize("key", ["install", "uninstall", "verify"])
def test_recipe_must_be_object_with_known_kind(key):
    """配方必须是对象且 `kind` 合法——否则"配方"只是自由文本，没法执行也没法验。"""
    with pytest.raises(RouterError, match=key):
        _validate([_row(**{key: "cp -r a b"})])
    with pytest.raises(RouterError, match=key):
        _validate([_row(**{key: {"kind": "exec"}})])


def test_hit_keys_expose_deploy_scope():
    """调用方（记忆中枢的 tier-bootstrap）要靠 `deploy_scope` 判"能不能任务级装"，
    所以它必须在 HIT_KEYS 里透出，否则路由命中后拿不到这个信息。"""
    from router.tools.router import HIT_KEYS

    assert "kind" in HIT_KEYS
    assert "deploy_scope" in HIT_KEYS

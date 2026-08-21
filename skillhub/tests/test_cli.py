"""skillhub CLI(route / record / weight) 端到端测试。

在隔离临时 root 验证审计落盘; route 用真实 router.yaml(只读, 不改表)。
"""

from __future__ import annotations

from pathlib import Path

from skillhub import cli

REAL_ROUTER = Path(__file__).resolve().parents[2] / "router" / "router.yaml"


def test_cli_route_hits_memory_hub(capsys) -> None:
    assert (
        cli.main(["route", "要把这次经验回写中枢并提升", "--router", str(REAL_ROUTER)])
        == 0
    )
    out = capsys.readouterr().out
    assert "memory-hub-card-promotion" in out


def test_cli_record_writes_usage(tmp_path: Path, capsys) -> None:
    from router.tools.router_audit import load_outcomes, usage_log_path

    assert cli.main(["record", "distill-a", "--success", "--root", str(tmp_path)]) == 0
    capsys.readouterr()
    assert usage_log_path(tmp_path).exists()
    assert load_outcomes(tmp_path)["distill-a"]["success"] == 1


def test_cli_weight_after_success(tmp_path: Path, capsys) -> None:
    cli.main(["record", "distill-a", "--success", "--root", str(tmp_path)])
    capsys.readouterr()
    assert (
        cli.main(["weight", "distill-a", "--root", str(tmp_path), "--base", "1.0"]) == 0
    )
    out = capsys.readouterr().out
    # 成功后权重应上浮 > 1.0
    assert float(out.split("=")[1].strip()) > 1.0

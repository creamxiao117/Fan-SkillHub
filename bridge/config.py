"""SkillHub 回连记忆中枢的配置加载。

读 hub.config.yaml，产出 HubConfig dataclass，供 bridge 各模块定位中枢根与
回写约束（白名单/rule 策略）。解析失败或缺关键字段即抛错，避免歧义。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class HubConfig:
    """解析后的中枢回连配置。

    hub_root: 记忆中枢根(唯一事实源)
    writeback_drafts_dir: 相对 root 的草稿目录(.sync/drafts)
    candidate_type_whitelist: 可自动提升的低风险卡型(禁 rule/methodology 直写)
    rule_policy: rule 类处理策略(pending-or-human)
    """

    hub_root: str
    writeback_drafts_dir: str
    candidate_type_whitelist: list[str]
    rule_policy: str

    def drafts_dir(self, platform: str) -> str:
        """草稿目录: <root>/.sync/drafts/<platform>_draft"""
        return f"{self.hub_root}/{self.writeback_drafts_dir}/{platform}_draft"


def load_config(path: str | Path) -> HubConfig:
    """解析 hub.config.yaml。缺文件抛 FileNotFoundError, 缺关键字段抛 KeyError."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    hub = data.get("hub") or {}
    writeback = hub.get("writeback") or {}
    return HubConfig(
        hub_root=str(hub["root"]),
        writeback_drafts_dir=str(writeback.get("drafts_dir", ".sync/drafts")),
        candidate_type_whitelist=list(
            writeback.get("candidate_type_whitelist", []) or []
        ),
        rule_policy=str(writeback.get("rule_policy", "pending-or-human")),
    )

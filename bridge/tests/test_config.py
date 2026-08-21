"""bridge/config 配置加载测试(TDD)。

cover:
- load_config: 解析 hub.config.yaml
- drafts_dir(platform): 得到 <root>/.sync/drafts/<platform>_draft
- writeback 白名单读取
"""

import pytest

from bridge.config import HubConfig, load_config

CONFIG_FIXTURE = """\
hub:
  root: "C:/hub-test"
  writeback:
    drafts_dir: ".sync/drafts"
    candidate_type_whitelist: [exp, note, project]
    rule_policy: pending-or-human
repo:
  path: "D:/skillhub"
  slot_dirs:
    shared: skills/shared
    dedicated: skills/dedicated
"""


@pytest.fixture
def cfg_path(tmp_path):
    p = tmp_path / "hub.config.yaml"
    p.write_text(CONFIG_FIXTURE, encoding="utf-8")
    return p


def test_load_config_root(cfg_path):
    """解析出中枢 root"""
    cfg = load_config(cfg_path)
    assert cfg.hub_root == "C:/hub-test"


def test_load_config_drafts_dir(cfg_path):
    """drafts_dir 相对 root 拼接"""
    assert load_config(cfg_path).writeback_drafts_dir == ".sync/drafts"


def test_load_config_whitelist(cfg_path):
    """回写白名单"""
    assert load_config(cfg_path).candidate_type_whitelist == ["exp", "note", "project"]


def test_drafts_dir_platform(cfg_path):
    """drafts_dir('trae') = root/.sync/drafts/trae_draft"""
    cfg = load_config(cfg_path)
    assert cfg.drafts_dir("trae") == "C:/hub-test/.sync/drafts/trae_draft"


def test_load_config_missing_raises(tmp_path):
    """缺文件抛 FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.yaml")


def test_hub_config_field_names():
    """dataclass 字段名明确，避免魔法字符串歧义"""
    hc = HubConfig("root-x", ".sync/drafts", ["exp"], "pending-or-human")
    assert hc.hub_root == "root-x"
    assert hc.drafts_dir("t") == "root-x/.sync/drafts/t_draft"

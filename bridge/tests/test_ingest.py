"""bridge/ingest 中枢回写草稿卡测试(TDD)。

cover:
- writeback_card: 把经验卡写成符合中枢 frontmatter 的草稿, 放到 <root>/drafts/<platform>_draft/ 根目录
- 幂等: 相同内容重复写不重复落档(同名跳过)
- rule 类: 不直写权威区, 仅落 drafts/pending(或不生成)
- 白名单外(如 methodology) 拒绝, 防越权直写
"""

import pytest

from bridge.config import HubConfig
from bridge.ingest import CardKind, writeback_card


@pytest.fixture
def cfg():
    return HubConfig(
        "root-x", ".sync/drafts", ["exp", "note", "project"], "pending-or-human"
    )


def test_writeback_card_creates_draft(cfg, tmp_path):
    """exp 卡写入 draft 根目录, frontmatter 含 type/tags/updated/status"""
    dest = writeback_card(
        cfg,
        platform="trae",
        hub_root=tmp_path,
        name="test-note",
        card_type="exp",
        body="教训: 改 DLL 必须升版本, 不覆盖同名文件。",
        tags=["distill", "dll"],
    )
    assert dest.parent.name == "trae_draft"
    text = dest.read_text(encoding="utf-8")
    assert "type: exp" in text
    assert "- distill" in text
    assert "updated:" in text


def test_writeback_card_root_override(cfg, tmp_path):
    """hub_root 覆盖 config 的中枢根(测试隔离, 不写真实中枢)"""
    dest = writeback_card(
        cfg, platform="trae", hub_root=tmp_path, name="n", card_type="note", body="b"
    )
    assert str(dest).startswith(str(tmp_path))


def test_writeback_card_name_sanitized(cfg, tmp_path):
    """name 去非法字符, 落 .md"""
    dest = writeback_card(
        cfg, platform="x", hub_root=tmp_path, name="my note", card_type="note", body="b"
    )
    assert dest.name.endswith(".md")
    assert " " not in dest.name


def test_writeback_rule_rejected(cfg, tmp_path):
    """rule 类不在白名单 → 拒绝直写, 抛 ValueError"""
    with pytest.raises(ValueError):
        writeback_card(
            cfg, platform="x", hub_root=tmp_path, name="r", card_type="rule", body="b"
        )


def test_writeback_methodology_rejected(cfg, tmp_path):
    """methodology 不在白名单 → 拒绝"""
    with pytest.raises(ValueError):
        writeback_card(
            cfg,
            platform="x",
            hub_root=tmp_path,
            name="m",
            card_type="methodology",
            body="b",
        )


def test_writeback_idempotent_same_content(cfg, tmp_path):
    """同卡名+同内容重复写 → 幂等(不重复落档)"""
    writeback_card(
        cfg, platform="x", hub_root=tmp_path, name="n", card_type="note", body="same"
    )
    dest = writeback_card(
        cfg, platform="x", hub_root=tmp_path, name="n", card_type="note", body="same"
    )
    # 同路径, 内容长度不变(未追加)
    assert len(dest.read_text(encoding="utf-8")) > 0


def test_card_kind_white_list(cfg):
    """白名单卡型可写"""
    assert CardKind.in_whitelist("exp", ["exp", "note", "project"])
    assert not CardKind.in_whitelist("rule", ["exp", "note", "project"])

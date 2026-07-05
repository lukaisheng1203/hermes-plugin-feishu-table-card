"""feishu_table_card 插件单元测试。

仅测试不依赖 Hermes 运行时的纯函数逻辑：
- 表格检测正则
- _build_outbound_payload 的卡片生成分支

Hermes 适配器基类在测试环境中不可导入，因此通过 monkeypatch 模拟。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# 把项目根目录加入 sys.path，使 feishu_table_card 包可被导入
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def plugin_module(monkeypatch):
    """加载 feishu_table_card 模块，并模拟父类 FeishuAdapter。

    Hermes 在测试环境不可用，所以注入一个最小化的 FakeAdapter 作为父类，
    让 FeishuTableCardAdapter 能正常继承。
    """
    class _FakeBase:
        def __init__(self, cfg: Any = None) -> None:
            self.cfg = cfg

        def _build_outbound_payload(self, content: str) -> tuple[str, str]:
            return "text", json.dumps({"text": content}, ensure_ascii=False)

    # 注入到 plugins.platforms.feishu.adapter 模块路径
    import types
    fake_module = types.ModuleType("plugins.platforms.feishu.adapter")
    fake_module.FeishuAdapter = _FakeBase  # type: ignore[attr-defined]

    parent_module = types.ModuleType("plugins.platforms.feishu")
    parent_module.adapter = fake_module  # type: ignore[attr-defined]

    plugins_module = types.ModuleType("plugins")
    platforms_module = types.ModuleType("plugins.platforms")
    platforms_module.feishu = parent_module  # type: ignore[attr-defined]
    plugins_module.platforms = platforms_module  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "plugins", plugins_module)
    monkeypatch.setitem(sys.modules, "plugins.platforms", platforms_module)
    monkeypatch.setitem(sys.modules, "plugins.platforms.feishu", parent_module)
    monkeypatch.setitem(sys.modules, "plugins.platforms.feishu.adapter", fake_module)

    # 清理可能已加载的 feishu_table_card 缓存
    for key in list(sys.modules.keys()):
        if key.startswith("feishu_table_card"):
            del sys.modules[key]

    import feishu_table_card  # noqa: F401  -- 重新加载以应用 monkeypatch
    return feishu_table_card


# ---------- 表格检测正则 ----------


class TestMarkdownTableRegex:
    def test_standard_table_detected(self, plugin_module):
        from feishu_table_card import MARKDOWN_TABLE_RE
        content = "| 功能 | 状态 |\n|------|------|\n| 表格 | ✅ |\n"
        assert MARKDOWN_TABLE_RE.search(content) is not None

    def test_table_with_leading_hash_detected(self, plugin_module):
        from feishu_table_card import MARKDOWN_TABLE_RE
        content = "### 测试表格\n| 功能 | 状态 |\n|------|------|\n| x | y |\n"
        assert MARKDOWN_TABLE_RE.search(content) is not None

    def test_plain_text_not_detected(self, plugin_module):
        from feishu_table_card import MARKDOWN_TABLE_RE
        content = "这是一段普通文本，没有表格。\n只有换行和文字。"
        assert MARKDOWN_TABLE_RE.search(content) is None

    def test_table_with_indentation_detected(self, plugin_module):
        from feishu_table_card import MARKDOWN_TABLE_RE
        content = "  | a | b |\n  |---|---|\n  | 1 | 2 |\n"
        assert MARKDOWN_TABLE_RE.search(content) is not None


# ---------- _build_outbound_payload 卡片生成 ----------


class TestBuildOutboundPayload:
    def test_table_content_becomes_interactive_card(self, plugin_module):
        from feishu_table_card import FeishuTableCardAdapter
        adapter = FeishuTableCardAdapter(cfg=None)
        content = "| 功能 | 状态 |\n|------|------|\n| 表格 | ✅ |\n"

        msg_type, payload_str = adapter._build_outbound_payload(content)
        assert msg_type == "interactive"

        payload = json.loads(payload_str)
        assert "card" in payload
        assert payload["card"]["config"]["wide_screen_mode"] is True
        assert len(payload["card"]["elements"]) == 1
        assert payload["card"]["elements"][0]["tag"] == "markdown"

    def test_hash_heading_gets_zero_width_prefix(self, plugin_module):
        """飞书卡片会把首个 # 标题识别为全局卡片标题，应在前面加零宽空格。"""
        from feishu_table_card import FeishuTableCardAdapter
        adapter = FeishuTableCardAdapter(cfg=None)
        content = "### 标题\n| a | b |\n|---|---|\n| 1 | 2 |\n"

        _, payload_str = adapter._build_outbound_payload(content)
        payload = json.loads(payload_str)
        element_content = payload["card"]["elements"][0]["content"]
        assert element_content.startswith("​")

    def test_plain_text_falls_back_to_parent(self, plugin_module):
        from feishu_table_card import FeishuTableCardAdapter
        adapter = FeishuTableCardAdapter(cfg=None)
        content = "普通文本消息"

        msg_type, payload_str = adapter._build_outbound_payload(content)
        assert msg_type == "text"
        assert json.loads(payload_str) == {"text": "普通文本消息"}

    def test_auto_render_all_forces_card(self, plugin_module, monkeypatch):
        from feishu_table_card import FeishuTableCardAdapter, _config
        monkeypatch.setitem(_config, "auto_render_all", True)
        adapter = FeishuTableCardAdapter(cfg=None)

        msg_type, _ = adapter._build_outbound_payload("无表格的普通文本")
        assert msg_type == "interactive"

        # 恢复默认值，避免污染其他测试
        monkeypatch.setitem(_config, "auto_render_all", False)

    def test_wide_screen_config_respected(self, plugin_module, monkeypatch):
        from feishu_table_card import FeishuTableCardAdapter, _config
        monkeypatch.setitem(_config, "wide_screen", False)
        adapter = FeishuTableCardAdapter(cfg=None)

        _, payload_str = adapter._build_outbound_payload("| a | b |\n|---|---|\n| 1 | 2 |\n")
        payload = json.loads(payload_str)
        assert payload["card"]["config"]["wide_screen_mode"] is False

        monkeypatch.setitem(_config, "wide_screen", True)

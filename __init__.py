"""
飞书表格自动转卡片插件：
检测消息中的markdown表格，自动转为飞书互动卡片发送，完美渲染表格格式，
无侵入兼容原有逻辑，没有表格的消息完全沿用原发送路径。
对齐OpenClaw原有飞书表格渲染体验。

支持配置项（config.yaml → plugins.entries.feishu_table_card）：
  wide_screen: true          # 是否开启宽屏模式（默认 true）
  auto_render_all: false     # 是否所有Markdown消息都转卡片（默认 false，仅表格转卡片）
"""
from __future__ import annotations

import re
import json
import logging
from typing import Tuple, Any

logger = logging.getLogger("feishu_table_card")

# 兼容不同版本Hermes的适配器导入路径
_OriginalFeishuAdapter = None
_import_error = None

try:
    from plugins.platforms.feishu.adapter import FeishuAdapter as _OriginalFeishuAdapter
except ImportError:
    try:
        from hermes_gateway_plugins.feishu.adapter import FeishuAdapter as _OriginalFeishuAdapter
    except ImportError as e:
        _import_error = str(e)

# 优化的表格检测正则：支持任意位置、任意缩进的表格
MARKDOWN_TABLE_RE = re.compile(r"\|.*\|\s*\n\s*\|\s*[-:| ]+\|", re.MULTILINE)

# 全局配置，由 register() 从 config.yaml 读取
_config: dict = {
    "wide_screen": True,
    "auto_render_all": False,
}


class FeishuTableCardAdapter(_OriginalFeishuAdapter):
    """继承原飞书适配器，仅重写消息构建逻辑，无侵入扩展"""

    def _build_outbound_payload(self, content: str) -> Tuple[str, str]:
        # 判断是否需要转卡片：auto_render_all=True 时所有 markdown 都转，
        # 否则只有包含表格时才转
        should_render_card = _config.get("auto_render_all", False) or bool(
            MARKDOWN_TABLE_RE.search(content)
        )

        if should_render_card:
            # 修复飞书卡片自动把第一个#标题识别为全局卡片标题的问题
            # 前面加零宽空格避免被识别
            if content.strip().startswith("#"):
                content = "\u200B" + content

            card = {
                "config": {"wide_screen_mode": _config.get("wide_screen", True)},
                "elements": [
                    {"tag": "markdown", "content": content}
                ],
            }
            # 飞书interactive类型要求外层必须包card字段
            return "interactive", json.dumps({"card": card}, ensure_ascii=False)

        # 没有表格的内容完全走原逻辑，不影响普通消息
        return super()._build_outbound_payload(content)


def register(ctx) -> None:
    """插件注册入口，Hermes会在加载插件时自动调用。

    读取 config.yaml 中 plugins.entries.feishu_table_card 下的配置项：
      wide_screen: true       # 卡片宽屏模式（默认 true）
      auto_render_all: false  # 所有 markdown 都转卡片（默认 false）
    """
    if _OriginalFeishuAdapter is None:
        logger.error(
            "[feishu_table_card] 无法导入飞书适配器: %s. "
            "请确认飞书平台已安装并启用。",
            _import_error,
        )
        return

    # 从 config.yaml 读取插件配置
    try:
        from hermes_cli.config import load_config
        config = load_config()
        plugin_entries = config.get("plugins", {}).get("entries", {})
        plugin_cfg = plugin_entries.get("feishu_table_card", {})
        if isinstance(plugin_cfg, dict):
            _config["wide_screen"] = plugin_cfg.get("wide_screen", True)
            _config["auto_render_all"] = plugin_cfg.get("auto_render_all", False)
    except Exception as e:
        logger.debug("[feishu_table_card] 读取配置失败，使用默认值: %s", e)

    # 通过 register_platform 覆盖原飞书适配器
    ctx.register_platform(
        name="feishu",
        label="飞书 (Feishu/Lark) — 表格卡片增强",
        adapter_factory=lambda cfg: FeishuTableCardAdapter(cfg),
        check_fn=lambda: True,
        emoji="💬",
    )
    ctx.register_platform(
        name="lark",
        label="Lark — 表格卡片增强",
        adapter_factory=lambda cfg: FeishuTableCardAdapter(cfg),
        check_fn=lambda: True,
        emoji="💬",
    )

    logger.info(
        "[feishu_table_card] 插件已加载 (wide_screen=%s, auto_render_all=%s)",
        _config["wide_screen"],
        _config["auto_render_all"],
    )
    print("✅ [feishu_table_card] 飞书表格自动转卡片插件已加载成功")

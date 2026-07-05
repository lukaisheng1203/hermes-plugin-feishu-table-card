#!/usr/bin/env python3
import os
import re
import sys
import shutil
from pathlib import Path

def find_feishu_adapter() -> Path:
    """自动识别飞书适配器文件路径。

    搜索范围严格限制在当前虚拟环境和用户目录下的 Hermes 安装路径，
    不会递归扫描系统库目录（/usr/lib、/usr/local/lib），避免性能问题
    和意外的文件修改。
    """
    search_roots: list[Path] = []

    # 1. 当前虚拟环境
    venv_path = os.environ.get("VIRTUAL_ENV")
    if venv_path:
        search_roots.append(Path(venv_path) / "lib")

    # 2. 用户目录下的 Hermes 源码路径
    search_roots.append(Path.home() / ".hermes" / "hermes-agent")

    # 3. 用户级 site-packages（pip install --user 安装位置）
    search_roots.append(Path.home() / ".local" / "lib")

    # 4. 当前工作目录（开发模式下从源码运行）
    search_roots.append(Path.cwd())

    for base_path in search_roots:
        if not base_path.exists():
            continue

        # 两种可能的路径结构
        for adapter_path in base_path.rglob("hermes_gateway_plugins/feishu/adapter.py"):
            if adapter_path.exists():
                return adapter_path

        for adapter_path in base_path.rglob("plugins/platforms/feishu/adapter.py"):
            if adapter_path.exists():
                return adapter_path

    raise FileNotFoundError(
        "未找到飞书适配器文件。已搜索以下路径：\n  - "
        + "\n  - ".join(str(p) for p in search_roots if p.exists())
        + "\n请确认 Hermes 已安装并对接飞书，或在使用此脚本前激活正确的虚拟环境。"
    )

def _confirm(prompt: str) -> bool:
    """交互式确认。在非 TTY 环境下默认通过（用于自动化脚本）。"""
    if not sys.stdin.isatty():
        return True
    try:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


def patch_adapter(adapter_path: Path) -> bool:
    """打补丁"""
    print(f"⚠️  即将修改文件：{adapter_path}")
    print("   原文件会备份为 *.py.bak.table_card，可用 --rollback 恢复。")
    if not _confirm("   确认继续？"):
        print("ℹ️  已取消")
        return False

    content = adapter_path.read_text(encoding="utf-8")
    
    # 备份原文件
    backup_path = adapter_path.with_suffix(".py.bak.table_card")
    if not backup_path.exists():
        shutil.copy(adapter_path, backup_path)
        print(f"✅ 原文件已备份到：{backup_path}")
    
    # 1. 替换表格检测正则
    old_regex = r'_MARKDOWN_TABLE_RE = re.compile\(r"\\^\\\\\\|.*\\\\\\|\\\\n\\\\\\|\[-: ]+\\\\\\|", re\.MULTILINE\)'
    new_regex = r'_MARKDOWN_TABLE_RE = re.compile(r"\|.*\|\s*\n\s*\|\s*[-:| ]+\|", re.MULTILINE)'
    
    if re.search(old_regex, content):
        content = re.sub(old_regex, new_regex, content)
        print("✅ 表格检测正则已优化")
    
    # 2. 替换_build_outbound_payload函数逻辑
    old_func_pattern = r'''def _build_outbound_payload\(self, content: str\) -> tuple\[str, str\]:
.*?if _MARKDOWN_TABLE_RE\.search\(content\):
.*?text_payload = \{"text": content\}
.*?return "text", json\.dumps\(text_payload, ensure_ascii=False\)
.*?if _MARKDOWN_HINT_RE\.search\(content\):
.*?return "post", _build_markdown_post_payload\(content\)
.*?text_payload = \{"text": content\}
.*?return "text", json\.dumps\(text_payload, ensure_ascii=False\)'''
    
    new_func = '''def _build_outbound_payload(self, content: str) -> tuple[str, str]:
        # Feishu post-type 'md' elements do not render markdown tables; 
        # instead of downgrading to text, send table content as interactive card
        # which supports full markdown rendering including tables
        if _MARKDOWN_TABLE_RE.search(content):
            # 修复飞书卡片自动把第一个#标题识别为全局卡片标题的问题
            # 前面加零宽空格避免被识别
            if content.strip().startswith("#"):
                content = "\u200B" + content
            card = {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {"tag": "markdown", "content": content}
                ]
            }
            # 飞书interactive类型要求外层必须包card字段
            return "interactive", json.dumps({"card": card}, ensure_ascii=False)
        if _MARKDOWN_HINT_RE.search(content):
            return "post", _build_markdown_post_payload(content)
        text_payload = {"text": content}
        return "text", json.dumps(text_payload, ensure_ascii=False)'''
    
    if re.search(old_func_pattern, content, flags=re.DOTALL):
        content = re.sub(old_func_pattern, new_func, content, flags=re.DOTALL)
        print("✅ 表格转卡片逻辑已注入")
    else:
        # 已经打过补丁的情况
        if "send table content as interactive card" in content:
            print("ℹ️  已经打过补丁，无需重复操作")
            return True
        print("❌ 未找到匹配的函数代码，可能Hermes版本不兼容")
        return False
    
    # 写入修改后的文件
    adapter_path.write_text(content, encoding="utf-8")
    print("✅ 补丁已成功写入")
    return True

def rollback(adapter_path: Path) -> bool:
    """回滚补丁"""
    backup_path = adapter_path.with_suffix(".py.bak.table_card")
    if not backup_path.exists():
        print("❌ 未找到备份文件，无法回滚")
        return False
    shutil.copy(backup_path, adapter_path)
    print("✅ 已回滚到原文件")
    return True

if __name__ == "__main__":
    try:
        adapter_path = find_feishu_adapter()
        print(f"✅ 找到飞书适配器：{adapter_path}")
        
        if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
            rollback(adapter_path)
        else:
            patch_adapter(adapter_path)
            
        print("\n🎉 操作完成，请重启Hermes网关生效！")
        
    except Exception as e:
        print(f"❌ 操作失败：{str(e)}", file=sys.stderr)
        sys.exit(1)

# Hermes飞书表格自动转卡片插件
✨ 自动将包含Markdown表格的飞书消息转为互动卡片渲染，完美解决飞书原生不支持表格渲染的问题，完全对齐OpenClaw使用体验，无侵入兼容原有逻辑。

## 🚀 特性
- ✅ **自动识别**：自动检测消息中的Markdown表格，无需手动操作
- ✅ **格式全兼容**：卡片内支持完整Markdown语法（表格、列表、加粗、代码块、链接、表情）
- ✅ **无侵入**：没有表格的普通消息完全沿用原有逻辑，不影响日常使用
- ✅ **宽屏模式**：默认开启宽屏卡片，内容展示更完整
- ✅ **自动降级**：卡片发送失败自动转为普通消息，100%不丢失内容
- ✅ **标题修复**：自动修复飞书卡片将首个#标题误识别为全局卡片标题的问题
- ✅ **对齐OpenClaw**：完全还原OpenClaw的飞书表格渲染体验，老用户无缝迁移
- ✅ **一键安装**：安装时加 `--enable` 参数即可自动启用，无需手动编辑 config.yaml

## 📦 安装
### 方式1：直接从GitHub安装（推荐）
```bash
hermes plugins install git+https://github.com/lukaisheng1203/hermes-plugin-feishu-table-card.git --enable
```
安装完成后**只需重启网关即可生效**，无需手动编辑 config.yaml。

### 方式2：本地安装
```bash
git clone https://github.com/lukaisheng1203/hermes-plugin-feishu-table-card.git
cd hermes-plugin-feishu-table-card
hermes plugins install . --enable
```

### 方式3：从PyPI安装（上传到PyPI后支持）
```bash
hermes plugins install hermes-plugin-feishu-table-card --enable
```

### 备用方式：一键补丁脚本（无需插件机制）
如果不想用插件，直接使用项目根目录下的 `patch_feishu_table_card.py` 脚本，一键给飞书适配器打补丁：
```bash
python3 patch_feishu_table_card.py
# 回滚补丁
python3 patch_feishu_table_card.py --rollback
```

## ⚙️ 配置项（可选）
安装时使用 `--enable` 参数已自动启用插件，通常无需任何额外配置。  
如需自定义行为，可在 `config.yaml` 中添加：
```yaml
plugins:
  enabled:
    - feishu_table_card
  entries:
    feishu_table_card:
      wide_screen: true          # 卡片宽屏模式（默认 true）
      auto_render_all: false     # 所有Markdown消息都转卡片（默认 false，仅表格转卡片）
```

## 🔑 权限要求
飞书机器人需要开通「发送互动卡片」权限，否则会自动降级为普通消息：
1. 进入飞书开放平台 → 你的应用 → 权限管理 → 搜索「消息与群组」
2. 开通「发送互动卡片（普通版）」权限并提交审核

## 📝 效果示例
发送内容：
```markdown
### 测试表格
| 功能 | 状态 |
|------|------|
| 表格渲染 | ✅ 支持 |
| 列表 | ✅ 支持 |
| 代码块 | ✅ 支持 |
```
自动转为带格式的卡片消息，表格完美渲染。

## 🤝 贡献
欢迎提交Issue和PR！

## 📄 许可证
MIT License

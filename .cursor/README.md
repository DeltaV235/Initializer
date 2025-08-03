# Cursor IDE 配置说明

## 📁 目录结构

```
.cursor/
├── instructions.md           # AI 指令文档
├── workspace.template.json   # 工作区配置模板
└── README.md                # 配置说明（本文件）
```

## 🚨 关键规则

这个项目配置了严格的远端执行规则：

- **禁止本地执行任何脚本**
- **所有脚本必须在远端服务器执行**
- **Cursor AI 会自动遵循这些规则**

## 📋 配置文件说明

### `.cursorrules`
- 项目根目录的主要规则文件
- Cursor AI 自动加载和遵循
- 包含完整的执行规则和工作流程

### `instructions.md`
- 项目上下文和技术信息
- 为 AI 提供项目背景

## 🎯 使用说明

1. **自动生效** - Cursor 会自动读取 `.cursorrules`
2. **规则提醒** - AI 会在建议脚本执行时自动提醒远端规则
3. **工作流程** - AI 会引导正确的 sync → SSH → execute 流程

## 🔧 自定义配置

如果需要修改远端服务器地址或其他设置：

1. 编辑 `.cursorrules` 中的服务器信息
2. 更新 `workspace.template.json` 中的 `remote_server` 配置
3. 修改各个文档中的 IP 地址引用

---

**Cursor AI 现在会自动遵循项目的远端执行规则！** 🤖
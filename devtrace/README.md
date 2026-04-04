# DevTrace

## 概述

DevTrace 是一个把项目推进过程沉淀成 `TraceUnit` 的 skill。该 skill 围绕跨时间事件追踪工作，维护 `01_CURRENT.md`、`00_INDEX.md`、`TraceUnit`、session context pack 和 review，帮助 AI 接上项目上下文、继续同一事件、保留工作细节，并支持日报、周报、月报和定时阶段记录。

## 使用

常见使用方式：

- 让 AI 记录当前会话：先判断是新事件还是旧事件续写，再写回 DevTrace
- 让 AI 续写已有事件：把本轮新进展补进原有 `TraceUnit`
- 让 AI 加载项目上下文：先读取 current，再读取 index，再读取相关 unit
- 让 AI 检索相关事件：按 tag / thread / 时间筛选相关内容
- 让 AI 生成日报、周报、月报或设置定时生成

## 命令

主脚本：

`scripts/devtrace_write.py`

主要命令：

- `init-project`
- `add-unit`
- `extend-unit`
- `capture-session`
- `split-material`
- `load-session`
- `generate-review`

## 目录

- `SKILL.md`：AI 执行规则
- `references/`：补充说明
- `scripts/`：落盘与生成脚本
- `assets/templates/`：模板文件
- `agents/openai.yaml`：skill 元数据

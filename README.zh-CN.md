# DevTrace

[English](./README.en.md)

## 项目简介

这个仓库是从已完成的 DevTrace 工作中独立拆出的 **skill 版本**。

它不是 Web 界面项目本身，而是把 DevTrace 里已经沉淀好的“开发过程整理能力”封装成一个可复用的 skill，专门用于把原始开发记录整理成结构化结果。

核心能力包括：

- 整理开发聊天记录
- 提炼主线脉络
- 提炼关键节点
- 提炼核心内容
- 绑定原文证据
- 输出结构化总结
- 按需生成 Markdown / TXT 导出内容

## 仓库结构

```text
DevTrace/
├─ README.md
├─ README.zh-CN.md
├─ README.en.md
└─ devtrace/
   ├─ SKILL.md
   ├─ README.md
   ├─ agents/
   │  └─ openai.yaml
   └─ references/
      ├─ workflow.md
      ├─ output-schema.md
      ├─ prompt-notes.md
      └─ examples.md
```

## 适用场景

适合这类任务：

- 根据 `.md` / `.txt` 聊天记录整理开发过程
- 从需求推进记录中提炼主线
- 对调试过程做复盘摘要
- 从讨论文本中抽取关键节点和证据
- 输出适合保存和分享的结构化总结

## 说明

仓库中的 `devtrace/SKILL.md` 是写给 AI / agent 看的核心文件；  
`devtrace/README.md` 是写给人看的 skill 说明。

这个仓库当前专注于 **Skill 部分**，与原来的 Web 应用部分独立维护。

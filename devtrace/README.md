# DevTrace Skill

这是 `DevTrace` 项目中独立拆出的 skill 版本，用来把开发过程记录整理成结构化结果。

它和 `E:\Visual Code\DevTrace` 里的 Web 应用是两套独立内容：

- Web 部分负责界面、导入、展示、导出等产品能力
- Skill 部分负责把 DevTrace 的整理方法封装成可复用能力

## 这个 skill 是干什么的

它主要用于：

- 整理开发聊天记录
- 提炼主线脉络
- 提炼关键节点
- 提炼核心内容
- 绑定原文证据
- 输出结构化总结
- 按需生成 Markdown / TXT 导出内容

## 适用场景

适合处理这类输入：

- `.md` 聊天记录
- `.txt` 聊天记录
- 需求推进记录
- 开发讨论文本
- 调试过程复盘
- 项目过程材料整理

## 目录结构

```text
devtrace/
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

## 各文件作用

### `SKILL.md`
skill 的核心文件，主要写给 AI / agent 看。  
定义了：

- 这个 skill 做什么
- 什么时候触发
- 怎么执行
- 输出结构是什么
- 什么时候读取参考资料

### `agents/openai.yaml`
skill 的界面元数据，提供：

- 展示名称
- 简短描述
- 默认提示语

### `references/workflow.md`
说明 DevTrace 的标准处理流程。

### `references/output-schema.md`
说明输出结构应该怎么组织。

### `references/prompt-notes.md`
整理 DevTrace 原有 prompt 实验里的关键偏好和规则。

### `references/examples.md`
给出典型请求和期望输出方式。

## 使用方式

当你要整理开发过程记录时，可以直接按下面这种方式触发：

- 帮我整理这段开发聊天记录
- 提炼这份讨论的主线脉络和关键节点
- 把这次需求推进过程整理成结构化总结
- 把这份记录整理成适合导出的 Markdown

## 说明

这个 skill 当前是基于 DevTrace 已经完成的工作内容提炼出来的，目标是：

- 忠实复用 DevTrace 的方法
- 不额外发明新产品逻辑
- 先把“开发过程整理能力”独立出来

如果后续需要，还可以继续补充：

- `scripts/`
- 更多 `references/`
- 示例输入输出

# DevTrace.skill

[English](./README.en.md) | [Design](./DESIGN.md)

## 概述

DevTrace 是一个面向长期工作的追踪项目。该项目把聊天、讨论、调试、实验、复盘中的关键信息沉淀成可跨时间追踪的事件单元，帮助 AI 在后续多轮工作中接上上下文、持续追踪同一事件、保留工作细节，并支持生成日报、周报、月报和定时阶段记录。

在整个项目里，共有4个核心元素：

* `01_CURRENT.md` ：记录当前状态，内容通常包括当前主线、当前问题、当前 blocker、下一步、最近变化。
* `00_INDEX.md` ：时间线记录，内容通常包括日期、事件入口、一句话概括、tag，可以快速回顾这段时间的工作内容，快速知道最近发生了什么、接下来该读哪些事件。
* `TraceUnit` ：负责记录事件事实，内容通常包括标题、一句话概括、细节、证据、状态、tag，作用把一大事件进行整体规划，保证跨时间追溯。
* `tag` ：主题标签，主要写在 `TraceUnit` 中，也显示在 `00_INDEX.md` 里，可按主题快速筛选相关事件。

## 设计

### `01_CURRENT.md`

 当前状态入口，快速知道当前工作位置。

常见内容：

- 当前主线
- 当前问题
- 当前 blocker
- 下一步
- 最近变化

例子：

```md
# 01_CURRENT

## 当前主线
- session-loader

## 当前问题
- relevant units 的筛选口径还不稳定

## 当前 blocker
- 新 session 进入后仍然不知道先读哪些 unit

## 下一步
- 固定 current -> index -> relevant units 的读取顺序

## 最近变化
- 2026-04-03：明确读取顺序
- 2026-04-02：补充 loader 相关筛选规则
```

### `00_INDEX.md`

 时间入口。面向用户和AI，用来快速知道最近的关键事件。

常见内容：

- 日期
- 事件入口
- 一句话概括
- tag

例子：

```md
# 00_INDEX

- YYYY-MM-DD [path/to/file.md] 一句话概括。 #tag1 #tag2 #type

- 2026-04-04 [reviews/daily/2026-04-04.md] 今日日报：读取顺序已经固定，主线转向筛选规则细化。 #loader #design #daily
- 2026-04-04 [reviews/weekly/2026-W14.md] 本周回顾：完成 current -> index -> 相关内容 的默认读取路径收敛。 #loader #review #weekly
- 2026-04-03 [reviews/session/2026-04-03-loader-summary.md] 会话总结：确认 index 作为生成内容入口，unit 作为事件事实层。 #loader #design #session-summary
```

另：这里的一句话概括可以由用户写，也可以由 AI 写。

### TraceUnit

该项目的核心记录对象。`TraceUnit` 记录的是值得跨时间继续追踪的事件，默认按一个大事件沉淀。

在同一事件里的 `problem / attempt / decision / next-step / result` 很多时候只是 unit 内部的一部分，我们加入了关于unit的特判逻辑，保证在只有在形成新的独立状态节点、值得未来单独加载时，才更适合单独成为新的 unit。

一个简单判断方式：

- 后面还会沿着这件事继续追，通常就值得成为 unit
- 只是同一事件里的补充细节，通常更适合续写已有 unit

### Tag

主题标签，主要写在 `TraceUnit` 、`00_INDEX.md` 里。AI 会结合 `tag / thread / date / status / affects_current` 去筛选相关事件。

当前内置常见 tag：

`meeting / experiment / debug / review / documentation / automation / design / loader`

用户可以自己写新的 tag，AI 也可以根据实际情况补充新的 tag。

### 阅读顺序

AI 一般

先阅读 current 明白当前状态  `01_CURRENT.md ->`

再用 index 定位最近时间线，查看上一次记录和最近时间线，并根据`tag`确定相关内容  `00_INDEX.md ->`

只有在 `current `和 `index `不足以支持继续工作时，才继续读取

* 相关日报 / 周报 / review
* 相关总结
* 带对应 tag 的 **`TraceUnit`**


## 使用

### 1. 记录

Skill 用法：

- `/skill devtrace 记录当前会话`
- `$devtrace 记录当前进展`

对 AI 说：

- `用 DevTrace 记录这轮工作 / 把这轮关于 loader 的推进写进 DevTrace / 把刚才这个 blocker 记到 DevTrace`

### 2. 续写

Skill 用法：

- `/skill devtrace 续写上一个 loader 事件`
- `$devtrace 继续这个事件`

对 AI 说：

- `继续之前那个 loader 事件，用 DevTrace 续写 / 把这轮新进展补进上次那个事件 / 这还是同一个问题，写回原来的 TraceUnit`

### 3. 加载

Skill 用法：

- `/skill devtrace 加载当前项目上下文`
- `$devtrace 读取 current 和 index`

对 AI 说：

- `用 DevTrace 加载当前项目上下文 / 先读 DevTrace 的 current 和 index / 用 DevTrace 帮我接上这个项目`

### 4. 检索

Skill 用法：

- `/skill devtrace 查找 loader 相关事件`
- `$devtrace 查找相关事件`

对 AI 说：

- `用 DevTrace 找 loader 相关事件 / 看最近的 design 变化 / 追一下这个事件的前后变化`

### 5. 回顾

Skill 用法：

- `/skill devtrace 生成本周周报`
- `$devtrace 设置每周五生成周报`

对 AI 说：

- `用 DevTrace 生成今天的日报 / 生成本月回顾 / 以后每天晚上 9 点用 DevTrace 生成日报 / 每周五下午用 DevTrace 生成周报`

一般生成的日报、周报、月报文件会放在项目目录下的 `reviews/` 中，例如 `reviews/daily/`、`reviews/weekly/`、`reviews/monthly/`。

## 文件目录

```text
DevTrace/
├─ DESIGN.md
├─ README.md
├─ devtrace/
│  ├─ SKILL.md
│  ├─ agents/
│  ├─ references/
│  ├─ assets/
│  └─ scripts/
```

- `DESIGN.md`：设计文档
- `devtrace/SKILL.md`：AI 执行规则
- `01_CURRENT.md`：当前状态入口
- `00_INDEX.md`：时间入口
- `trace/`：TraceUnit 存放目录

如有兴趣详细了解架构设计，可查看 [DESIGN.md](./DESIGN.md) 文档。

感觉不错的话可以给个star⭐哦

祝你天天开心(´▽`ʃ♡ƪ)

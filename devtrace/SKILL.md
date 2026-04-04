---
name: devtrace
description: 将项目推进中的聊天、会议、实验、调试、复盘等内容沉淀为可跨时间追踪的 TraceUnit，并维护 01_CURRENT.md、00_INDEX.md、session loader 与 review。用于新 session 接手项目、记录当前会话进展、续写已有事件、导入外部材料，或为日报 / 周报 / 月报创建定时自动化场景。
---

# DevTrace

## 结构口径

使用 DevTrace 时，先按下面四层理解：

1. **当前状态层**
   - `01_CURRENT.md`
2. **生成内容索引层**
   - `00_INDEX.md`
3. **事件事实层**
   - `TraceUnit`
4. **筛选与关系辅助层**
   - `tag / thread / date / status / affects_current`
   - `prev / next / related / supersedes`

不要把这些层混用。

固定分工如下：

- `01_CURRENT.md`：当前状态入口
- `00_INDEX.md`：生成内容索引入口
- `TraceUnit`：事件事实层
- `tag`：主题筛选标签
- `thread`：主线归属
- `unit_type`：事件类型

## 事件单元规则

把 `TraceUnit` 理解为 **事件事实单元**，不要理解为聊天切片或默认阅读入口。

每个 `TraceUnit` 至少回答：

- 发生了什么事件
- 当前状态是什么
- 属于哪条 thread
- 是否影响当前状态
- 未来是否还值得继续追踪

默认粒度规则：

- 当前会话默认优先沉淀为 **一个大事件 unit**
- 只有当前轮里真的出现了第二个独立大事件，才拆多个 unit
- `problem / attempt / decision / next-step / result` 很多时候只是同一个大事件内部的组成部分
- 重复确认、补充说明、局部排查，优先并入已有事件的 `details / evidence`

如果当前内容只是已有事件的继续推进，优先：

- 定位旧 `TraceUnit`
- 续写旧 unit
- 不要默认新开 unit
- `capture-session` 默认会先尝试自动判断是否应续写旧事件

## Index 规则

`00_INDEX.md` 是**生成内容索引**，不是 `TraceUnit` 索引。

它主要记录：

- 用户主动让 AI 生成的内容
- 定时自动生成的内容
- 可供用户和 AI 回看与导航的内容入口

典型内容包括：

- 当前会话总结
- 阶段总结
- review
- 日报
- 周报
- 月报
- 定时生成的日报 / 周报 / 月报

默认不直接把“单纯新建 unit / 单纯续写 unit”写成 index 主记录项；只有产生新的生成内容时，才把它写入 `00_INDEX.md`。

## 读取规则

处理任务时，不要直接全读所有 unit。

先按顺序：

1. 读 `01_CURRENT.md`
2. 读 `00_INDEX.md`
3. 看 index 中最近生成了什么内容
4. 根据任务、tag、类型、时间线决定后续读取方向
5. 必要时再深入读取 relevant `TraceUnit`

也就是说：

- `current` 管现在
- `index` 管最近生成了什么
- `TraceUnit` 管事件事实

### 不同任务的读取重点

#### 继续当前主线
优先看：
- `01_CURRENT.md`
- index 中最近的会话总结 / 阶段记录
- 与当前主线 tag / thread 相关的内容
- 必要时再读相关 `TraceUnit`

#### 追某个具体事件
优先看：
- index 中与该事件相关的生成记录
- 对应 `tag`
- 对应 `thread`
- 必要时再继续读相关 `TraceUnit`

#### 查看某个主题
优先看：
- index 中对应 `tag` 的内容
- 最近时间
- 必要时再补读同主题 `TraceUnit`

#### review / 阶段复盘
优先看：
- 时间窗内的日报 / 周报 / 月报 / review
- 必要时再补读支撑这些内容的高价值 `TraceUnit`

### 扩读条件

只有这些情况才继续扩读 `TraceUnit`：

- current 和 index 还不足以解释当前状态
- 用户要看某个事件全貌
- 当前任务要求追某个事件的前后变化
- 当前生成内容需要进一步回到底层事实核对

如果 current 和 index 已经足够支持当前任务，不要默认扩读很多历史 unit。

## tag / thread / unit_type 的执行约束

执行时保持：

- `tag` 主要用于主题筛选，例如 `automation / design / review / daily / weekly`
- `thread` 主要用于主线归属，不要把它当普通标签堆叠
- `unit_type` 只用于描述事件类型，不要拿它替代主题标签
- 生成内容的类型优先通过 index 记录项中的 tag 表达，例如 `#session-summary / #review / #daily / #weekly / #monthly`

## 关系字段的轻量规则

`prev / next / related / supersedes` 只做最小导航，不做复杂事件图。

执行时用下面的最小规则：

- **前后承接**：写 `prev / next`
- **横向强相关，但不是前后推进**：写 `related`
- **新状态覆盖旧状态**：写 `supersedes`

默认不要硬补关系。

只有在下面情况才优先补：

1. 新 unit 明显接着某个旧 unit 往下走
2. 新 unit 明显只是横向补充某个旧 unit
3. 新 unit 明显让某个旧状态失效

如果只是旧事件补细节：直接续写旧 unit，不必补关系。

## 当前会话提炼规则

主路径是：**当前会话 -> 判断新旧事件 -> 写回**。

处理当前会话时，按这个顺序：

1. 先读 `01_CURRENT.md`
2. 再读 `00_INDEX.md`
3. 判断当前会话是新事件还是旧事件续写
4. 默认优先沉淀成一个大事件 unit
5. 写入或续写 `TraceUnit`
6. 如果本轮还产生了新的总结 / review / 日报周报等生成内容，再写入 `00_INDEX.md`
7. 再按需更新 `01_CURRENT.md`

在“旧事件续写 vs 新开 unit”上，执行时继续用这条边界：

- **只是补充细节 / 补做验证 / 继续排查**：优先续写旧 unit
- **旧 blocker 还在，但已经形成明确 next-step / 决策**：优先新开 unit
- **旧 blocker 被解除，或拿到明确结果**：优先新开 `result` unit
- **主线或方案发生转向**：优先新开 `decision / direction-shift` unit

## review / 阶段回顾口径

`generate-review` 应输出基于事实层组织的阶段视图，而不是简单堆结果。

优先组织为：

- 当前状态背景
- 本周期关键推进
- 关键决策与转向
- 风险与 blocker
- 下一步建议
- 参考 TraceUnit

## 定时自动化规则

如果用户要求：

- 定时生成日报
- 定时生成周报
- 定时生成月报

默认只使用 **AI 自动任务** 方案，不默认建议用户自己配置外部调度器。

执行时应理解为：

1. 由 AI 创建自动任务
2. 定时运行 DevTrace 的 review 生成流程
3. 输出到 `reviews/daily/`、`reviews/weekly/`、`reviews/monthly/`
4. 生成后继续写入 `00_INDEX.md`

自动任务的 prompt 应明确：

- 使用 DevTrace
- 读取 current / index / relevant TraceUnit
- 生成对应周期的 review
- 写入固定目录
- 完成后更新 index

如果平台不方便直接表达月度调度，也仍然保持 AI 自动任务方案：

- 让任务按更高频运行
- 在任务内部判断本次是否应该生成月报
- 不要改回外部调度器方案

## AI 的执行约束

执行时遵守：

1. `01_CURRENT.md` 是当前状态入口
2. `00_INDEX.md` 是生成内容索引，不是 `TraceUnit` 索引
3. `TraceUnit` 是事实层，不是默认第一阅读入口
4. 默认先读 current，再读 index，再按 index 和 tag 决定后续读取
5. tag / thread / date / status / affects_current 是筛选辅助，不是事件关系
6. 关系字段只属于 unit 内部，不要把 `prev / next` 当成筛选层
7. 默认优先沉淀事件，而不是停留在自由总结
8. 默认优先判断“新事件还是旧事件续写”
9. 当前会话默认先按一个大事件理解，不要急着切碎
10. 更新 `01_CURRENT.md` 时，按覆盖 / 保留 / 追加处理，而不是机械填槽
11. 只有在生成了新的导航内容时，才写入 `00_INDEX.md`
12. 如果用户要求定时日报 / 周报 / 月报，默认创建 AI 自动任务，不默认改成外部计划任务

需要落地写文件时，优先使用：

- `scripts/devtrace_write.py`

按需读取参考：

- `references/workflow.md`
- `references/traceunit-schema.md`
- `references/index-current.md`
- `references/session-loader.md`
- `references/writeback.md`
- `references/examples.md`

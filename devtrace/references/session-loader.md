# Session Loader

`session loader` 回答的是：

> 新开 AI 对话时，应该先读什么，再根据什么决定继续读哪些内容。

它不是“全量加载器”，而是一个 **当前状态 -> 生成内容索引 -> 按需下钻** 的规则。

## 一、稳定读取顺序

默认读取顺序固定为：

1. 先读 `01_CURRENT.md`
2. 再读 `00_INDEX.md`
3. 看 index 中最近生成了什么内容
4. 根据任务、tag、记录类型、时间线决定后续读取方向
5. 必要时再读 relevant `TraceUnit`

也就是说：

- `current` 负责把 AI 带到“现在”
- `index` 负责把 AI 带到“最近生成了什么”
- `TraceUnit` 负责承载事件事实

---

## 二、不同任务类型的读取路径

### 1. 新 session 接手项目

目标：

- 快速知道项目现在到哪了
- 快速知道最近记录了什么
- 找到当前最该继续的内容

读取顺序：

1. `01_CURRENT.md`
2. `00_INDEX.md`
3. 看最近的会话总结 / review / 日报周报
4. 必要时再读支撑这些内容的相关 `TraceUnit`

### 2. 继续当前主线工作

目标：

- 在当前主线上直接继续推进

优先读取：

1. current 中的当前主线 / blocker / 下一步
2. index 中最近与该主线相关的生成内容
3. 必要时再补读相关 `TraceUnit`

### 3. 追某个具体事件

目标：

- 还原某个事件的来龙去脉

读取路径：

1. 先从 index 找到与该事件相关的生成内容
2. 再看对应 tag / 时间线
3. 必要时再进入相关 `TraceUnit`
4. 再沿 `prev / next / related / supersedes` 继续追

### 4. 查看某个主题

例如：

- automation
- design
- review
- loader

优先读取：

1. index 中对应 `tag` 的生成内容
2. 最近时间窗内的相关内容
3. 必要时再补读同主题 `TraceUnit`

### 5. 做阶段复盘 / review

目标：

- 看到某个时间窗内的关键推进

优先读取：

1. 时间窗内的日报 / 周报 / 月报 / review
2. 当前主线相关的生成内容
3. 必要时再补读高价值 `TraceUnit`

---

## 三、什么时候需要继续读 `TraceUnit`

默认不要一上来就读很多 unit。

只有这些情况才继续深入：

### 条件 1

current 和 index 还不能解释：

- 当前 blocker 从哪来
- 当前主线为什么是这样
- 当前 next-step 为什么成立

### 条件 2

用户要的是：

- 这个事情的完整经过
- 为什么会变成这样
- 之前是怎么演化过来的

### 条件 3

当前生成内容需要继续回到底层事实核对：

- review 需要补事实来源
- 日报 / 周报需要补事件细节
- 会话总结需要继续追某个事件

如果 current 和 index 已经足够支持当前任务，不要默认扩读很多历史 unit。

---

## 四、输出目标

session loader 的输出不应是一堆原文，而应是：

- 当前状态摘要
- 最近生成内容摘要
- 当前任务最相关的 tag / 类型 / 时间线
- 是否需要继续深入到 `TraceUnit`

## 五、命令入口

```powershell
python scripts/devtrace_write.py load-session --project-dir <项目目录>
```

常见变体：

```powershell
python scripts/devtrace_write.py load-session --project-dir <项目目录> --days 7 --limit 5
python scripts/devtrace_write.py load-session --project-dir <项目目录> --thread evaluation
python scripts/devtrace_write.py load-session --project-dir <项目目录> --tags automation review
```

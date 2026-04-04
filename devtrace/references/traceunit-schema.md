# TraceUnit Schema

`TraceUnit` 是 DevTrace 的主事实对象。

它不是入口，也不是筛选条件，而是：

- 被长期维护的事件事实单元
- 能被单独加载的事件对象
- 能被后续续写的事件对象

## `TraceUnit` 的字段分组

### 一、内容字段

```yaml
title:
summary:
details:
evidence:
status:
```

作用：

- 保存事件本体内容
- 保存当前状态与证据

### 二、类型字段

```yaml
unit_type:
```

作用：

- 标记该 `TraceUnit` 的核心状态变化类型

常见值：

- `context`
- `problem`
- `attempt`
- `failure`
- `decision`
- `direction-shift`
- `result`
- `blocker`
- `next-step`
- `review`

注意：

> `unit_type` 是 `TraceUnit` 的内部类型字段，不是主题标签。

### 三、关系字段

```yaml
prev:
next:
related:
supersedes:
```

作用：

- 表示该 `TraceUnit` 与其他 `TraceUnit` 的关系

含义：

- `prev`：前序承接
- `next`：后续承接
- `related`：横向关联
- `supersedes`：覆盖旧状态

注意：

> 关系字段是 `TraceUnit` 的内部关系字段，不是筛选层。

推荐使用口径：

- **前后承接**时写 `prev / next`
- **横向强相关**时写 `related`
- **新状态覆盖旧状态**时写 `supersedes`

不要求每个 `TraceUnit` 都补关系字段；
只有当关系明显、且值得未来继续导航时再写。

### 四、检索与筛选字段

```yaml
thread:
tags:
date:
affects_current:
```

作用：

- 帮助 AI 从很多 unit 中筛出 relevant content / TraceUnit

其中职责应保持：

- `thread`：主线归属
- `tags`：主题筛选标签
- `date`：时间范围筛选
- `affects_current`：当前有效性筛选

不要把：

- `tags` 当成 `unit_type` 的替代
- `thread` 当成任意主题标签

## 推荐完整结构

```yaml
id:
project:
date:
title:
source_type:
source_ref:
raw_refs:
unit_type:
thread:
tags:
summary:
details:
evidence:
status:
affects_current:
importance:
confidence:
prev:
next:
related:
supersedes:
```

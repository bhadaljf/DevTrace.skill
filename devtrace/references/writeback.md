# Writeback

写回机制回答的是：

> 当前会话或补充材料产生了新进展后，如何把它稳定写回到 DevTrace。

## 何时需要写回

以下情况通常应写回：

- 形成新的结论
- 出现新的 blocker
- 方向发生切换
- 获得新的实验结果
- 确认新的 next-step
- 对已有事件有了新的推进

## 默认写回顺序

### 1. 先判断：新事件还是旧事件续写

这是当前阶段最重要的判断。

- 如果形成独立新状态：新开 `TraceUnit`
- 如果只是已有事件继续推进：续写旧 `TraceUnit`
- `capture-session` 默认先尝试自动判断是否应续写最近相关旧事件

这里再补一层边界：

- **继续补充旧 blocker / 旧问题的细节**：续写旧 unit
- **旧 blocker 还在，但已经形成明确 next-step / 决策**：新开 unit
- **旧 blocker 被解除，出现明确结果**：新开 `result` unit
- **主线或方案发生转向**：新开 `decision / direction-shift` unit

即：

> 默认先判断是否相关，再判断它是不是已经变成“值得未来单独加载的新状态节点”。

脚本只做轻量辅助，不替代 AI 的最终理解：

- 明显仍是同一状态，就允许自动续写
- 明显已经变成新状态，就不要自动并回旧 unit
- 如果 AI 明确知道要续写，可以显式指定续写目标

### 2. 更新 `00_INDEX.md`

只有当本轮产生了新的生成内容时，才更新 `00_INDEX.md`。

典型情况包括：

- 会话总结生成后
- review 生成后
- 日报 / 周报 / 月报生成后
- 定时任务生成后

### 3. 按需更新 `01_CURRENT.md`

当它改变了：

- 当前主线
- 当前问题
- 当前 blocker
- 下一步
- 最近变化

才更新 `01_CURRENT.md`。

### 4. 按需生成派生结果

例如：

- session context pack
- daily / weekly / monthly review

## 写回原则

- 优先写事件事实，不停留在自由总结
- 当前会话默认优先按一个大事件理解
- 能续写旧事件，就不要默认新开 unit
- current 只保留当前仍有效状态
- current 更新优先按覆盖 / 保留 / 追加处理
- 旧状态失效时，应被覆盖或标记为被替代

## 推荐命令

初始化项目：

```powershell
python scripts/devtrace_write.py init-project --project-dir <项目目录>
```

新增一个事件 unit：

```powershell
python scripts/devtrace_write.py add-unit --project-dir <项目目录> --input <原始材料文件> --unit-type decision --thread evaluation --tags decision evaluation --affects-current
```

续写已有事件：

```powershell
python scripts/devtrace_write.py extend-unit --project-dir <项目目录> --target TU-2026-04-02-001 --input <SESSION_CAPTURE.md> --status active --affects-current
```

沉淀当前会话：

```powershell
python scripts/devtrace_write.py capture-session --project-dir <项目目录> --input <SESSION_CAPTURE.md>
```

导入外部材料：

```powershell
python scripts/devtrace_write.py split-material --project-dir <项目目录> --input <RAW_NOTE.md>
```

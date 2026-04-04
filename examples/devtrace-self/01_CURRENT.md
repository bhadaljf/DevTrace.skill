# 01_CURRENT

## 当前主线
- skill-core

## 当前问题
- 需要把 DevTrace 从“聊天记录整理器”明确升级为“以分割系统为核心的项目上下文加载 Skill”。

## 当前 blocker
- 当前已经落了规则层骨架，但还没有补最小可运行脚本来自动生成 `TraceUnit`、更新 `00_INDEX.md` 和 `01_CURRENT.md`。

## 下一步
- 先用真实项目样本验证 `TraceUnit / index / current` 的结构是否顺手。
- 再补一个最小脚本，把原始材料转成标准化 `TraceUnit`。

## 最近变化
- 2026-04-02：正式确定 DevTrace 的核心不是单次总结，而是“分割系统”。
- 2026-04-02：已落地 `TraceUnit schema`、`index/current`、session loader 和回写机制。

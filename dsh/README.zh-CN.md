[English](./README.md) | [简体中文](./README.zh-CN.md)

# DSH 专属技能

本分类存放依赖 DeepSeek Harness 能力的技能，不宣称适用于其他 agent 平台。每个子技能独立完整，并说明所需能力。

## 技能列表

- **[council](./council/)**：借助 Agent Teams，让三个不同模型独立提出意见，当前 lead 主持按需补证和最终裁决。需要开启允许 lead 选择子智能体模型的能力。

## 安装

把具体技能目录安装或软链接到当前 DSH 配置的技能根目录，不假定链接整个分类后就能发现下级技能。安装与验证方式见各技能 README；分类目录本身没有 `SKILL.md`。

## 目录结构

- `README.md` 和 `README.zh-CN.md`：分类索引与安装边界。
- `council/`：完整 Council 技能，包含独立技能入口和双语说明。

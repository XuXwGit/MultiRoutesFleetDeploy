# multi.model 说明

本包包含船舶调度与多类型集装箱联合调度问题的核心建模类，分为原始模型（primal）与对偶模型（dual）两大部分。

## 目录结构
- primal/  原始问题建模（主问题、子问题、确定性/随机/反应式等）
- dual/    对偶问题建模（对偶主问题、对偶子问题等）

## 主要类说明与继承关系

### primal 子包
- `BasePrimalModel`
  - `DetermineModel`（确定性优化模型）
  - `SubProblem`（二阶段子问题）
  - `SubProblemReactive`（反应式子问题）
  - `MasterProblem`（Benders分解主问题）
  - `CapacityCalculate`（容量计算模型，若有）
  - `PrimalDecision`（决策变量辅助类）

### dual 子包
- `BaseDualModel`
  - `DualProblem`（对偶主问题）
  - `DualSubProblem`（对偶子问题/Benders切割）
    - `DualSubProblemReactive`（反应式对偶子问题）

## 设计思想
- 采用面向对象分层设计，基类抽象通用接口，子类实现具体模型。
- 支持多种优化范式（确定性/随机/对偶/分解等），便于算法扩展。
- 变量、约束、目标函数均以方法形式封装，便于自动化建模与复用。

---
如需详细了解每个类的接口和用法，请查阅对应子包下的源代码和注释。 
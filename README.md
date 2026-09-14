# Lottery Engine — 营销抽奖引擎

> 本项目中的 "lottery" 指**营销抽奖**（运营活动的抽奖/转盘），不是彩票号码预测。

仓库里有两套实现，但**只有 Python 版在维护**：

| 实现 | 状态 | 技术栈 | 端口 | 入口 |
| --- | --- | --- | --- | --- |
| Python 版 | **主线（Active）** | FastAPI、SQLAlchemy、MySQL、Redis | 8000 | [`lottery_python/`](lottery_python/) |
| Java 版 | **Legacy / Reference（冻结）** | Spring Boot、MyBatis、MySQL、Redis、RocketMQ、Dubbo | 8080 | [`src/`](src/) |

## 文档入口

| 文档 | 作用 |
| --- | --- |
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | **规划文档**：项目定位、技术栈、架构原则、Phase 排期、停止线 |
| [`lottery_python/REQUIREMENTS.md`](lottery_python/REQUIREMENTS.md) | **需求规格**：功能需求、数据模型 DDL、API 契约、验收标准、已知缺陷 |
| [`lottery_python/README.md`](lottery_python/README.md) | Python 版启动说明与当前能力 |
| [`docs/java-quickstart.md`](docs/java-quickstart.md) | Java 版历史启动指南（已冻结，见下方说明） |

有冲突时以 `docs/PROJECT_PLAN.md` 为准。

## 目录结构

```text
lottery_engine/
├─ lottery_python/              Python/FastAPI 实现（主线）
├─ src/                         Java 源码、配置和数据库脚本（Legacy）
├─ docs/                        规划文档与启动指南
├─ scripts/                     只读辅助脚本
├─ archive/2026-07-31/          历史材料，其中的进度数字全部作废
├─ pom.xml                      Java/Maven 配置（Legacy）
└─ README.md
```

## Python 版（主线）

默认 SQLite 本地启动，Phase 1 起迁移到 MySQL。启动说明见
[`lottery_python/README.md`](lottery_python/README.md)。

启动后入口：

- 健康检查：`http://127.0.0.1:8000/api/health`
- Swagger：`http://127.0.0.1:8000/docs`

## Java 版（Legacy / Reference）

自 2026-09-14 起冻结：**不删除、不维护、不与 Python 版同步、不再为本项目深入 Java 生态**。

这套代码**从未成功编译或启动过**。已知缺陷记录在
[`lottery_python/REQUIREMENTS.md` §9.2](lottery_python/REQUIREMENTS.md)，**不计划修复**，其中最关键的两条：

- `src/main/resources/application.yml` 存在两个顶层 `spring:` 键，Spring Boot 的 YAML
  加载器禁止重复键，启动即抛 `DuplicateKeyException`。这是历史上"8080 端口不监听"
  长期无解的真实原因。
- `schema.sql` 没有订单表，`ActivityPartakeImpl.recordDrawOrder()` 是空实现，
  抽奖不留任何记录。

`docs/java-quickstart.md` 保留为历史参考，其中的 `mvn clean package` 步骤实际跑不通。

## 归档目录

`archive/2026-07-31/` 是 2026-07-31 目录治理时的历史留存。其中所有进度描述
（"完成度 85%"、"95%"、"责任链 100%"）经代码核实**全部不成立**，不得作为判断依据。
该目录不再维护，也不应被当前文档或脚本引用。

## 开发约定

- 不提交 `target/`、虚拟环境、Python 字节码、本地数据库、测试缓存、`.env`。
- 长期文档放在 `docs/` 或对应实现目录，不在根目录堆临时 Markdown。
- 阶段进度写进 `REQUIREMENTS.md` 的验收清单，不再单独建进度文件。
- Java 状态检查可运行 `scripts/check-java-status.ps1`（只读）。

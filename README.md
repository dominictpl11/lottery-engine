# 智能营销抽奖引擎

本仓库并列维护两套抽奖引擎实现：

| 实现 | 技术栈 | 默认端口 | 入口 |
| --- | --- | --- | --- |
| Java 版 | Spring Boot、MyBatis、MySQL、Redis、RocketMQ、Dubbo | 8080 | [`src/`](src/) |
| Python 版 | FastAPI、SQLAlchemy、SQLite，可选 Redis | 8000 | [`lottery_python/`](lottery_python/) |

两套实现用于演示相同的抽奖领域，但依赖、数据存储和接口结构相互独立。

## 目录结构

```text
lottery_engine/
├─ src/                         Java 源码、配置和数据库脚本
├─ lottery_python/              Python/FastAPI 实现
├─ docs/                        当前有效的项目文档
├─ scripts/                     安全的本地辅助脚本
├─ archive/2026-07-31/          不再维护的历史材料
├─ pom.xml                      Java/Maven 配置
└─ README.md                    项目统一入口
```

`archive/` 仅用于本次清理后的临时保留，不是正式文档入口。

## Java 版

环境要求：

- JDK 8+
- Maven 3.6+
- MySQL 8.x
- Redis
- 使用对应功能时准备 RocketMQ 和 ZooKeeper

完整的数据库初始化、配置、启动和接口验证步骤见
[`docs/java-quickstart.md`](docs/java-quickstart.md)。

在 Windows 上也可以从任意工作目录运行：

```bat
scripts\start-java.bat
```

启动后健康检查地址：

```text
http://localhost:8080/lottery/api/lottery/health
```

## Python 版

Python 版默认使用本地 SQLite，适合快速运行和继续开发。启动说明、当前接口和功能状态见
[`lottery_python/README.md`](lottery_python/README.md)。

需求与阶段目标见
[`lottery_python/REQUIREMENTS.md`](lottery_python/REQUIREMENTS.md)。

启动后的主要入口：

- 健康检查：`http://127.0.0.1:8000/api/health`
- Swagger：`http://127.0.0.1:8000/docs`

## 数据库脚本

Java 版只维护以下两个数据库脚本：

- [`src/main/resources/db/schema.sql`](src/main/resources/db/schema.sql)：表结构
- [`src/main/resources/db/test-data.sql`](src/main/resources/db/test-data.sql)：示例数据

根目录旧版合并脚本已经归档，避免多个副本继续产生差异。

## 开发约定

- 不提交 `target/`、虚拟环境、Python 字节码、本地数据库和测试缓存。
- 新的长期文档放在 `docs/` 或对应实现目录中。
- 临时诊断结果和阶段进度不再作为根目录 Markdown 文件保存。
- Java 状态检查可运行 `scripts/check-java-status.ps1`，该脚本只执行只读检查。

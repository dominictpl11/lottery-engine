# Java 版快速开始

本文是 Java/Spring Boot 实现的唯一启动指南。项目默认使用 `8080` 端口和
`/lottery` 上下文路径。

## 1. 准备环境

需要安装：

- JDK 8+
- Maven 3.6+
- MySQL 8.x
- Redis

当前配置还包含 RocketMQ 和 ZooKeeper。使用消息队列或 Dubbo 功能时，请分别确保
`localhost:9876` 和 `localhost:2181` 可用。

## 2. 初始化 MySQL

进入 MySQL 客户端：

```bash
mysql -u root -p
```

在项目根目录启动客户端后执行：

```sql
CREATE DATABASE IF NOT EXISTS lottery_db
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE lottery_db;
SOURCE src/main/resources/db/schema.sql;
SOURCE src/main/resources/db/test-data.sql;
```

`schema.sql` 和 `test-data.sql` 是当前唯一维护的 Java 数据库脚本。重复执行测试数据
前，请先确认目标库中的现有数据是否需要保留。

## 3. 检查配置

配置文件位于 `src/main/resources/application.yml`。启动前至少核对：

- `spring.datasource` 下的 MySQL 地址、用户名和密码
- `spring.redis` 下的 Redis 地址、端口和密码
- RocketMQ NameServer 地址
- Dubbo/ZooKeeper 注册中心地址

不要把本机密码写入准备提交或分享的配置文件。

## 4. 启动应用

在项目根目录运行：

```bash
mvn spring-boot:run
```

Windows 用户也可以从任意目录运行：

```bat
scripts\start-java.bat
```

打包运行：

```bash
mvn clean package
java -jar target/lottery-engine-1.0.0.jar
```

## 5. 验证接口

健康检查：

```bash
curl http://localhost:8080/lottery/api/lottery/health
```

预期响应为 `OK`。

执行抽奖：

```bash
curl -X POST http://localhost:8080/lottery/api/lottery/draw \
  -H "Content-Type: application/json" \
  -d '{"uId":"user001","activityId":100001}'
```

Windows PowerShell 状态检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-java-status.ps1
```

状态脚本只读取 Java 进程、8080 端口和健康接口，不会终止进程或修改系统。

## 6. 常见问题

### Maven 或 Java 不可用

分别运行 `java -version` 和 `mvn -version`，确认命令位于 `PATH`。项目没有正式的
Maven Wrapper，请使用系统 Maven。

### 数据库连接失败

确认 MySQL 已启动、`lottery_db` 已创建，并检查 `application.yml` 中的连接信息。

### Redis 连接失败

使用 `redis-cli ping` 检查服务；正常响应为 `PONG`。

### 8080 端口被占用

在 PowerShell 中运行：

```powershell
Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
```

确认占用进程后再决定停止对应应用，避免批量结束所有 Java 进程。

### RocketMQ 或 ZooKeeper 不可用

检查本地端口和应用日志，并根据是否需要 MQ/Dubbo 功能调整本机服务。现有
`application.yml` 的运行配置问题不属于本次目录清理范围。

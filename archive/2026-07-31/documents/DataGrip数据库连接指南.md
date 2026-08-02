# DataGrip 数据库连接和初始化指南

## 📋 数据库信息

- **数据库名称**: `lottery_db`
- **数据库类型**: MySQL
- **字符集**: utf8mb4
- **默认端口**: 3306
- **默认用户名**: root
- **默认密码**: root（根据您的实际配置调整）

## 🔌 在 DataGrip 中连接数据库

### 步骤 1: 创建数据源

1. 打开 DataGrip
2. 点击左上角的 **"+"** 或 **"Database"** → **"+"** → **"Data Source"** → **"MySQL"**
3. 填写连接信息：
   - **Host**: `localhost`
   - **Port**: `3306`
   - **Database**: `lottery_db`（可以先不填，稍后创建）
   - **User**: `root`
   - **Password**: `root`（您的实际密码）
4. 点击 **"Test Connection"** 测试连接
5. 如果提示缺少驱动，DataGrip 会自动下载 MySQL 驱动
6. 点击 **"OK"** 保存连接

### 步骤 2: 执行初始化脚本

1. 在 DataGrip 中打开文件：`setup-complete.sql`
2. 或者右键点击数据源 → **"Open Query Console"**
3. 将 `setup-complete.sql` 的内容复制到查询控制台
4. 点击执行按钮（▶️）或按 `Ctrl+Enter`（Windows）/ `Cmd+Enter`（Mac）

脚本会执行以下操作：
- ✅ 创建数据库 `lottery_db`
- ✅ 创建 4 个表：`activity`、`strategy`、`strategy_detail`、`award`
- ✅ 插入测试数据
- ✅ 显示验证信息

### 步骤 3: 刷新并查看数据库

1. 执行完脚本后，右键点击数据源
2. 选择 **"Refresh"**（刷新）
3. 展开数据库，您应该能看到：
   - 📁 `lottery_db`
     - 📋 `activity`（活动表）
     - 📋 `strategy`（策略表）
     - 📋 `strategy_detail`（策略明细表）
     - 📋 `award`（奖品表）

## ✅ 验证数据库是否正确创建

在 DataGrip 的查询控制台中执行以下 SQL：

```sql
USE lottery_db;

-- 查看表数量
SELECT COUNT(*) as table_count 
FROM information_schema.tables 
WHERE table_schema = 'lottery_db';

-- 查看活动数据
SELECT * FROM activity;

-- 查看策略数据
SELECT * FROM strategy;

-- 查看奖品数据
SELECT * FROM award;
```

预期结果：
- `activity` 表应该有 2 条记录
- `strategy` 表应该有 2 条记录
- `strategy_detail` 表应该有 11 条记录
- `award` 表应该有 10 条记录

## 🔧 如果遇到问题

### 问题 1: 连接失败

**错误**: `Access denied for user 'root'@'localhost'`

**解决方案**:
1. 确认 MySQL 服务已启动
2. 检查用户名和密码是否正确（查看 `src/main/resources/application.yml`）
3. 如果密码不是 `root`，修改 DataGrip 连接配置

### 问题 2: 数据库已存在

**错误**: `Database 'lottery_db' already exists`

**解决方案**:
- 这是正常的，脚本使用了 `IF NOT EXISTS`，不会报错
- 如果想重新创建，可以先删除数据库：
  ```sql
  DROP DATABASE IF EXISTS lottery_db;
  ```
  然后重新执行 `setup-complete.sql`

### 问题 3: 表已存在但想重新创建

如果需要清空并重新创建所有数据：

```sql
USE lottery_db;

-- 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 清空表数据
TRUNCATE TABLE activity;
TRUNCATE TABLE strategy;
TRUNCATE TABLE strategy_detail;
TRUNCATE TABLE award;

-- 启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 重新执行 setup-complete.sql 的插入部分
```

## 📊 数据库表结构说明

### 1. activity（活动表）
- 存储抽奖活动的基本信息
- 包含活动ID、名称、描述、时间范围、库存等

### 2. strategy（策略表）
- 存储抽奖策略配置
- 包含策略模式、发放方式等

### 3. strategy_detail（策略明细表）
- 存储每个策略的奖品配置
- 包含奖品ID、中奖概率、库存等

### 4. award（奖品表）
- 存储奖品详细信息
- 包含奖品类型、名称、内容等

## 📝 相关配置文件

数据库连接配置在 `src/main/resources/application.yml`：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/lottery_db?useUnicode=true&characterEncoding=utf8&useSSL=false&serverTimezone=Asia/Shanghai
    username: root
    password: root
```

确保 DataGrip 中的连接信息与上述配置一致。


# 快速执行SQL脚本

## 🚀 最快的方法

### 方法1：复制粘贴执行（最简单）

1. 打开 `init-database.sql` 文件
2. 全选复制（Ctrl+A, Ctrl+C）
3. 打开MySQL客户端（命令行或工具）
4. 粘贴执行（Ctrl+V, Enter）

### 方法2：命令行执行

```bash
# 在项目根目录执行
mysql -u root -p < init-database.sql

# 输入密码后回车
```

### 方法3：在MySQL客户端中

1. 打开MySQL客户端
2. 连接到服务器
3. 执行：`source d:/projects/lottery_engine/init-database.sql`
   （注意：使用正斜杠 /，不是反斜杠 \）

---

## ✅ 执行后验证

执行以下SQL验证：

```sql
USE lottery_db;
SELECT COUNT(*) as activity_count FROM activity;  -- 应该返回 2
SELECT COUNT(*) as strategy_count FROM strategy;  -- 应该返回 2
```

如果都返回正确的数字，说明初始化成功！






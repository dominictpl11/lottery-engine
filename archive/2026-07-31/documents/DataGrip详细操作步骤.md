# DataGrip 详细操作步骤（图文版）

## 🎯 重要说明
**您不需要手动创建 schema（数据库）！** 脚本会自动创建 `lottery_db` 数据库。

---

## 📋 完整操作步骤

### 步骤 1: 打开 DataGrip 并创建数据源连接

1. **打开 DataGrip**

2. **创建新的数据源连接**
   - 方法一：点击左上角的 **"+"** 按钮
   - 方法二：点击顶部菜单 **"File"** → **"New"** → **"Data Source"** → **"MySQL"**
   - 方法三：在左侧边栏右键点击空白处 → **"New"** → **"Data Source"** → **"MySQL"**

3. **填写连接信息**
   - 在弹出的窗口中，填写以下信息：
     ```
     名称（Name）: Lottery MySQL（可以自定义）
     Host: localhost
     Port: 3306
     Authentication: User & Password
     User: root
     Password: root（填写您的实际 MySQL 密码）
     ```
   
   ⚠️ **重要**：此时 **Database** 字段可以留空，或者填写 `mysql`（系统数据库）

4. **测试连接**
   - 点击窗口下方的 **"Test Connection"** 按钮
   - 如果是第一次连接，DataGrip 会提示下载 MySQL 驱动
   - 点击 **"Download"** 下载驱动
   - 下载完成后，再次点击 **"Test Connection"**
   - 如果看到绿色的 **"Successful"**，说明连接成功

5. **保存连接**
   - 点击 **"OK"** 或 **"Apply"** 保存连接

---

### 步骤 2: 打开 SQL 脚本文件

**方法一：直接在 DataGrip 中打开文件**

1. 在 DataGrip 中，点击顶部菜单 **"File"** → **"Open"**，或者按 `Ctrl+O`（Windows）/ `Cmd+O`（Mac）
2. 导航到项目目录：`d:\projects\lottery_engine\`
3. 选择文件：`setup-complete.sql`
4. 点击 **"Open"**

**方法二：使用外部编辑器打开，然后复制**

1. 在 Windows 资源管理器中打开文件：`d:\projects\lottery_engine\setup-complete.sql`
2. 全选内容（`Ctrl+A`），复制（`Ctrl+C`）
3. 在 DataGrip 中打开查询控制台（见步骤 3）

---

### 步骤 3: 打开查询控制台

**方法一：在数据源连接上打开**

1. 在左侧边栏找到刚创建的 MySQL 连接
2. 右键点击连接名称（如 "Lottery MySQL"）
3. 选择 **"New"** → **"Query Console"**，或者直接点击连接名称前的 **">"** 图标

**方法二：使用快捷键**

1. 确保选中了 MySQL 数据源连接
2. 按 `Ctrl+Alt+L`（Windows）/ `Cmd+Option+L`（Mac）

---

### 步骤 4: 执行 SQL 脚本

#### 方式 A：如果脚本文件已经在 DataGrip 中打开

1. 在编辑器窗口中打开 `setup-complete.sql` 文件
2. 确保该文件已关联到正确的数据源：
   - 查看文件顶部右侧的数据源下拉菜单
   - 如果显示 "Unassigned"，点击下拉菜单，选择您的 MySQL 连接（如 "Lottery MySQL"）
3. 全选所有内容：按 `Ctrl+A`（Windows）/ `Cmd+A`（Mac）
4. 执行脚本：
   - 点击编辑器右上角的绿色执行按钮（▶️）
   - 或者按 `Ctrl+Enter`（Windows）/ `Cmd+Enter`（Mac）
   - 或者右键点击代码 → **"Execute"**

#### 方式 B：在查询控制台中执行

1. 在查询控制台中，粘贴脚本内容（如果之前复制了）
2. 全选内容：按 `Ctrl+A`
3. 执行：按 `Ctrl+Enter` 或点击执行按钮

---

### 步骤 5: 查看执行结果

执行后，您会在底部看到：

1. **结果面板（Results）**
   - 会显示脚本执行的结果
   - 最后的验证查询会显示：
     - Tables created: 4
     - Activities: 2
     - Strategies: 2
     - Strategy Details: 11
     - Awards: 10

2. **消息面板（Messages）**
   - 显示执行过程中的消息
   - 如果有错误，会在这里显示红色错误信息

---

### 步骤 6: 刷新并查看数据库

1. **刷新数据源连接**
   - 在左侧边栏，找到您的 MySQL 连接
   - 右键点击连接名称
   - 选择 **"Refresh"**（或按 `F5`）

2. **查看创建的数据库**
   - 展开连接（点击连接名称前的 ▶️ 或 >）
   - 展开 **"Databases"**
   - 您应该能看到 **"lottery_db"** 数据库（之前可能没有，现在已经创建）

3. **查看表结构**
   - 展开 **"lottery_db"** 数据库
   - 展开 **"Tables"**
   - 您应该能看到 4 张表：
     - `activity`（活动表）
     - `award`（奖品表）
     - `strategy`（策略表）
     - `strategy_detail`（策略明细表）

4. **查看表数据**
   - 右键点击任意表（如 `activity`）
   - 选择 **"Open Table"** 或 **"Jump to Data"**
   - 可以看到表中的数据

---

## ✅ 验证数据库是否正确创建

在查询控制台中执行以下 SQL 验证：

```sql
-- 切换到 lottery_db 数据库
USE lottery_db;

-- 查看所有表
SHOW TABLES;

-- 查看活动数据
SELECT * FROM activity;

-- 查看策略数据
SELECT * FROM strategy;

-- 查看奖品数据
SELECT * FROM award;

-- 查看策略明细数据
SELECT * FROM strategy_detail;
```

---

## ❓ 常见问题

### Q1: 提示 "Unknown database 'lottery_db'"

**原因**：脚本执行失败，数据库未创建

**解决**：
1. 检查 MySQL 服务是否运行
2. 检查连接的用户是否有创建数据库的权限
3. 重新执行整个脚本

### Q2: 提示 "Table already exists"

**原因**：表已经存在（可能之前执行过部分脚本）

**解决**：
- 这是正常的，脚本使用了 `IF NOT EXISTS`，不会报错
- 如果想重新创建，先删除数据库：
  ```sql
  DROP DATABASE IF EXISTS lottery_db;
  ```
  然后重新执行脚本

### Q3: 找不到数据源下拉菜单

**解决**：
1. 确保文件已在 DataGrip 中打开
2. 查看文件标签页顶部，应该有数据源选择器
3. 如果没有，在查询控制台中执行脚本

### Q4: 脚本执行到一半就停止了

**解决**：
1. 检查是否有语法错误（查看 Messages 面板）
2. 确保脚本完整（应该有 160+ 行）
3. 确保所有语句都以分号结尾

---

## 🎯 快速检查清单

执行完成后，确认以下项目：

- [ ] MySQL 连接成功（绿色对勾）
- [ ] 脚本执行完成（没有红色错误）
- [ ] `lottery_db` 数据库已创建
- [ ] 4 张表都已创建（activity, strategy, strategy_detail, award）
- [ ] 可以查看表数据（activity 表有 2 条记录）
- [ ] 在项目中可以正常连接数据库

---

## 📸 关键界面位置说明

### DataGrip 界面布局：

```
┌─────────────────────────────────────┐
│  File  Edit  View  Navigate  ...    │ ← 顶部菜单栏
├─────────────────────────────────────┤
│  [+] 按钮  →  创建数据源连接         │ ← 工具栏
├─────────┬───────────────────────────┤
│         │                           │
│  左侧   │      编辑器区域           │
│  连接   │      (SQL 文件)           │
│  列表   │                           │
│         │                           │
├─────────┴───────────────────────────┤
│  结果面板 / 消息面板                 │ ← 底部面板
└─────────────────────────────────────┘
```

### 关键按钮位置：

- **"+"** 按钮：左上角，创建数据源
- **执行按钮（▶️）**：编辑器右上角，或按 `Ctrl+Enter`
- **刷新按钮**：右键连接 → Refresh

---

完成以上步骤后，您的数据库就已经搭建好了！🎉


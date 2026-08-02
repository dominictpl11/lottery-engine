# Maven安装说明

## Windows安装Maven

### 方式一：使用Chocolatey（推荐）

```powershell
# 以管理员身份运行PowerShell
choco install maven
```

### 方式二：手动安装

1. **下载Maven**
   - 访问：https://maven.apache.org/download.cgi
   - 下载 `apache-maven-3.9.x-bin.zip`

2. **解压到目录**
   - 例如：`C:\Program Files\Apache\maven`

3. **配置环境变量**
   - 添加 `MAVEN_HOME` = `C:\Program Files\Apache\maven`
   - 在 `PATH` 中添加 `%MAVEN_HOME%\bin`

4. **验证安装**
   ```bash
   mvn -version
   ```

### 方式三：使用IDE内置Maven

- **IntelliJ IDEA**: 自带Maven，可以直接使用
- **Eclipse**: 可以配置使用内置Maven

---

## 安装后运行项目

```bash
cd d:\projects\lottery_engine
mvn spring-boot:run
```


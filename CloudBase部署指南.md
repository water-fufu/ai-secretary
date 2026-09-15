# 秘书 2.0 CloudBase 部署指南

## 前置准备

- [x] CloudBase 环境已创建（环境 ID: fokaloz-d3gluy2nf3a669ec4）
- [x] PostgreSQL 数据库已创建并运行（共享集群，版本 17.11）
- [x] 云托管服务已启用
- [x] 代码包已打包：`C:\AI\秘书\秘书2.0\mishu-server.zip`（41 KB）
- [x] DeepSeek API Key（需要你提供）

## 部署步骤（在你自己的浏览器中操作）

### 第 1 步：进入云托管

1. 打开 https://console.cloud.tencent.com/tcb
2. 选择环境 `fokaloz`
3. 左侧菜单 → 云函数/托管 → 服务管理
4. 找到「更多部署方式」→ 点击「使用本地代码上传部署」

### 第 2 步：填写基础配置

| 配置项 | 值 |
|--------|-----|
| 代码包类型 | 压缩包 |
| 代码包 | 点击「上传」→ 选择 `C:\AI\秘书\秘书2.0\mishu-server.zip` |
| 服务名称 | `mishu-api` |
| 访问端口 | `80`（保持默认） |
| 服务端口 | `8080`（必须改，FastAPI 监听 8080） |

### 第 3 步：配置环境变量

展开「环境变量设置」，添加以下变量：

| Key | Value | 说明 |
|-----|-------|------|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key | 必填，用于 LLM 调用 |
| `FAISS_INDEX_PATH` | `/app/data/faiss` | 可选，默认就是这个值 |

**不需要手动配置数据库连接串！** 代码已适配 CloudBase 自动注入的环境变量：
- `PGHOST` / `PGPORT` / `PGDATABASE` / `PGUSER` / `PGPASSWORD`
- 应用启动时会自动拼接成 `postgresql+asyncpg://...` 连接串

**Redis 暂未接入**，不需要配置，不影响核心功能。

### 第 4 步：部署

1. 点击底部「部署」按钮
2. 等待构建和部署完成（通常 2-5 分钟）
3. 部署成功后，在服务列表中找到 `mishu-api`
4. 点击服务名称 → 查看「公网访问地址」（类似 `https://mishu-api-xxx.tcloudbaseapp.com`）

### 第 5 步：配置客户端

1. 双击运行 `秘书-Setup-2.0.0.exe` 安装客户端（如已安装则直接打开）
2. 左侧菜单 → 设置
3. API 地址填入上一步的公网访问地址（注意不要加末尾的 `/`）
4. 点击「测试连接」→ 显示"连接成功"即配置正确
5. 点击「保存配置」

### 第 6 步：验证

1. 回到聊天页，发送一条消息（如"你好"）
2. 如果返回"天书库中暂无相关资料"，说明 RAG 链路正常
3. 切换到「写入天书」模式，输入"记下来：测试一条记录"，确认写入
4. 切换到「知识库」页，确认笔记已创建

## 常见问题

### Q: 部署失败怎么办？
A: 在服务管理页点击服务名称 → 版本管理 → 查看构建日志，把错误信息发我。

### Q: 客户端测试连接失败？
A: 检查 API 地址是否正确（不要加 `/api/v1`，只要域名），确认服务状态是"运行中"。

### Q: 数据库连不上？
A: 确认 PostgreSQL 实例状态是"运行中"。代码会自动读取 CloudBase 注入的 `PG*` 环境变量，不需要手动配置连接串。如果仍失败，在环境变量里手动添加 `DATABASE_URL=postgresql+asyncpg://用户:密码@主机:5432/数据库名`。

### Q: 怎么导入 1.0 的数据？
A: 部署完成后，在本地运行：
```bash
cd C:\AI\秘书\秘书2.0\server
set DATABASE_URL=postgresql+asyncpg://用户:密码@主机:5432/数据库名
python -m app.migrate_from_v1 --vault-path "C:\AI\秘书\tian_shu_vault"
```

## 文件清单

| 文件 | 路径 |
|------|------|
| 代码包 | `C:\AI\秘书\秘书2.0\mishu-server.zip` |
| 客户端安装包 | `C:\AI\秘书\秘书2.0\client\release\秘书-Setup-2.0.0.exe` |
| 后端源码 | `C:\AI\秘书\秘书2.0\server\` |
| 客户端源码 | `C:\AI\秘书\秘书2.0\client\` |
| 执行方案 | `C:\AI\秘书\秘书2.0\执行方案.md` |
| 本部署指南 | `C:\AI\秘书\秘书2.0\CloudBase部署指南.md` |

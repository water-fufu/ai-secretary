# 秘书 2.0

个人知识库 AI Agent —— Electron 桌面客户端 + CloudBase 云端后端。

从 1.0 单文件 Gradio 应用演进为分层架构的正式产品，支持 RAG 问答、计划生成、Claude 指令解析、天书写入四条业务链路，SSE 流式输出。

## 架构

```
Electron 桌面客户端（本地安装包，不含 Python）
    ↓ HTTPS + SSE 流式
CloudBase 云托管（FastAPI + PostgreSQL/SQLite + Redis + FAISS）
```

- **客户端**：Electron + React 18 + TypeScript + Vite + Tailwind CSS + Zustand
- **后端**：FastAPI + Uvicorn + SQLAlchemy 2.0（异步） + Pydantic v2
- **数据库**：PostgreSQL（生产）/ SQLite（开发），Alembic 迁移
- **缓存**：Redis（精确缓存 + 语义缓存两层）
- **RAG**：LangChain + FAISS（向量检索） + fastembed（ONNX 向量化，无 torch 依赖）
- **LLM**：DeepSeek API（langchain-deepseek）
- **部署**：Docker（python:3.12-slim）+ 腾讯云 CloudBase 云托管

## 目录结构

```
秘书2.0/
├── client/                  # Electron 桌面客户端
│   ├── electron/            # 主进程：托盘/快捷键/通知/窗口管理/IPC
│   ├── src/                 # React 渲染进程
│   │   ├── api/             # API 客户端 + SSE 处理
│   │   ├── components/      # UI 组件
│   │   ├── store/           # Zustand 状态管理
│   │   └── types/           # TypeScript 类型定义
│   ├── electron-builder.yml
│   └── package.json
├── server/                  # FastAPI 云端后端
│   ├── app/
│   │   ├── api/             # API 路由（chat/notes/vault/health）
│   │   ├── services/        # 业务逻辑（chat_service/note_service/write_service）
│   │   ├── rag/             # RAG 五层：prompts/splitter/embeddings/vector_store/retriever
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── core/            # 基础设施（logging/exceptions/llm/cache）
│   │   ├── tests/           # pytest 单元测试
│   │   ├── config.py        # 配置管理（支持 PG* 环境变量自动拼接）
│   │   ├── database.py      # 异步引擎 + Session
│   │   ├── main.py          # FastAPI 入口 + lifespan
│   │   └── migrate_from_v1.py  # 1.0 数据迁移 CLI
│   ├── alembic/             # 数据库迁移
│   ├── Dockerfile           # CloudBase 部署
│   └── requirements.txt
├── docker-compose.yml       # 本地开发（PostgreSQL + Redis + Backend）
├── CloudBase部署指南.md      # 详细部署步骤
├── 执行方案.md               # 6 阶段执行方案
└── README.md
```

## 快速开始

### 客户端开发

```bash
cd client
npm install
npm run dev        # 开发模式（Vite + Electron）
npm run build      # 构建并打包 exe 安装包
```

安装包输出：`client/release/秘书-Setup-2.0.0.exe`（约 77MB）

### 后端本地开发

```bash
cd server
pip install -r requirements.txt

# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 启动后端
uvicorn app.main:app --reload --port 8080
```

API 文档：http://localhost:8080/docs

### 数据迁移（从 1.0 导入）

```bash
cd server
python -m app.migrate_from_v1 --vault-path "C:\AI\秘书\tian_shu_vault"
```

## 桌面客户端特性

- 无边框窗口，自定义标题栏
- 系统托盘，关闭最小化到托盘（不退出）
- 全局快捷键 `Ctrl+Alt+M` 唤起/隐藏
- 桌面通知
- SSE 流式输出，逐字显示
- 知识库管理（天书库）
- API 地址在设置页可配置，默认留空
- 薄荷绿主题

## API 接口

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/chat` | 通用聊天（SSE） |
| POST | `/api/v1/chat/qa` | 知识库问答（SSE） |
| POST | `/api/v1/chat/plan` | 生成工作计划（SSE） |
| POST | `/api/v1/chat/claude` | 生成 Claude 指令（SSE） |
| POST | `/api/v1/chat/write/preview` | 写入预览 |
| POST | `/api/v1/chat/write/confirm` | 确认写入天书 |
| GET | `/api/v1/notes` | 笔记列表 |
| GET | `/api/v1/notes/{id}` | 笔记详情 |
| POST | `/api/v1/notes` | 创建笔记 |
| PUT | `/api/v1/notes/{id}` | 更新笔记 |
| DELETE | `/api/v1/notes/{id}` | 删除笔记 |
| GET | `/api/v1/vault/overview` | 知识库概览 |
| POST | `/api/v1/vault/refresh` | 重建 FAISS 索引 |

## 技术亮点

1. **RAG 检索增强生成**：Markdown 标题感知切片 + FAISS 向量检索 + 冲突检测
2. **SSE 流式输出**：FastAPI StreamingResponse + React ReadableStream，逐字渲染
3. **两层缓存设计**：精确缓存（SHA-256）+ 语义缓存（向量相似度阈值 0.9）
4. **FAISS 持久化**：索引保存到磁盘，启动加载而非全量重建
5. **模块化分层架构**：API / Service / RAG / Model 四层分离，职责清晰
6. **Electron 安全**：contextIsolation + contextBridge，禁用 nodeIntegration
7. **fastembed 向量化**：ONNX 运行时，不依赖 torch，Docker 镜像从 3GB+ 降至 1.2GB
8. **数据库容错启动**：init_db 移至后台任务，连接失败不阻塞服务启动

## CloudBase 部署

### 环境要求

- CloudBase 环境（已开通云托管）
- DeepSeek API Key
- 数据库：PostgreSQL（推荐外部实例如 Supabase/Neon）或 SQLite + 存储卷

### 部署步骤

详见 [CloudBase部署指南.md](./CloudBase部署指南.md)。

核心配置：
- 服务端口：`8080`
- 环境变量：`DEEPSEEK_API_KEY`、`DATABASE_URL`（或 `PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD`）
- 存储挂载：`/app/data`（FAISS 索引 + SQLite 持久化）

### 已知限制

- CloudBase 共享集群（体验版）PostgreSQL 无内网地址，无法从云托管直连
- 解决方案：启用存储挂载 + SQLite，或接入外部免费 PostgreSQL（Supabase / Neon）

## 开发中遇到的主要问题

| 问题 | 根因 | 解决方案 |
|------|------|----------|
| Docker 构建超时 | sentence-transformers 依赖 torch（2GB+） | 换 fastembed（ONNX，无 torch） |
| onnxruntime 安装失败 | Alpine musllinux 无预编译 wheel | 换回 python:3.12-slim（Debian/glibc） |
| 健康检查超时部署失败 | 数据库连接超时阻塞 lifespan | init_db 移到后台 + connect_timeout=5 |
| Python 3.14 依赖冲突 | langchain 与 faiss-cpu 版本互斥 | Docker 固定 Python 3.12 |
| 共享 PG 无法连接 | 体验版无内网地址 | SQLite + 存储卷 / 外部 PG |

## 阶段进度

- [x] P1: Electron 客户端脚手架 + 自定义标题栏
- [x] P2: 桌面特性（托盘/快捷键/通知/最小化到托盘）
- [x] P3: 后端脚手架（分层架构 + Docker + Alembic）
- [x] P4: RAG 核心 + 四条业务链路 + SSE 流式
- [x] P5: 客户端功能页（聊天/笔记/天书/设置）
- [x] P6: 收尾（迁移脚本/Redis缓存/单元测试/文档）
- [ ] 云端数据库配置与全链路联调
- [ ] 1.0 数据迁移到云端

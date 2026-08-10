# LLC Engineering Assistant

面向 Half-Bridge LLC 电源设计评审与故障排查的工程辅助项目。本仓库当前仅完成 **Phase 0：项目初始化与工程骨架**。

当前可用内容：

- FastAPI Backend 与 `GET /health`；
- React + TypeScript + Vite 基础首页；
- Backend pytest 配置与 health endpoint 测试；
- 为后续 Phase 保留的分层目录。

当前没有 LLC 工程计算、设计评审规则、波形分析、器件数据手册解析、故障诊断或 LLM 功能。系统不是安全认证工具，不应据此对电源设计作安全、合规或量产结论。

## 环境要求

- Python 3.12 或更高版本
- Node.js 22.12 或更高版本
- npm 10 或更高版本

可选：复制 `.env.example` 为 `.env`，并按本地端口调整其中的非敏感配置。不要提交 `.env`、API key、客户数据手册或专有波形数据。

## Backend 本地开发

在仓库根目录创建虚拟环境并安装 Backend 与测试依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

启动 Backend：

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

验证 health endpoint：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

运行 Backend 测试：

```powershell
python -m pytest
```

## Frontend 本地开发

Frontend 可以独立安装和启动：

```powershell
Set-Location frontend
npm install
npm run dev
```

Vite 默认会在终端显示本地访问地址。生产构建与 TypeScript 检查：

```powershell
npm run build
```

## 当前目录边界

```text
backend/app/        FastAPI 应用及后续 Backend 分层占位
backend/tests/      Backend 自动化测试
frontend/           React + TypeScript + Vite 应用
docs/               架构、API、安全和后续工程规范
examples/           后续示例项目与波形占位
datasets/           后续规则、故障案例和评估数据占位
scripts/            后续开发脚本占位
```

后续开发必须按照 `docs/MASTER_WORKFLOW.md` 的 Phase 顺序推进。


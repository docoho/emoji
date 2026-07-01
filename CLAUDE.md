# Emoji Showcase Platform

FastAPI + SQLModel + SQLite/Alembic 后端，Vue 3 + Vite 前端。用于分享、审核、收藏和管理 emoji。共享规则写这里；个人配置写 `CLAUDE.local.md` 或 `.claude/settings.local.json`，禁止提交。

## 技术栈

- 后端：FastAPI、SQLModel、Alembic、SQLite、Redis、PyJWT、Ruff、pytest
- 前端：Vue 3、Vue Router、Vite
- 部署：`emoji.undov.com`

## 常用命令

所有 shell 命令都必须加 `rtk` 前缀；链式命令中每段都要加。

```bash
rtk make backend              # 后端开发服务，端口 8000
rtk make frontend             # 前端开发服务，端口 5173
rtk make backend-test         # 后端测试
rtk make lint                 # Ruff 检查
rtk make backend-migrate      # 执行 Alembic 迁移
cd frontend && rtk npm run build
```

## 项目结构

- `backend/app/main.py` — FastAPI app、lifespan、CORS、安全响应头
- `backend/app/db.py` — 数据库 engine/session、Alembic 启动迁移
- `backend/app/api/endpoints/` — REST API 路由
- `backend/app/models/` — SQLModel 表定义
- `backend/alembic/versions/` — 数据库迁移文件
- `frontend/src/services/api.js` — 前端 API 入口
- `frontend/src/composables/` — Vue 共享状态 composable
- `.claude/` — Claude Code commands、rules、skills、agents

## 编码规范

- 前端 API 只使用相对路径 `/api/...`，禁止写死 localhost 或生产域名。
- 认证 token 只存 `sessionStorage`，禁止改回 `localStorage`。
- Vue composable 的共享状态保持模块级定义，禁止随意移入函数内部。
- 需要登录的后端接口使用 `get_current_user`；匿名/登录均可访问的接口使用 `get_optional_user`。
- 修改 SQLModel model 必须新增 Alembic revision，并运行迁移相关测试。
- 列表接口必须避免 N+1 查询，批量查询提交者、点赞、收藏等关联数据。
- 后端测试必须使用 `backend/tests/conftest.py` 的 `client` fixture，禁止直接创建 `TestClient(app)`。

## 注意事项

- 禁止读取、输出或提交 `.env`、`backend/.env`、`backend/app.db`、密钥、token、凭据文件。
- 禁止削弱 OAuth state 校验、JWT `token_version` 校验、CORS、CSP、HSTS、rate limit。
- 修改认证、权限、数据库迁移、部署配置前必须先说明风险。
- `backend/app.db` 是本地数据，禁止提交。
- `.claude/settings.local.json` 和 `CLAUDE.local.md` 是本地私有文件，禁止提交。

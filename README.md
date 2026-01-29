# DeepStudy

基于 ModelScope 的递归学习 Agent

## 技术栈

- **前端**: React + TypeScript + ReactFlow + Vite
- **后端**: FastAPI + Python
- **模型**: Qwen/Qwen3-32B (ModelScope OpenAI 兼容 API)
- **数据库**: Neo4j (知识图谱) + SQLite (用户数据)
- **认证**: JWT

## 项目结构

```
DeepStudy/
├── frontend/          # React 前端应用
├── backend/           # FastAPI 后端服务
│   ├── api/           # API Layer
│   ├── agent/         # Agent Layer
│   ├── data/          # Data Layer
│   └── storage/       # 数据存储目录
└── README.md          # 项目说明
```

## 快速开始

### 环境要求

- **Node.js** >= 18
- **Python** >= 3.10
- **Docker** (用于运行 Neo4j)
- **Conda** 或 **venv** (Python 环境管理)

### 1. 克隆项目

```bash
git clone <repository-url>
cd DeepStudy
```

### 2. 配置后端环境

#### 2.1 创建 Python 环境

```bash
# 使用 conda
conda create -n deepstudy python=3.10
conda activate deepstudy

# 或使用 venv
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

#### 2.2 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 2.3 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
# ModelScope API 配置
MODELSCOPE_API_KEY=your_api_key_here
MODELSCOPE_API_BASE=https://api-inference.modelscope.cn/v1

# 模型选择
MODEL_NAME=Qwen/Qwen3-32B
CODER_MODEL_NAME=Qwen/Qwen3-32B

# Neo4j 配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=deepstudy123

# JWT 配置
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# 数据库路径
SQLITE_DB_PATH=./backend/storage/deepstudy.db
VECTOR_STORE_PATH=./backend/storage/vector_store

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# 服务器配置
API_HOST=0.0.0.0
API_PORT=8000
```

**重要提示**：
- `MODELSCOPE_API_KEY`: 从 [ModelScope](https://www.modelscope.cn/) 获取
- `NEO4J_PASSWORD`: 需要与 Docker 容器中的密码一致
- `JWT_SECRET_KEY`: 建议使用随机字符串生成器生成

### 3. 启动 Neo4j 服务

使用 Docker 运行 Neo4j：

```bash
# 启动 Neo4j 容器
docker run -d \
  --name deepstudy-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/deepstudy123 \
  neo4j:5.15.0
```

**验证 Neo4j 运行**：
```bash
docker ps
```

**访问 Neo4j Browser**：http://localhost:7474
- 用户名：`neo4j`
- 密码：`deepstudy123`

**常用命令**：
```bash
# 停止容器
docker stop deepstudy-neo4j

# 启动容器
docker start deepstudy-neo4j

# 删除容器（数据会丢失）
docker rm -f deepstudy-neo4j
```

### 4. 启动后端服务

```bash
# 在项目根目录运行
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

后端将在 `http://localhost:8000` 启动。

**API 文档**：http://localhost:8000/docs

### 5. 配置前端环境

#### 5.1 安装前端依赖

```bash
cd frontend
npm install
```

#### 5.2 启动前端开发服务器

```bash
npm run dev
```

前端将在 `http://localhost:5173` 启动。

## 使用流程

1. **注册/登录**：访问前端页面，注册新用户或登录
2. **开始对话**：在聊天界面输入问题，AI 会基于 ModelScope API 回答
3. **划词追问**：选中回答中的文本片段，可以针对性地追问
4. **知识图谱**：对话记录会保存到 Neo4j，构建知识图谱（待完善）

## 开发指南

详细开发指南请参考：
- [前端开发指南](frontend/README.md)
- [后端开发指南](backend/README.md)
- [实现状态报告](backend/IMPLEMENTATION_STATUS.md)

## 开发规范

- 使用 Git 分支管理：`main` 分支保持稳定，功能开发使用 `feature/*` 分支
- 提交前确保代码可运行，测试通过后再合并到 `main`
- 遵循单一职责原则和 SOLID 原则
- 代码修改遵循 KISS 原则

## 常见问题

### 1. Docker 连接失败

**错误**：`docker: error during connect: ...`

**解决**：确保 Docker Desktop 已启动并运行。

### 2. Neo4j 连接失败

**错误**：`ConnectionRefusedError: [Errno 10061]`

**解决**：
- 检查 Neo4j 容器是否运行：`docker ps`
- 确认 `.env` 中的 `NEO4J_PASSWORD` 与容器启动时的密码一致
- 检查端口是否被占用：`netstat -ano | findstr :7687`

### 3. ModelScope API 调用失败

**错误**：`400 Bad Request` 或 `401 Unauthorized`

**解决**：
- 检查 `MODELSCOPE_API_KEY` 是否正确
- 确认 `MODELSCOPE_API_BASE` 为 `https://api-inference.modelscope.cn/v1`
- 检查网络连接

### 4. 前端无法连接后端

**解决**：
- 确认后端服务已启动（`http://localhost:8000`）
- 检查浏览器控制台的错误信息
- 确认 CORS 配置正确

## 下一步计划

- [ ] 完善意图识别（Few-shot 提示词）
- [ ] 实现知识三元组提取
- [ ] 实现文本片段提取和标记
- [ ] 完善划词追问上下文获取
- [ ] 实现知识图谱可视化
- [ ] 实现学习画像和诊断报告
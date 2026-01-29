# DeepStudy 后端开发指南

## 技术栈

- **框架**: FastAPI
- **LLM 客户端**: 自定义 ModelScope OpenAI 兼容 API 客户端
- **模型**: Qwen/Qwen3-32B (ModelScope API)
- **数据库**: Neo4j (知识图谱) + SQLite (用户数据)
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt (passlib)

## 项目结构

```
backend/
├── api/                 # API Layer
│   ├── routes/          # 路由定义
│   │   ├── auth.py      # 认证路由（注册/登录）
│   │   └── chat.py      # 聊天路由
│   ├── middleware/      # 中间件
│   │   └── auth.py      # JWT 认证中间件
│   └── schemas/         # Pydantic 模型
│       ├── request.py   # 请求模型
│       └── response.py  # 响应模型
├── agent/               # Agent Layer
│   ├── orchestrator.py  # 编排器
│   ├── intent_router.py # 意图识别
│   ├── llm_client.py    # ModelScope LLM 客户端
│   ├── prompts/         # Prompt 模板
│   └── strategies/      # 处理策略
│       ├── base_strategy.py
│       ├── concept_strategy.py
│       ├── code_strategy.py
│       └── derivation_strategy.py
├── data/                # Data Layer
│   ├── neo4j_client.py  # Neo4j 客户端
│   ├── sqlite_db.py     # SQLite 操作
│   └── vector_store.py # 向量存储（预留）
├── storage/             # 数据存储目录
│   └── deepstudy.db     # SQLite 数据库文件
├── config.py            # 配置管理
├── main.py              # 应用入口
└── requirements.txt     # Python 依赖
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

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
- `NEO4J_PASSWORD`: 需要与 Docker 容器中的密码一致（见下方）
- `JWT_SECRET_KEY`: 建议使用随机字符串生成器生成

### 3. 启动 Neo4j 服务

使用 Docker 运行 Neo4j（推荐）：

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

# 查看日志
docker logs deepstudy-neo4j

# 删除容器（数据会丢失）
docker rm -f deepstudy-neo4j
```

**数据持久化**（可选）：
```bash
docker run -d \
  --name deepstudy-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/deepstudy123 \
  -v neo4j_data:/data \
  -v neo4j_logs:/logs \
  neo4j:5.15.0
```

### 4. 初始化数据库

SQLite 数据库会在应用启动时自动创建表结构。

### 5. 启动服务

在项目根目录运行：

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

或使用 Python 直接运行：

```bash
cd backend
python main.py
```

API 文档访问：http://localhost:8000/docs

## API 协议

### 认证

#### 注册
```
POST /api/auth/register
Content-Type: application/json

Request Body:
{
  "username": "string",  // 3-50 字符
  "email": "string",     // 有效邮箱地址
  "password": "string"   // 至少 6 字符
}

Response 200:
{
  "access_token": "string",
  "token_type": "bearer",
  "user_id": "string",
  "username": "string"
}
```

#### 登录
```
POST /api/auth/login
Content-Type: application/json

Request Body:
{
  "username": "string",
  "password": "string"
}

Response 200:
{
  "access_token": "string",
  "token_type": "bearer",
  "user_id": "string",
  "username": "string"
}
```

### 聊天

#### 发送消息
```
POST /api/chat
Authorization: Bearer <token>
Content-Type: application/json

Request Body:
{
  "query": "string",              // 用户问题
  "parent_id": "string | null",   // 父对话 ID（可选）
  "ref_fragment_id": "string | null", // 划词追问的片段 ID（可选）
  "session_id": "string"          // 会话 ID
}

Response 200:
{
  "answer": "string",
  "fragments": [
    {
      "id": "string",
      "content": "string",
      "type": "text | formula | code | concept"
    }
  ],
  "knowledge_triples": [
    {
      "subject": "string",
      "relation": "string",
      "object": "string"
    }
  ],
  "suggestion": "string | null",
  "conversation_id": "string",
  "parent_id": "string | null"
}
```

#### 获取对话树
```
GET /api/chat/conversation/{conversation_id}
Authorization: Bearer <token>

Response 200:
{
  "node_id": "string",
  "parent_id": "string | null",
  "user_id": "string",
  "role": "user | assistant",
  "content": "string",
  "intent": "string | null",
  "mastery_score": 0.0,
  "timestamp": "datetime",
  "children": [...]
}
```

## 数据库结构

### SQLite 表结构

**users 表**:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `username` (TEXT UNIQUE NOT NULL)
- `email` (TEXT UNIQUE NOT NULL)
- `hashed_password` (TEXT NOT NULL)
- `created_at` (TEXT NOT NULL)

### Neo4j 节点和关系

**节点标签**：
- `DialogueNode`: 对话节点

**节点属性**：
- `node_id`: 唯一标识（UUID）
- `user_id`: 用户 ID
- `role`: 角色（"user" 或 "assistant"）
- `content`: 对话内容
- `intent`: 意图类型（"concept", "code", "derivation"）
- `mastery_score`: 掌握度评分（0-1）
- `timestamp`: 时间戳

**关系类型**：
- `HAS_CHILD`: 父子对话关系
  - 属性：`fragment_id`（可选，用于划词追问）

## 开发规范

1. **代码风格**: 使用 JSDoc 风格注释
2. **类型提示**: 所有函数使用类型注解
3. **错误处理**: 统一使用 HTTPException 和日志记录
4. **单一职责**: 每个模块只负责一个功能
5. **SOLID 原则**: 遵循面向对象设计原则

## 日志配置

应用使用 Python `logging` 模块，配置在 `main.py` 中：

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

日志级别：
- `INFO`: 正常操作信息
- `WARNING`: 警告信息（如 Neo4j 连接失败）
- `ERROR`: 错误信息（包含堆栈跟踪）

## 环境变量说明

### ModelScope API

- `MODELSCOPE_API_KEY`: **必填** - ModelScope API 密钥
- `MODELSCOPE_API_BASE`: API 基础地址（默认：`https://api-inference.modelscope.cn/v1`）
- `MODEL_NAME`: 主模型名称（默认：`Qwen/Qwen3-32B`）
- `CODER_MODEL_NAME`: 代码模型名称（默认：`Qwen/Qwen3-32B`）

### Neo4j

- `NEO4J_URI`: Neo4j 连接地址（默认：`bolt://localhost:7687`）
- `NEO4J_USER`: Neo4j 用户名（默认：`neo4j`）
- `NEO4J_PASSWORD`: **必填** - Neo4j 密码（需与 Docker 容器一致）

### JWT

- `JWT_SECRET_KEY`: **必填** - JWT 签名密钥（生产环境请使用强随机字符串）
- `JWT_ALGORITHM`: JWT 算法（默认：`HS256`）
- `JWT_EXPIRATION_HOURS`: Token 过期时间（小时，默认：`24`）

### 数据库

- `SQLITE_DB_PATH`: SQLite 数据库路径（默认：`./backend/storage/deepstudy.db`）
- `VECTOR_STORE_PATH`: 向量存储路径（默认：`./backend/storage/vector_store`）

### CORS

- `CORS_ORIGINS`: 允许的跨域来源（JSON 数组格式，默认：`["http://localhost:5173","http://localhost:3000"]`）

### 服务器

- `API_HOST`: 服务器监听地址（默认：`0.0.0.0`）
- `API_PORT`: 服务器端口（默认：`8000`）

## 注意事项

1. **不要将 `.env` 文件提交到 Git**（已在 `.gitignore` 中排除）
2. **生产环境请使用强随机字符串作为 `JWT_SECRET_KEY`**
3. **Neo4j 密码必须与 Docker 容器启动时的密码一致**
4. **ModelScope API Key 需要从官网申请**
5. **数据库目录会自动创建**（如果不存在）

## 常见问题

### 1. ModelScope API 调用失败

**错误**：`400 Bad Request: parameter.enable_thinking must be set to false`

**解决**：已在 `llm_client.py` 中设置 `extra_body={"enable_thinking": False}`，确保使用最新代码。

**错误**：`401 Unauthorized`

**解决**：
- 检查 `MODELSCOPE_API_KEY` 是否正确
- 确认 API Key 未过期
- 检查网络连接

### 2. Neo4j 连接失败

**错误**：`ConnectionRefusedError: [Errno 10061]`

**解决**：
- 检查 Neo4j 容器是否运行：`docker ps`
- 确认 `.env` 中的 `NEO4J_PASSWORD` 与容器启动时的密码一致
- 检查端口是否被占用：`netstat -ano | findstr :7687`
- 查看容器日志：`docker logs deepstudy-neo4j`

**临时方案**：如果暂时不想启动 Neo4j，可以修改 `orchestrator.py`，在 Neo4j 保存失败时只记录警告而不抛出异常（见 `IMPLEMENTATION_STATUS.md`）。

### 3. JWT Token 过期

Token 默认 24 小时过期，可在 `.env` 中配置 `JWT_EXPIRATION_HOURS`。

### 4. 数据库初始化失败

**错误**：`sqlite3.OperationalError: unable to open database file`

**解决**：
- 检查 `SQLITE_DB_PATH` 配置的目录是否存在
- 确认应用有写入权限
- 数据库目录会自动创建，但父目录必须存在

### 5. 导入错误

**错误**：`ImportError: cannot import name 'XXX' from 'backend.xxx'`

**解决**：
- 确保在项目根目录运行命令（不是 `backend/` 目录）
- 检查 Python 路径：`PYTHONPATH` 应包含项目根目录
- 确认所有依赖已安装：`pip install -r requirements.txt`

## 实现状态

当前实现状态和已知限制请参考：[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)

## 下一步计划

- [ ] 完善意图识别（Few-shot 提示词）
- [ ] 实现知识三元组提取
- [ ] 实现文本片段提取和标记
- [ ] 完善划词追问上下文获取
- [ ] 实现知识图谱可视化
- [ ] 实现学习画像和诊断报告

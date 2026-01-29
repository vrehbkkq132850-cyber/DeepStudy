# 实现状态报告

本文档记录 DeepStudy 项目的当前实现状态、缺省实现、预留接口和已知限制。

## 当前实现状态

### 已完成功能

1. **用户认证系统**
   - 用户注册（用户名、邮箱、密码）
   - 用户登录（JWT Token）
   - 密码哈希存储（bcrypt）
   - 邮箱唯一性验证

2. **数据存储架构**
   - SQLite：仅存储用户数据（users 表）
   - Neo4j：存储对话记录和知识图谱
   - 对话树结构：使用 DialogueNode 节点和 HAS_CHILD 关系

3. **Agent 编排框架**
   - IntentRouter：意图识别框架（当前缺省实现）
   - 策略模式：ConceptStrategy、CodeStrategy、DerivationStrategy
   - Orchestrator：协调意图识别、策略选择和响应生成
   - Neo4j 集成：自动保存对话节点和关系

4. **API 路由**
   - `/api/auth/register`：用户注册
   - `/api/auth/login`：用户登录
   - `/api/chat`：发送聊天消息（支持普通提问和划词追问）
   - `/api/chat/conversation/{conversation_id}`：获取对话树

5. **前端界面**
   - 登录/注册页面（卡片式布局，背景图片）
   - 聊天界面（消息展示、输入框、侧边栏）
   - 知识图谱可视化（ReactFlow，待完善）

## 缺省实现（简化实现）

### 1. 意图识别

**位置**：`backend/agent/intent_router.py`

**当前实现**：
- 总是返回 `IntentType.CONCEPT`，不进行实际的 LLM 调用
- 保留代码结构，便于后续完善

**预留接口**：
```python
async def route(self, query: str) -> IntentType:
    # TODO: 实现真正的 Few-shot 意图识别
    # 使用 LLM 分析用户问题，返回 derivation/code/concept
```

### 2. 知识三元组提取

**位置**：`backend/agent/orchestrator.py`

**当前实现**：
- 返回空数组 `[]`
- 不进行任何提取逻辑

**预留接口**：
```python
# TODO: 提取知识三元组
# 从 LLM 回答中提取结构化知识，格式：
# [{"subject": "...", "relation": "...", "object": "..."}]
```

### 3. 文本片段提取

**位置**：`backend/agent/orchestrator.py`

**当前实现**：
- 返回空数组 `[]`
- 不进行任何片段识别和标记

**预留接口**：
```python
# TODO: 提取文本片段
# 识别代码、公式、概念等片段，生成 ContentFragment 列表
# 格式：[{"id": "frag_xxx", "type": "code", "content": "..."}]
```

### 4. 划词追问上下文获取

**位置**：`backend/agent/orchestrator.py` 的 `process_recursive_query()`

**当前实现**：
- 使用简单的递归提示词
- 不获取父对话上下文
- 不获取片段内容

**预留接口**：
```python
async def process_recursive_query(...):
    # TODO: 获取父对话上下文
    # 从 Neo4j 查询父对话的完整上下文路径
    # TODO: 获取片段内容
    # 根据 fragment_id 获取对应的文本片段内容
```

### 5. 知识图谱生成

**位置**：`backend/agent/orchestrator.py`

**当前实现**：
- 不生成知识图谱数据
- 不将知识三元组存储到 Neo4j

**预留接口**：
```python
# TODO: 生成思维导图数据
# 将知识三元组转换为 MindMapGraph 格式
# 存储知识三元组到 Neo4j 作为 KnowledgeNode
```

### 6. 学习画像计算

**位置**：未实现

**预留接口**：
- 基于对话树结构计算掌握度（mastery_score）
- 生成学习诊断报告
- 识别知识薄弱点

## 预留接口列表

### Data Layer

#### Neo4j 客户端（`backend/data/neo4j_client.py`）

1. **`get_dialogue_context_path()`**（待实现）
   - 功能：获取从根节点到指定节点的完整路径
   - 用途：划词追问时获取上下文
   - 参数：`root_node_id: str, target_node_id: str`
   - 返回：节点路径列表

2. **`save_knowledge_triple()`**（待实现）
   - 功能：保存知识三元组到 Neo4j
   - 用途：构建知识图谱
   - 参数：`subject: str, relation: str, object: str, user_id: str`
   - 返回：None

3. **`get_knowledge_graph()`**（待实现）
   - 功能：获取用户的知识图谱
   - 用途：可视化知识结构
   - 参数：`user_id: str, topic: Optional[str] = None`
   - 返回：知识图谱数据

### Agent Layer

#### IntentRouter（`backend/agent/intent_router.py`）

1. **`route()`**（缺省实现）
   - 当前：总是返回 CONCEPT
   - 后续：实现真正的 Few-shot 意图识别

#### Orchestrator（`backend/agent/orchestrator.py`）

1. **`process_recursive_query()`**（部分实现）
   - 当前：简单递归提示词
   - 后续：获取父对话上下文和片段内容

2. **知识三元组提取逻辑**（待实现）
   - 从 LLM 回答中提取结构化知识

3. **文本片段提取逻辑**（待实现）
   - 识别和标记代码、公式、概念等片段

4. **思维导图生成逻辑**（待实现）
   - 将知识三元组转换为 MindMapGraph

### API Layer

#### Chat 路由（`backend/api/routes/chat.py`）

1. **`/api/chat/mindmap`**（待实现）
   - 功能：获取知识图谱数据
   - 用途：前端可视化

2. **`/api/chat/diagnosis`**（待实现）
   - 功能：获取学习诊断报告
   - 用途：学习画像展示

## 已知限制

### 1. Llama-index 导入问题

**问题**：
- `llama-index` 版本兼容性问题导致 `ChatMessage` 导入失败
- 当前 `chat` 和 `mindmap` 路由被注释，避免导入错误

**影响**：
- 无法使用完整的 LlamaIndex 功能
- 需要修复版本兼容性或改用直接 API 调用

**解决方案**：
- 选项 1：修复 `llama-index` 版本兼容性
- 选项 2：创建简单的 LLM 包装类，直接调用 ModelScope API

### 2. 意图识别缺省实现

**问题**：
- 所有问题都被识别为 CONCEPT 类型
- 无法根据问题类型选择不同的处理策略

**影响**：
- 代码型和推导型问题可能无法得到最佳回答
- 无法充分利用 CodeStrategy 和 DerivationStrategy

**解决方案**：
- 实现真正的 Few-shot 意图识别
- 或使用规则匹配作为临时方案

### 3. 知识三元组和片段提取缺失

**问题**：
- 无法从 LLM 回答中提取结构化知识
- 无法识别和标记文本片段

**影响**：
- 知识图谱无法构建
- 划词追问功能受限
- 学习画像无法生成

**解决方案**：
- 使用 LLM 进行后处理提取
- 或使用专门的 NER/关系抽取模型

### 4. 对话树查询性能

**问题**：
- `get_dialogue_tree()` 使用递归查询，深度较大时可能性能较差

**影响**：
- 对话树较深时查询可能较慢

**解决方案**：
- 添加深度限制
- 使用分页查询
- 缓存常用查询

### 5. 错误处理

**问题**：
- Neo4j 连接失败时整个请求失败（严格模式）
- 没有降级方案

**影响**：
- Neo4j 不可用时系统完全不可用

**解决方案**：
- 考虑添加降级方案（如临时存储到 SQLite）
- 或改进错误提示，引导用户重试

## 后续扩展计划

### 短期（Demo 完善）

1. **修复 Llama-index 导入问题**
   - 解决版本兼容性
   - 恢复 `chat` 和 `mindmap` 路由

2. **实现基础的知识三元组提取**
   - 使用 LLM 后处理提取
   - 存储到 Neo4j

3. **实现基础的文本片段提取**
   - 识别代码块、公式、概念
   - 生成片段 ID

### 中期（功能完善）

1. **完善意图识别**
   - 实现真正的 Few-shot 意图识别
   - 提高识别准确率

2. **完善划词追问**
   - 从 Neo4j 获取父对话上下文
   - 获取片段内容并注入提示词

3. **实现知识图谱生成**
   - 将知识三元组存储到 Neo4j
   - 生成可视化数据

### 长期（高级功能）

1. **实现学习画像**
   - 基于对话树计算掌握度
   - 生成诊断报告
   - 识别知识薄弱点

2. **实现向量检索**
   - 使用向量数据库存储对话内容
   - 支持语义搜索和相似问题推荐

3. **实现多模态支持**
   - 支持图片、公式识别
   - 支持代码执行和可视化

## 技术债务

1. **代码重复**
   - 三个策略类有相似的实现
   - 可以考虑提取公共逻辑

2. **错误处理不统一**
   - 不同层的错误处理方式不一致
   - 需要统一错误响应格式

3. **测试覆盖**
   - 当前没有单元测试
   - 需要添加测试用例

4. **文档完善**
   - API 文档需要补充
   - 需要添加使用示例

## 总结

当前实现已经完成了基础的问答功能框架，包括用户认证、对话存储（Neo4j）、Agent 编排和 API 路由。主要功能可以运行，但许多高级功能（知识提取、学习画像等）仍处于缺省实现状态。

后续开发应优先解决 Llama-index 导入问题，然后逐步完善知识提取、意图识别等核心功能，最终实现完整的学习诊断系统。

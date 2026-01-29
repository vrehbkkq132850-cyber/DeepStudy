# DeepStudy 前端开发指南

## 技术栈

- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **路由**: React Router v6
- **HTTP 客户端**: Axios
- **图表**: ReactFlow
- **Markdown 渲染**: react-markdown + KaTeX

## 项目结构

```
frontend/
├── src/
│   ├── components/      # UI 组件
│   │   ├── Auth/        # 登录/注册
│   │   ├── Chat/        # 聊天界面
│   │   ├── MindMap/     # 思维导图
│   │   └── Markdown/     # Markdown 渲染
│   ├── services/        # API 服务
│   ├── hooks/           # React Hooks
│   ├── types/           # TypeScript 类型
│   └── utils/           # 工具函数
├── public/              # 静态资源
│   └── bg.jpg          # 背景图片
├── package.json
└── vite.config.ts
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:5173` 启动。

### 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 预览生产构建

```bash
npm run preview
```

## 核心组件说明

### 1. App.tsx

主应用组件，处理路由和认证状态：
- 路由配置：`/login`, `/register`, `/` (聊天界面)
- 认证状态检查：基于 `localStorage` 中的 `access_token`
- 自动重定向：未认证用户跳转到登录页

### 2. ChatInterface

主聊天界面组件，包含：
- **消息列表展示**：用户消息和 AI 回答
- **输入框和发送功能**：支持 Enter 发送，Shift+Enter 换行
- **思维导图侧边栏**：可折叠的知识图谱展示
- **划词选择监听**：选中文本片段触发追问
- **自动滚动**：新消息自动滚动到底部
- **加载状态**：显示 AI 思考中的加载动画

### 3. TextFragment

Markdown 文本片段组件，功能：
- **渲染 Markdown**：支持标题、列表、代码块等
- **数学公式渲染**：使用 KaTeX 渲染 LaTeX 公式
- **代码高亮**：代码块语法高亮
- **唯一 ID 注入**：为代码块和公式注入 `frag_xxx` ID
- **文本选择监听**：监听用户选中文本，触发 `onFragmentSelect` 回调

### 4. KnowledgeGraph

知识图谱组件，使用 ReactFlow：
- **接收后端数据**：接收 `nodes` 和 `edges` 数据
- **可视化展示**：使用 ReactFlow 渲染图谱
- **节点交互**：支持节点点击、拖拽等交互
- **掌握度显示**：节点颜色反映掌握度评分

### 5. API 服务

`src/services/api.ts` 封装了所有 API 调用：
- **自动添加 JWT token**：从 `localStorage` 读取并添加到请求头
- **Token 过期处理**：401 错误时清除 token 并跳转登录
- **统一错误处理**：捕获并格式化错误信息
- **类型安全**：所有 API 调用使用 TypeScript 类型定义

**主要 API 方法**：
- `register(username, email, password)`: 用户注册
- `login(username, password)`: 用户登录
- `sendMessage(query, parentId?, refFragmentId?, sessionId)`: 发送聊天消息
- `getConversation(conversationId)`: 获取对话树

## 环境变量

创建 `.env.local` 文件（可选，开发环境通常不需要）：

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

**注意**：Vite 使用 `VITE_` 前缀的环境变量，且需要在代码中通过 `import.meta.env.VITE_API_BASE_URL` 访问。

## 开发规范

1. **代码风格**: 使用 ESLint + Prettier
2. **类型安全**: 所有 API 调用使用 TypeScript 类型
3. **组件复用**: 遵循单一职责原则
4. **错误处理**: 统一使用 try-catch 和错误提示
5. **样式管理**: 使用内联样式（当前实现）或 CSS Modules

## 样式说明

### 背景图片

- 背景图片位于 `public/bg.jpg`
- 全局背景通过 `App.css` 中的 `.app-background` 类应用
- 使用高斯模糊效果（`filter: blur(10px)`）
- 前景内容通过 `.app-content` 类确保清晰显示

### 组件样式

当前实现使用内联样式，主要特点：
- **卡片式布局**：登录/注册页面使用卡片容器
- **统一配色**：使用一致的色彩方案
- **响应式设计**：适配不同屏幕尺寸
- **加载动画**：使用 CSS 动画实现加载效果

## 常见问题

### 1. 跨域问题

开发环境下，Vite 已配置代理（如需要），将 `/api` 请求转发到后端 `http://localhost:8000`。

如果遇到跨域问题：
- 检查后端 CORS 配置
- 确认后端服务已启动
- 检查浏览器控制台的错误信息

### 2. Token 管理

- Token 存储在 `localStorage` 中，键名为 `access_token`
- Token 过期后（401 错误），自动清除并跳转到登录页
- 登录成功后，Token 自动保存到 `localStorage`

### 3. ReactFlow 样式

确保在组件中导入 ReactFlow 样式：

```typescript
import 'reactflow/dist/style.css';
```

### 4. 热重载不工作

- 检查 Vite 开发服务器是否正常运行
- 确认文件保存后触发了重新编译
- 尝试重启开发服务器

### 5. 构建失败

- 检查 TypeScript 类型错误：`npm run build` 会先运行 `tsc`
- 检查 ESLint 错误：`npm run lint`
- 确认所有依赖已正确安装：`npm install`

## 调试技巧

1. **React DevTools**：安装浏览器扩展，查看组件状态
2. **Network 面板**：检查 API 请求和响应
3. **Console 面板**：查看错误日志和调试信息
4. **Vite HMR**：利用热模块替换快速查看修改效果

## 下一步优化

- [ ] 添加错误边界（Error Boundary）
- [ ] 实现消息分页加载
- [ ] 优化大文本渲染性能
- [ ] 添加消息编辑和删除功能
- [ ] 实现会话管理（多会话切换）

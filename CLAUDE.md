# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作时提供指导。

## 常用开发命令

### 前端 (基于NextChat的Web界面)
```bash
# 进入前端目录
cd src/frontend

# 开发相关
yarn install
yarn dev                    # 启动开发服务器 (localhost:3000)
yarn build                  # 生产构建
yarn start                  # 启动生产服务器
yarn lint                   # 运行ESLint检查
yarn test                   # 运行Jest测试
yarn test:ci                # 运行CI模式测试

# Tauri桌面应用
yarn app:dev                # 启动Tauri开发
yarn app:build              # 构建桌面应用

# 面具和提示词
yarn mask                   # 构建聊天面具
yarn prompts                # 获取最新提示词
```

### 后端 (FastAPI Python服务)
```bash
# 进入后端目录
cd src/backend

# 开发相关
pip install -r requirements.txt
python app.py               # 启动主后端服务器 (localhost:8001)

# 测试相关
pytest                      # 运行测试
pytest -v                   # 详细测试输出
```

### RAG系统 (检索增强生成)
```bash
# 进入RAG系统目录
cd src/services/rag_system

# 开发相关
pip install -r requirements.txt
python app.py               # 启动RAG服务 (localhost:8000)

# 测试相关
python performance_test.py  # 运行性能测试
```

## 项目架构

### 高层系统结构
这是一个北京科技大学AI教务助手系统，采用7层混合云架构：

1. **前端层**: 基于Next.js的Web界面 (ChatGPT-Next-Web分支) 与OpenAI兼容API集成
2. **后端API层**: 基于FastAPI的Web后端，包含认证、聊天路由和代理服务
3. **RAG系统层**: 使用Qdrant和BCE嵌入模型的文档检索和向量搜索
4. **模型推理层**: 针对USTB定制的LoRA微调Qwen2.5-7B模型
5. **数据层**: 4,621份USTB教务文档及其向量嵌入
6. **混合API层**: 连接本地和远程模型服务的集成服务
7. **基础设施层**: AutoDL云服务与SSH隧道进行模型服务

### 核心组件

#### 前端 (`src/frontend/`)
- **基础**: ChatGPT-Next-Web分支，包含USTB定制化
- **技术栈**: Next.js, React, TypeScript, SCSS
- **功能**: 多模型聊天界面、实时通信、工件支持、MCP集成
- **配置**: 支持多个AI提供商 (OpenAI, Anthropic, Google等)

#### 后端 (`src/backend/`)
- **主应用**: `app.py` - 包含CORS、认证和健康监控的FastAPI应用
- **路由**: 聊天、分类、反馈和OpenAI兼容的模块化路由
- **数据库**: 带连接池的MySQL，Redis缓存
- **服务**: RAG系统集成的代理服务

#### RAG系统 (`src/services/rag_system/`)
- **核心**: `app.py` - 用于文档检索的FastAPI服务
- **向量存储**: Qdrant集成进行相似度搜索
- **嵌入**: BCE (双向对比编码) 模型用于中文文本
- **功能**: 查询扩展、缓存、性能优化

#### 数据处理 (`data/`)
- **原始数据**: 各类别的USTB教务文档
- **处理后数据**: 向量嵌入和训练数据集
- **训练数据**: 用于模型微调的问答对生成

### 服务启动顺序

**关键**: 服务必须按以下特定顺序启动：

1. **AutoDL服务** (远程云端):
   - RAG Service v2.0 (端口 8000)
   - LoRA推理服务 (端口 8001)
   - 混合API服务 (端口 8003)

2. **SSH隧道** (本地):
   ```bash
   python system/ssh_tunnel/start_tunnels.py
   ```

3. **本地服务**:
   - 后端API服务器 (端口 8001): `python src/backend/app.py`
   - 前端Web服务器 (端口 3000): `cd src/frontend && yarn dev`

### 配置管理

#### 环境变量
- `DATABASE_URL`: MySQL连接字符串
- `RAG_API_URL`: RAG系统端点 (默认: http://localhost:8000)
- `HYBRID_API_URL`: 混合API端点 (默认: http://localhost:8002, 通过SSH隧道连接到AutoDL的Web API连接器端口8003)
- `SECRET_KEY`: JWT认证密钥
- `DEBUG`: 启用调试模式

#### 前端配置
- `.env.local`: API密钥和端点的本地环境变量
- `next.config.mjs`: Next.js构建配置
- `app/config/`: 不同环境的运行时配置

#### 后端配置
- `config.py`: 包含数据库、API和安全设置的集中配置
- `requirements.txt`: 带版本固定的Python依赖

### 测试策略

#### 前端测试
- **框架**: Jest配合React Testing Library
- **配置**: `jest.config.ts`与Next.js集成
- **覆盖范围**: 组件测试、API集成测试

#### 后端测试
- **框架**: pytest配合异步支持
- **测试范围**: API端点、数据库操作、认证
- **性能**: 并发用户负载测试

### 开发指南

#### 代码风格
- **前端**: ESLint + Prettier配置
- **后端**: Python Black格式化 (在requirements中配置)
- **TypeScript**: 启用严格类型检查

#### 安全考虑
- 基于JWT的认证
- 可信域名的CORS配置
- 使用Pydantic模型进行输入验证
- 使用ORM防止SQL注入

#### 性能优化
- 数据库操作连接池
- 频繁访问数据的Redis缓存
- 向量存储优化，实现200ms以下响应时间
- 静态资源CDN集成

### 故障排除

#### 常见问题
1. **端口冲突**: 确保在启动SSH隧道前AutoDL服务正在运行
2. **认证失败**: 检查JWT配置和令牌过期
3. **RAG系统连接**: 验证SSH隧道状态和AutoDL服务健康状况
4. **前端构建问题**: 清除Next.js缓存: `rm -rf .next`

#### 健康检查端点
- 前端: http://localhost:3000
- 后端: http://localhost:8001/health
- RAG系统: http://localhost:8000/health
- 混合API: http://localhost:8003/health

#### 日志位置
- 后端: `logs/ustb_backend.log`
- RAG系统: `logs/rag_service.log`
- AutoDL服务: 检查`logs/`目录中的服务特定日志
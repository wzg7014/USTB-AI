<manual>
<identity>
## 工具名称
@tool://github-manager

## 简介
GitHub 仓库管理工具，支持仓库创建、查询、上传和管理操作
</identity>

<purpose>
⚠️ **AI重要提醒**: 调用此工具前必须完整阅读本说明书，理解工具功能边界、参数要求和使用限制。禁止在不了解工具功能的情况下盲目调用。

## 核心问题定义
解决开发者需要频繁进行 GitHub 仓库管理操作的痛点，包括创建仓库、查询仓库信息、上传项目等常见操作。

## 价值主张
- 🎯 **解决什么痛点**：简化 GitHub 仓库管理操作，避免频繁切换到浏览器或命令行
- 🚀 **带来什么价值**：提高开发效率，统一仓库管理入口，支持批量操作
- 🌟 **独特优势**：集成在 PromptX 环境中，支持 AI 辅助的智能仓库管理

## 应用边界
- ✅ **适用场景**：GitHub 仓库的 CRUD 操作、项目上传、仓库信息查询
- ❌ **不适用场景**：复杂的 Git 分支管理、大文件处理、企业级权限管理
</purpose>

<usage>
## 使用时机
- 需要创建新的 GitHub 仓库时
- 查询现有仓库信息时
- 将本地项目上传到 GitHub 时
- 批量管理多个仓库时

## 操作步骤
1. **认证阶段**：提供 GitHub Personal Access Token
2. **操作选择**：选择具体的管理操作（创建、查询、上传等）
3. **参数配置**：根据操作类型提供相应参数
4. **执行验证**：检查操作结果并确认成功

## 最佳实践
- 🎯 **Token 安全**：使用具有适当权限的 Personal Access Token
- ⚠️ **权限控制**：避免使用过高权限的 Token
- 🔧 **错误处理**：注意网络连接和 API 限制

## 注意事项
- 需要有效的 GitHub Personal Access Token
- 遵守 GitHub API 使用限制
- 大文件上传可能需要较长时间
</usage>

<parameter>
## 必需参数
| 参数名 | 类型 | 描述 | 示例 |
|--------|------|------|------|
| action | string | 操作类型 | "create", "list", "upload" |
| token | string | GitHub Personal Access Token | "ghp_xxxx" 或 "github_pat_xxxx" |

## 可选参数
| 参数名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| repoName | string | null | 仓库名称（创建/上传时需要） |
| description | string | "" | 仓库描述 |
| private | boolean | false | 是否为私有仓库 |
| localPath | string | null | 本地项目路径（上传时需要） |

## 参数约束
- **Token 格式**：必须是有效的 GitHub Personal Access Token（支持 ghp_ 或 github_pat_ 格式）
- **仓库名称**：符合 GitHub 命名规范，不能包含特殊字符
- **路径限制**：本地路径必须存在且可访问

## 参数示例
```json
{
  "action": "create",
  "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
  "repoName": "my-new-project",
  "description": "A new project created via PromptX",
  "private": false
}
```
</parameter>

<outcome>
## 成功返回格式
```json
{
  "success": true,
  "data": {
    "action": "create",
    "repository": {
      "name": "my-new-project",
      "fullName": "username/my-new-project",
      "url": "https://github.com/username/my-new-project",
      "cloneUrl": "https://github.com/username/my-new-project.git"
    }
  }
}
```

## 错误处理格式
```json
{
  "success": false,
  "error": {
    "code": "AUTH_ERROR",
    "message": "GitHub 认证失败，请检查 Token",
    "details": "Invalid token provided"
  }
}
```

## 结果解读指南
- **成功标识**：success 字段为 true 表示操作成功
- **仓库信息**：data.repository 包含创建的仓库详细信息
- **错误分类**：根据 error.code 判断错误类型并采取相应措施

## 后续动作建议
- 创建成功后可以克隆仓库到本地进行开发
- 上传成功后可以在 GitHub 上查看项目
- 出现错误时检查 Token 权限和网络连接
</outcome>
</manual>

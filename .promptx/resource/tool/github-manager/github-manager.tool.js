/**
 * GitHub Manager Tool for PromptX
 * 基于原有 github-manager 项目的核心功能，适配 PromptX 工具标准
 */

module.exports = {
  getDependencies() {
    return [
      'axios@^1.6.0',
      'simple-git@^3.20.0',
      'fs-extra@^11.1.1'
    ];
  },

  getMetadata() {
    return {
      name: 'github-manager',
      description: 'GitHub 仓库管理工具，支持仓库创建、查询、上传和管理操作',
      version: '1.0.0',
      category: 'development',
      author: '鲁班',
      tags: ['github', 'repository', 'git', 'management'],
      manual: '@manual://github-manager'
    };
  },

  getSchema() {
    return {
      type: 'object',
      properties: {
        action: {
          type: 'string',
          enum: ['create', 'list', 'upload', 'info'],
          description: '操作类型：create-创建仓库, list-列出仓库, upload-上传项目, info-获取仓库信息'
        },
        token: {
          type: 'string',
          description: 'GitHub Personal Access Token',
          pattern: '^(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]+)$'
        },
        repoName: {
          type: 'string',
          description: '仓库名称（创建/上传时需要）'
        },
        description: {
          type: 'string',
          description: '仓库描述',
          default: ''
        },
        private: {
          type: 'boolean',
          description: '是否为私有仓库',
          default: false
        },
        localPath: {
          type: 'string',
          description: '本地项目路径（上传时需要）'
        }
      },
      required: ['action', 'token']
    };
  },

  validate(params) {
    const errors = [];

    // 验证必需参数
    if (!params.action) {
      errors.push('action 参数是必需的');
    }

    if (!params.token) {
      errors.push('token 参数是必需的');
    }

    // 验证 token 格式
    if (params.token && !params.token.startsWith('ghp_') && !params.token.startsWith('github_pat_')) {
      errors.push('token 格式不正确，应该以 ghp_ 或 github_pat_ 开头');
    }

    // 根据操作类型验证特定参数
    if (params.action === 'create' || params.action === 'upload') {
      if (!params.repoName) {
        errors.push(`${params.action} 操作需要 repoName 参数`);
      }
    }

    if (params.action === 'upload' && !params.localPath) {
      errors.push('upload 操作需要 localPath 参数');
    }

    return {
      valid: errors.length === 0,
      errors: errors
    };
  },

  async execute(params) {
    const axios = require('axios');
    const simpleGit = require('simple-git');
    const fs = require('fs-extra');
    const path = require('path');

    try {
      // 创建 GitHub API 客户端
      const api = axios.create({
        baseURL: 'https://api.github.com',
        headers: {
          'Authorization': `token ${params.token}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      // 验证 token 并获取用户信息
      let userInfo;
      try {
        const userResponse = await api.get('/user');
        userInfo = userResponse.data;
      } catch (error) {
        return {
          success: false,
          error: {
            code: 'AUTH_ERROR',
            message: 'GitHub 认证失败，请检查 Token',
            details: error.response?.data?.message || error.message
          }
        };
      }

      // 根据操作类型执行相应功能
      switch (params.action) {
        case 'list':
          return await this.listRepositories(api);
        
        case 'create':
          return await this.createRepository(api, params);
        
        case 'upload':
          return await this.uploadProject(api, params, userInfo.login);
        
        case 'info':
          return await this.getRepositoryInfo(api, params, userInfo.login);
        
        default:
          return {
            success: false,
            error: {
              code: 'INVALID_ACTION',
              message: `不支持的操作类型: ${params.action}`,
              details: '支持的操作: create, list, upload, info'
            }
          };
      }

    } catch (error) {
      return {
        success: false,
        error: {
          code: 'EXECUTION_ERROR',
          message: '工具执行失败',
          details: error.message
        }
      };
    }
  },

  // 列出用户仓库
  async listRepositories(api) {
    try {
      const response = await api.get('/user/repos', {
        params: {
          per_page: 50,
          sort: 'updated'
        }
      });

      const repositories = response.data.map(repo => ({
        name: repo.name,
        fullName: repo.full_name,
        description: repo.description,
        private: repo.private,
        url: repo.html_url,
        cloneUrl: repo.clone_url,
        language: repo.language,
        updatedAt: repo.updated_at
      }));

      return {
        success: true,
        data: {
          action: 'list',
          count: repositories.length,
          repositories: repositories
        }
      };
    } catch (error) {
      return {
        success: false,
        error: {
          code: 'API_ERROR',
          message: '获取仓库列表失败',
          details: error.response?.data?.message || error.message
        }
      };
    }
  },

  // 创建新仓库
  async createRepository(api, params) {
    try {
      const response = await api.post('/user/repos', {
        name: params.repoName,
        description: params.description || '',
        private: params.private || false,
        auto_init: true
      });

      return {
        success: true,
        data: {
          action: 'create',
          repository: {
            name: response.data.name,
            fullName: response.data.full_name,
            url: response.data.html_url,
            cloneUrl: response.data.clone_url,
            sshUrl: response.data.ssh_url
          }
        }
      };
    } catch (error) {
      return {
        success: false,
        error: {
          code: 'CREATE_ERROR',
          message: '创建仓库失败',
          details: error.response?.data?.message || error.message
        }
      };
    }
  },

  // 上传项目到 GitHub
  async uploadProject(api, params, username) {
    const fs = require('fs-extra');
    const simpleGit = require('simple-git');
    
    try {
      // 检查本地路径是否存在
      if (!await fs.pathExists(params.localPath)) {
        return {
          success: false,
          error: {
            code: 'PATH_ERROR',
            message: '本地路径不存在',
            details: `路径 ${params.localPath} 不存在`
          }
        };
      }

      // 首先创建远程仓库
      const createResult = await this.createRepository(api, params);
      if (!createResult.success) {
        return createResult;
      }

      // 初始化本地 Git 仓库并推送
      const git = simpleGit(params.localPath);
      
      // 检查是否已经是 Git 仓库
      const isRepo = await git.checkIsRepo();
      if (!isRepo) {
        await git.init();
      }

      // 添加所有文件
      await git.add('.');
      
      // 提交
      await git.commit('Initial commit via PromptX GitHub Manager');
      
      // 添加远程仓库
      const remoteUrl = createResult.data.repository.cloneUrl;
      await git.addRemote('origin', remoteUrl);
      
      // 推送到远程仓库
      await git.push('origin', 'main');

      return {
        success: true,
        data: {
          action: 'upload',
          repository: createResult.data.repository,
          localPath: params.localPath
        }
      };

    } catch (error) {
      return {
        success: false,
        error: {
          code: 'UPLOAD_ERROR',
          message: '上传项目失败',
          details: error.message
        }
      };
    }
  },

  // 获取仓库信息
  async getRepositoryInfo(api, params, username) {
    try {
      const repoFullName = params.repoName.includes('/') 
        ? params.repoName 
        : `${username}/${params.repoName}`;
      
      const response = await api.get(`/repos/${repoFullName}`);
      
      return {
        success: true,
        data: {
          action: 'info',
          repository: {
            name: response.data.name,
            fullName: response.data.full_name,
            description: response.data.description,
            private: response.data.private,
            url: response.data.html_url,
            cloneUrl: response.data.clone_url,
            language: response.data.language,
            stars: response.data.stargazers_count,
            forks: response.data.forks_count,
            createdAt: response.data.created_at,
            updatedAt: response.data.updated_at
          }
        }
      };
    } catch (error) {
      return {
        success: false,
        error: {
          code: 'INFO_ERROR',
          message: '获取仓库信息失败',
          details: error.response?.data?.message || error.message
        }
      };
    }
  }
};

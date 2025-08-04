#!/usr/bin/env node

/**
 * Mem0 Memory System Tool for PromptX
 * 基于Mem0的智能记忆系统工具
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class Mem0MemoryTool {
    constructor() {
        this.name = 'mem0-memory';
        this.description = 'Enhanced memory system based on Mem0 with intelligent storage and retrieval';
        this.version = '1.0.0';
        this.pythonScript = path.join(__dirname, 'mem0_memory_handler.py');
    }

    /**
     * 执行工具
     * @param {Object} params - 参数对象
     * @returns {Promise<Object>} 执行结果
     */
    async execute(params) {
        try {
            const { action, user_id = 'luoxiaohan', ...otherParams } = params;
            
            if (!action) {
                throw new Error('Action parameter is required');
            }

            // 准备Python脚本参数
            const scriptArgs = [
                this.pythonScript,
                '--action', action,
                '--user_id', user_id,
                '--params', JSON.stringify(otherParams)
            ];

            const result = await this.runPythonScript(scriptArgs);
            
            return {
                success: true,
                action: action,
                user_id: user_id,
                result: result,
                timestamp: new Date().toISOString()
            };

        } catch (error) {
            return {
                success: false,
                error: error.message,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * 运行Python脚本
     * @param {Array} args - 脚本参数
     * @returns {Promise<Object>} 脚本执行结果
     */
    runPythonScript(args) {
        return new Promise((resolve, reject) => {
            const python = spawn('python', args, {
                stdio: ['pipe', 'pipe', 'pipe'],
                cwd: process.cwd()
            });

            let stdout = '';
            let stderr = '';

            python.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            python.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            python.on('close', (code) => {
                if (code !== 0) {
                    reject(new Error(`Python script failed: ${stderr}`));
                    return;
                }

                try {
                    const result = JSON.parse(stdout);
                    resolve(result);
                } catch (parseError) {
                    reject(new Error(`Failed to parse Python output: ${parseError.message}`));
                }
            });

            python.on('error', (error) => {
                reject(new Error(`Failed to start Python process: ${error.message}`));
            });
        });
    }

    /**
     * 获取工具信息
     * @returns {Object} 工具信息
     */
    getInfo() {
        return {
            name: this.name,
            description: this.description,
            version: this.version,
            actions: [
                'add_memory',
                'search_memories', 
                'get_all_memories',
                'update_memory',
                'delete_memory',
                'get_memory_history',
                'reset_memories',
                'get_stats'
            ],
            parameters: {
                action: {
                    type: 'string',
                    required: true,
                    description: 'Action to perform'
                },
                user_id: {
                    type: 'string',
                    required: false,
                    default: 'luoxiaohan',
                    description: 'User ID for memory isolation'
                },
                content: {
                    type: 'string',
                    required: false,
                    description: 'Memory content (for add_memory, update_memory)'
                },
                query: {
                    type: 'string',
                    required: false,
                    description: 'Search query (for search_memories)'
                },
                memory_id: {
                    type: 'string',
                    required: false,
                    description: 'Memory ID (for update_memory, delete_memory, get_memory_history)'
                },
                metadata: {
                    type: 'object',
                    required: false,
                    description: 'Additional metadata for memory'
                },
                limit: {
                    type: 'number',
                    required: false,
                    default: 10,
                    description: 'Limit for search results'
                },
                threshold: {
                    type: 'number',
                    required: false,
                    default: 0.7,
                    description: 'Similarity threshold for search'
                }
            }
        };
    }
}

// 主执行逻辑
async function main() {
    try {
        const args = process.argv.slice(2);
        
        if (args.length === 0) {
            console.log(JSON.stringify({
                error: 'No parameters provided',
                usage: 'node mem0-memory.tool.js --action <action> [other params]'
            }));
            process.exit(1);
        }

        // 解析参数
        const params = {};
        for (let i = 0; i < args.length; i += 2) {
            if (args[i].startsWith('--')) {
                const key = args[i].substring(2);
                const value = args[i + 1];
                
                // 尝试解析JSON值
                try {
                    params[key] = JSON.parse(value);
                } catch {
                    params[key] = value;
                }
            }
        }

        const tool = new Mem0MemoryTool();
        const result = await tool.execute(params);
        
        console.log(JSON.stringify(result, null, 2));

    } catch (error) {
        console.log(JSON.stringify({
            success: false,
            error: error.message,
            timestamp: new Date().toISOString()
        }));
        process.exit(1);
    }
}

// 如果直接运行此脚本
if (require.main === module) {
    main();
}

module.exports = Mem0MemoryTool;

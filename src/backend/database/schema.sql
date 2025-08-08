-- USTB AI教务助手数据库表结构
-- 数据库: ustb
-- 字符集: utf8mb4
-- 创建时间: 2025-08-05

-- 设置字符集和时区
SET NAMES utf8mb4;
SET time_zone = '+08:00';

-- 1. 用户表 (users)
CREATE TABLE IF NOT EXISTS `users` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    `user_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户唯一标识',
    `username` VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    `email` VARCHAR(100) NOT NULL UNIQUE COMMENT '邮箱地址',
    `hashed_password` VARCHAR(255) NOT NULL COMMENT '加密密码',
    `full_name` VARCHAR(100) DEFAULT NULL COMMENT '真实姓名',
    `student_id` VARCHAR(20) DEFAULT NULL COMMENT '学号',
    `department` VARCHAR(100) DEFAULT NULL COMMENT '院系',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    `is_admin` BOOLEAN DEFAULT FALSE COMMENT '是否管理员',
    `preferences` JSON DEFAULT NULL COMMENT '用户偏好设置',
    `search_count` INT DEFAULT 0 COMMENT '搜索次数',
    `last_login` DATETIME DEFAULT NULL COMMENT '最后登录时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_username` (`username`),
    INDEX `idx_email` (`email`),
    INDEX `idx_student_id` (`student_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户信息表';

-- 2. 聊天会话表 (chat_sessions)
CREATE TABLE IF NOT EXISTS `chat_sessions` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '会话ID',
    `session_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '会话唯一标识',
    `user_id` VARCHAR(50) NOT NULL COMMENT '用户ID',
    `title` VARCHAR(200) NOT NULL COMMENT '会话标题',
    `message_count` INT DEFAULT 0 COMMENT '消息数量',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted_at` DATETIME DEFAULT NULL COMMENT '删除时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_is_active` (`is_active`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天会话表';

-- 3. 聊天消息表 (chat_messages)
CREATE TABLE IF NOT EXISTS `chat_messages` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '消息ID',
    `message_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '消息唯一标识',
    `session_id` VARCHAR(50) NOT NULL COMMENT '会话ID',
    `role` ENUM('user', 'assistant', 'system') NOT NULL COMMENT '角色类型',
    `content` TEXT NOT NULL COMMENT '消息内容',
    `message_type` VARCHAR(20) DEFAULT 'text' COMMENT '消息类型',
    `rag_results` JSON DEFAULT NULL COMMENT 'RAG搜索结果',
    `response_time` DECIMAL(8,3) DEFAULT NULL COMMENT '响应时间(秒)',
    `error_details` TEXT DEFAULT NULL COMMENT '错误详情',
    `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '消息时间',
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_message_id` (`message_id`),
    INDEX `idx_timestamp` (`timestamp`),
    INDEX `idx_role` (`role`),
    FOREIGN KEY (`session_id`) REFERENCES `chat_sessions`(`session_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

-- 4. 用户反馈表 (user_feedback)
CREATE TABLE IF NOT EXISTS `user_feedback` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '反馈ID',
    `feedback_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '反馈唯一标识',
    `user_id` VARCHAR(50) NOT NULL COMMENT '用户ID',
    `query_id` VARCHAR(50) DEFAULT NULL COMMENT '关联查询ID',
    `result_id` VARCHAR(50) DEFAULT NULL COMMENT '关联结果ID',
    `feedback_type` ENUM('helpful', 'not_helpful', 'irrelevant', 'error', 'suggestion') NOT NULL COMMENT '反馈类型',
    `rating` TINYINT DEFAULT NULL COMMENT '评分(1-5)',
    `comment` TEXT DEFAULT NULL COMMENT '反馈评论',
    `category` VARCHAR(50) DEFAULT NULL COMMENT '反馈分类',
    `tags` JSON DEFAULT NULL COMMENT '标签列表',
    `metadata` JSON DEFAULT NULL COMMENT '额外元数据',
    `status` ENUM('submitted', 'processing', 'processed', 'closed') DEFAULT 'submitted' COMMENT '处理状态',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `processed_at` DATETIME DEFAULT NULL COMMENT '处理时间',
    `response` TEXT DEFAULT NULL COMMENT '处理回复',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_feedback_id` (`feedback_id`),
    INDEX `idx_feedback_type` (`feedback_type`),
    INDEX `idx_rating` (`rating`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_status` (`status`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户反馈表';

-- 5. 教务分类表 (categories)
CREATE TABLE IF NOT EXISTS `categories` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '分类ID',
    `category_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '分类唯一标识',
    `name` VARCHAR(100) NOT NULL COMMENT '分类名称',
    `display_name` VARCHAR(100) NOT NULL COMMENT '显示名称',
    `description` TEXT DEFAULT NULL COMMENT '分类描述',
    `icon` VARCHAR(20) DEFAULT NULL COMMENT '分类图标',
    `parent_id` VARCHAR(50) DEFAULT NULL COMMENT '父分类ID',
    `level` TINYINT DEFAULT 1 COMMENT '分类层级',
    `sort_order` INT DEFAULT 999 COMMENT '排序顺序',
    `document_count` INT DEFAULT 0 COMMENT '文档数量',
    `recent_searches` INT DEFAULT 0 COMMENT '最近搜索次数',
    `avg_score` DECIMAL(3,2) DEFAULT 0.00 COMMENT '平均质量评分',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_category_id` (`category_id`),
    INDEX `idx_parent_id` (`parent_id`),
    INDEX `idx_level` (`level`),
    INDEX `idx_sort_order` (`sort_order`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教务分类表';

-- 6. 搜索历史表 (search_history)
CREATE TABLE IF NOT EXISTS `search_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '历史ID',
    `user_id` VARCHAR(50) NOT NULL COMMENT '用户ID',
    `query` VARCHAR(500) NOT NULL COMMENT '搜索查询',
    `category` VARCHAR(50) DEFAULT NULL COMMENT '搜索分类',
    `results_count` INT DEFAULT 0 COMMENT '结果数量',
    `response_time` DECIMAL(8,3) DEFAULT NULL COMMENT '响应时间(秒)',
    `clicked_results` JSON DEFAULT NULL COMMENT '点击的结果ID列表',
    `search_filters` JSON DEFAULT NULL COMMENT '搜索过滤条件',
    `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '用户代理',
    `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
    `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '搜索时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_query` (`query`(100)),
    INDEX `idx_category` (`category`),
    INDEX `idx_timestamp` (`timestamp`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索历史表';

-- 7. 系统配置表 (system_config)
CREATE TABLE IF NOT EXISTS `system_config` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
    `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    `config_value` TEXT DEFAULT NULL COMMENT '配置值',
    `config_type` ENUM('string', 'number', 'boolean', 'json') DEFAULT 'string' COMMENT '配置类型',
    `description` VARCHAR(500) DEFAULT NULL COMMENT '配置描述',
    `is_public` BOOLEAN DEFAULT FALSE COMMENT '是否公开',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_config_key` (`config_key`),
    INDEX `idx_is_public` (`is_public`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 8. API调用日志表 (api_logs)
CREATE TABLE IF NOT EXISTS `api_logs` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    `user_id` VARCHAR(50) DEFAULT NULL COMMENT '用户ID',
    `method` VARCHAR(10) NOT NULL COMMENT 'HTTP方法',
    `endpoint` VARCHAR(200) NOT NULL COMMENT 'API端点',
    `status_code` INT NOT NULL COMMENT 'HTTP状态码',
    `response_time` DECIMAL(8,3) DEFAULT NULL COMMENT '响应时间(秒)',
    `request_size` INT DEFAULT NULL COMMENT '请求大小(字节)',
    `response_size` INT DEFAULT NULL COMMENT '响应大小(字节)',
    `user_agent` VARCHAR(500) DEFAULT NULL COMMENT '用户代理',
    `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP地址',
    `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
    `timestamp` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '请求时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_endpoint` (`endpoint`),
    INDEX `idx_status_code` (`status_code`),
    INDEX `idx_timestamp` (`timestamp`),
    INDEX `idx_method` (`method`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API调用日志表';

-- 插入默认系统配置
INSERT INTO `system_config` (`config_key`, `config_value`, `config_type`, `description`, `is_public`) VALUES
('system_name', 'USTB AI教务助手', 'string', '系统名称', TRUE),
('system_version', '1.0.0', 'string', '系统版本', TRUE),
('max_search_results', '20', 'number', '最大搜索结果数', FALSE),
('default_page_size', '10', 'number', '默认分页大小', TRUE),
('enable_feedback', 'true', 'boolean', '是否启用用户反馈', TRUE),
('maintenance_mode', 'false', 'boolean', '维护模式', FALSE);

-- 插入默认分类数据
INSERT INTO `categories` (`category_id`, `name`, `display_name`, `description`, `icon`, `sort_order`) VALUES
('course_selection', '选课管理', '选课管理', '课程选择、退课、课程表查询等', '📚', 1),
('exam_management', '考试管理', '考试管理', '考试安排、成绩查询、补考申请等', '📝', 2),
('student_status', '学籍管理', '学籍管理', '学籍变更、休学复学、转专业等', '👨‍🎓', 3),
('graduation', '毕业管理', '毕业管理', '毕业要求、学位申请、毕业证书等', '🎓', 4),
('scholarship', '奖助学金', '奖助学金', '奖学金申请、助学金、勤工助学等', '💰', 5),
('international', '国际交流', '国际交流', '交换生项目、海外学习、国际合作等', '🌍', 6),
('campus_life', '校园生活', '校园生活', '住宿管理、食堂服务、校园卡等', '🏫', 7),
('other', '其他事务', '其他事务', '其他教务相关事务', '📋', 8);

-- 创建管理员用户（密码: admin123，实际使用时应该修改）
INSERT INTO `users` (`user_id`, `username`, `email`, `hashed_password`, `full_name`, `is_admin`) VALUES
('admin_001', 'admin', 'admin@ustb.edu.cn', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e', '系统管理员', TRUE);

COMMIT;

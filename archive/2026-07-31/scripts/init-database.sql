-- ============================================
-- 抽奖引擎数据库初始化脚本
-- ============================================
-- 使用方法：
-- 1. 在MySQL客户端执行此脚本
-- 2. 或者在命令行执行：mysql -u root -p < init-database.sql
-- ============================================

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS lottery_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. 使用数据库
USE lottery_db;

-- 3. 创建活动表
CREATE TABLE IF NOT EXISTS `activity` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `activity_id` bigint(20) NOT NULL COMMENT '活动ID',
    `activity_name` varchar(64) NOT NULL COMMENT '活动名称',
    `activity_desc` varchar(128) DEFAULT NULL COMMENT '活动描述',
    `begin_date_time` datetime NOT NULL COMMENT '开始时间',
    `end_date_time` datetime NOT NULL COMMENT '结束时间',
    `stock_count` int(11) NOT NULL COMMENT '库存',
    `take_count` int(11) DEFAULT NULL COMMENT '每人可参与次数',
    `state` tinyint(2) NOT NULL DEFAULT '1' COMMENT '活动状态：1编辑、2提审、3撤审、4通过、5运行(审核通过后worker扫描状态)、6拒绝、7关闭、8开启',
    `creator` varchar(32) NOT NULL COMMENT '创建人',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_activity_id` (`activity_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='活动表';

-- 4. 创建策略表
CREATE TABLE IF NOT EXISTS `strategy` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `strategy_id` bigint(20) NOT NULL COMMENT '策略ID',
    `strategy_desc` varchar(128) DEFAULT NULL COMMENT '策略描述',
    `strategy_mode` tinyint(2) NOT NULL DEFAULT '1' COMMENT '策略方式（1:单项概率、2:总体概率）',
    `grant_type` tinyint(2) NOT NULL DEFAULT '1' COMMENT '发放方式（1:即时、2:定时[含活动结束]、3:人工）',
    `grant_date` datetime DEFAULT NULL COMMENT '发放时间',
    `ext_info` varchar(128) DEFAULT NULL COMMENT '扩展信息',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_strategy_id` (`strategy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略表';

-- 5. 创建策略明细表
CREATE TABLE IF NOT EXISTS `strategy_detail` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `strategy_id` bigint(20) NOT NULL COMMENT '策略ID',
    `award_id` varchar(64) NOT NULL COMMENT '奖品ID',
    `award_name` varchar(128) DEFAULT NULL COMMENT '奖品名称',
    `award_count` int(11) NOT NULL COMMENT '奖品库存',
    `award_surplus_count` int(11) NOT NULL DEFAULT '0' COMMENT '奖品剩余库存',
    `award_rate` decimal(5,2) NOT NULL COMMENT '中奖概率',
    `sort` int(4) NOT NULL DEFAULT '0' COMMENT '排序',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    KEY `idx_strategy_id` (`strategy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略明细表';

-- 6. 创建奖品表
CREATE TABLE IF NOT EXISTS `award` (
    `id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '自增ID',
    `award_id` varchar(64) NOT NULL COMMENT '奖品ID',
    `award_type` tinyint(2) NOT NULL COMMENT '奖品类型（1:文字描述、2:兑换码、3:优惠券、4:实物奖品）',
    `award_name` varchar(64) NOT NULL COMMENT '奖品名称',
    `award_content` varchar(128) DEFAULT NULL COMMENT '奖品内容「描述、奖品码、sku」',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_award_id` (`award_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='奖品表';

-- ============================================
-- 测试数据初始化
-- ============================================

-- 7. 插入活动数据
INSERT INTO `activity` (`activity_id`, `activity_name`, `activity_desc`, `begin_date_time`, `end_date_time`, 
    `stock_count`, `take_count`, `state`, `creator`) 
VALUES 
(100001, '春节抽奖活动', '春节大促销抽奖活动', '2024-01-01 00:00:00', '2024-12-31 23:59:59', 
    1000, 3, 5, 'admin'),
(100002, '618抽奖活动', '618购物节抽奖活动', '2024-06-01 00:00:00', '2024-06-30 23:59:59', 
    500, 2, 5, 'admin')
ON DUPLICATE KEY UPDATE `activity_name`=VALUES(`activity_name`);

-- 8. 插入策略数据
INSERT INTO `strategy` (`strategy_id`, `strategy_desc`, `strategy_mode`, `grant_type`, `grant_date`) 
VALUES 
(100001, '春节抽奖策略', 1, 1, NULL),
(100002, '618抽奖策略', 2, 1, NULL)
ON DUPLICATE KEY UPDATE `strategy_desc`=VALUES(`strategy_desc`);

-- 9. 插入策略明细数据（活动ID 100001）
INSERT INTO `strategy_detail` (`strategy_id`, `award_id`, `award_name`, `award_count`, `award_surplus_count`, 
    `award_rate`, `sort`) 
VALUES 
(100001, '101', 'iPhone 15 Pro', 10, 10, 0.01, 1),
(100001, '102', 'MacBook Pro', 20, 20, 0.02, 2),
(100001, '103', 'AirPods Pro', 50, 50, 0.05, 3),
(100001, '104', '100元优惠券', 200, 200, 0.20, 4),
(100001, '105', '50元优惠券', 300, 300, 0.30, 5),
(100001, '106', '谢谢参与', 420, 420, 0.42, 6)
ON DUPLICATE KEY UPDATE `award_name`=VALUES(`award_name`);

-- 10. 插入策略明细数据（活动ID 100002）
INSERT INTO `strategy_detail` (`strategy_id`, `award_id`, `award_name`, `award_count`, `award_surplus_count`, 
    `award_rate`, `sort`) 
VALUES 
(100002, '201', 'iPad Air', 5, 5, 0.01, 1),
(100002, '202', 'Apple Watch', 10, 10, 0.02, 2),
(100002, '203', '200元优惠券', 100, 100, 0.20, 3),
(100002, '204', '100元优惠券', 200, 200, 0.30, 4),
(100002, '205', '谢谢参与', 685, 685, 0.47, 5)
ON DUPLICATE KEY UPDATE `award_name`=VALUES(`award_name`);

-- 11. 插入奖品数据
INSERT INTO `award` (`award_id`, `award_type`, `award_name`, `award_content`) 
VALUES 
('101', 4, 'iPhone 15 Pro', 'iPhone 15 Pro 256GB 深空黑色'),
('102', 4, 'MacBook Pro', 'MacBook Pro 14英寸 M3芯片'),
('103', 4, 'AirPods Pro', 'AirPods Pro 第二代'),
('104', 3, '100元优惠券', 'COUPON_100_2024'),
('105', 3, '50元优惠券', 'COUPON_50_2024'),
('106', 1, '谢谢参与', '感谢您的参与，祝您下次好运！'),
('201', 4, 'iPad Air', 'iPad Air 11英寸 M2芯片'),
('202', 4, 'Apple Watch', 'Apple Watch Series 9'),
('203', 3, '200元优惠券', 'COUPON_200_2024'),
('204', 3, '100元优惠券', 'COUPON_100_2024'),
('205', 1, '谢谢参与', '感谢您的参与，祝您下次好运！')
ON DUPLICATE KEY UPDATE `award_name`=VALUES(`award_name`);

-- ============================================
-- 验证数据
-- ============================================

-- 显示表数量
SELECT 'Tables created:' as Info, COUNT(*) as Count FROM information_schema.tables WHERE table_schema = 'lottery_db';

-- 显示活动数据
SELECT 'Activities:' as Info, COUNT(*) as Count FROM activity;

-- 显示策略数据
SELECT 'Strategies:' as Info, COUNT(*) as Count FROM strategy;

-- 显示策略明细数据
SELECT 'Strategy Details:' as Info, COUNT(*) as Count FROM strategy_detail;

-- 显示奖品数据
SELECT 'Awards:' as Info, COUNT(*) as Count FROM award;

-- 显示活动详情
SELECT activity_id, activity_name, stock_count, state FROM activity;

-- ============================================
-- 初始化完成
-- ============================================


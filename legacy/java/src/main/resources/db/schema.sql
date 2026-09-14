-- 活动表
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

-- 策略表
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

-- 策略明细表
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

-- 奖品表
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


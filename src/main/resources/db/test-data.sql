-- 测试数据初始化脚本

-- 插入活动数据
INSERT INTO `activity` (`activity_id`, `activity_name`, `activity_desc`, `begin_date_time`, `end_date_time`, 
    `stock_count`, `take_count`, `state`, `creator`) 
VALUES 
(100001, '春节抽奖活动', '春节大促销抽奖活动', '2024-01-01 00:00:00', '2024-12-31 23:59:59', 
    1000, 3, 5, 'admin'),
(100002, '618抽奖活动', '618购物节抽奖活动', '2024-06-01 00:00:00', '2024-06-30 23:59:59', 
    500, 2, 5, 'admin');

-- 插入策略数据
INSERT INTO `strategy` (`strategy_id`, `strategy_desc`, `strategy_mode`, `grant_type`, `grant_date`) 
VALUES 
(100001, '春节抽奖策略', 1, 1, NULL),
(100002, '618抽奖策略', 2, 1, NULL);

-- 插入策略明细数据（活动ID 100001）
INSERT INTO `strategy_detail` (`strategy_id`, `award_id`, `award_name`, `award_count`, `award_surplus_count`, 
    `award_rate`, `sort`) 
VALUES 
(100001, '101', 'iPhone 15 Pro', 10, 10, 0.01, 1),
(100001, '102', 'MacBook Pro', 20, 20, 0.02, 2),
(100001, '103', 'AirPods Pro', 50, 50, 0.05, 3),
(100001, '104', '100元优惠券', 200, 200, 0.20, 4),
(100001, '105', '50元优惠券', 300, 300, 0.30, 5),
(100001, '106', '谢谢参与', 420, 420, 0.42, 6);

-- 插入策略明细数据（活动ID 100002）
INSERT INTO `strategy_detail` (`strategy_id`, `award_id`, `award_name`, `award_count`, `award_surplus_count`, 
    `award_rate`, `sort`) 
VALUES 
(100002, '201', 'iPad Air', 5, 5, 0.01, 1),
(100002, '202', 'Apple Watch', 10, 10, 0.02, 2),
(100002, '203', '200元优惠券', 100, 100, 0.20, 3),
(100002, '204', '100元优惠券', 200, 200, 0.30, 4),
(100002, '205', '谢谢参与', 685, 685, 0.47, 5);

-- 插入奖品数据
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
('205', 1, '谢谢参与', '感谢您的参与，祝您下次好运！');


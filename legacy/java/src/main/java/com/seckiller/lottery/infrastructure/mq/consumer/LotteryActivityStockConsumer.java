package com.seckiller.lottery.infrastructure.mq.consumer;

import com.alibaba.fastjson.JSON;
import com.seckiller.lottery.domain.award.model.req.GoodsReq;
import com.seckiller.lottery.domain.award.service.distribution.IDistributionGoods;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;

/**
 * 抽奖活动库存消费者
 * 使用MQ解耦抽奖和奖品发放流程
 */
@Slf4j
@Component
@RocketMQMessageListener(
    topic = "lottery_activity_stock",
    consumerGroup = "lottery_activity_stock_consumer_group"
)
public class LotteryActivityStockConsumer implements RocketMQListener<String> {
    
    @Resource
    private IDistributionGoods distributionGoods;
    
    @Override
    public void onMessage(String message) {
        log.info("接收到奖品发放消息：{}", message);
        
        try {
            // 解析消息
            GoodsReq goodsReq = JSON.parseObject(message, GoodsReq.class);
            
            // 执行奖品发放
            boolean success = distributionGoods.doDistribution(goodsReq);
            
            if (success) {
                log.info("奖品发放成功，用户ID：{}，活动ID：{}，奖品ID：{}", 
                    goodsReq.getUId(), goodsReq.getActivityId(), goodsReq.getAwardId());
            } else {
                log.error("奖品发放失败，用户ID：{}，活动ID：{}，奖品ID：{}", 
                    goodsReq.getUId(), goodsReq.getActivityId(), goodsReq.getAwardId());
            }
        } catch (Exception e) {
            log.error("处理奖品发放消息异常：{}", message, e);
            // 实际实现中应该进行重试或记录失败日志
        }
    }
}


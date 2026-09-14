package com.seckiller.lottery.infrastructure.mq.producer;

import com.alibaba.fastjson.JSON;
import com.seckiller.lottery.domain.award.model.req.GoodsReq;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;

/**
 * 抽奖活动库存生产者
 * 发送奖品发放消息到MQ
 */
@Slf4j
@Component
public class LotteryActivityStockProducer {
    
    @Resource
    private RocketMQTemplate rocketMQTemplate;
    
    /**
     * 发送奖品发放消息
     * 
     * @param goodsReq 奖品发放请求
     */
    public void sendMessage(GoodsReq goodsReq) {
        try {
            String message = JSON.toJSONString(goodsReq);
            log.info("发送奖品发放消息：{}", message);
            
            rocketMQTemplate.convertAndSend("lottery_activity_stock", message);
            
            log.info("奖品发放消息发送成功，用户ID：{}，活动ID：{}，奖品ID：{}", 
                goodsReq.getUId(), goodsReq.getActivityId(), goodsReq.getAwardId());
        } catch (Exception e) {
            log.error("发送奖品发放消息失败，用户ID：{}，活动ID：{}，奖品ID：{}", 
                goodsReq.getUId(), goodsReq.getActivityId(), goodsReq.getAwardId(), e);
            throw new RuntimeException("发送奖品发放消息失败", e);
        }
    }
}


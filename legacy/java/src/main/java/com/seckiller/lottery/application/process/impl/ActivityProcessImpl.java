package com.seckiller.lottery.application.process.impl;

import com.seckiller.lottery.application.process.IActivityProcess;
import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.domain.activity.model.res.DrawResult;
import com.seckiller.lottery.domain.activity.model.res.PartakeResult;
import com.seckiller.lottery.domain.activity.service.partake.IActivityPartake;
import com.seckiller.lottery.domain.award.model.req.GoodsReq;
import com.seckiller.lottery.domain.strategy.model.req.DrawReq;
import com.seckiller.lottery.domain.strategy.service.draw.IDrawExec;
import com.seckiller.lottery.domain.activity.model.vo.AwardInfoVO;
import com.seckiller.lottery.infrastructure.mq.producer.LotteryActivityStockProducer;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

/**
 * 活动流程编排实现
 * 应用层：编排领域服务，实现业务流程
 */
@Slf4j
@Service
public class ActivityProcessImpl implements IActivityProcess {
    
    @Resource
    private IActivityPartake activityPartake;
    
    @Resource
    private IDrawExec drawExec;
    
    @Resource
    private LotteryActivityStockProducer lotteryActivityStockProducer;
    
    @Override
    public DrawResult doDrawProcess(PartakeReq req) {
        log.info("开始执行抽奖流程，用户ID：{}，活动ID：{}", req.getUId(), req.getActivityId());
        
        // 1. 参与活动（包含滑动窗口锁校验、库存校验和扣减）
        PartakeResult partakeResult = activityPartake.doPartake(req);
        if (!"0000".equals(partakeResult.getCode())) {
            log.warn("参与活动失败，用户ID：{}，活动ID：{}，原因：{}", 
                req.getUId(), req.getActivityId(), partakeResult.getInfo());
            DrawResult drawResult = new DrawResult();
            drawResult.setUId(req.getUId());
            drawResult.setActivityId(req.getActivityId());
            drawResult.setDrawState(0);
            drawResult.setDrawStateName(partakeResult.getInfo());
            return drawResult;
        }
        
        // 2. 执行抽奖算法
        DrawReq drawReq = new DrawReq();
        drawReq.setUId(req.getUId());
        drawReq.setStrategyId(partakeResult.getStrategyId());
        
        com.seckiller.lottery.domain.strategy.model.res.DrawResult strategyDrawResult = drawExec.doDrawExec(drawReq);
        
        // 3. 封装抽奖结果
        DrawResult drawResult = new DrawResult();
        drawResult.setUId(req.getUId());
        drawResult.setActivityId(req.getActivityId());
        
        // 转换奖品信息
        if (strategyDrawResult.getAwardInfo() != null) {
            AwardInfoVO awardInfoVO = new AwardInfoVO();
            awardInfoVO.setAwardId(strategyDrawResult.getAwardInfo().getAwardId());
            awardInfoVO.setAwardType(strategyDrawResult.getAwardInfo().getAwardType());
            awardInfoVO.setAwardName(strategyDrawResult.getAwardInfo().getAwardName());
            awardInfoVO.setAwardContent(strategyDrawResult.getAwardInfo().getAwardContent());
            drawResult.setAwardInfo(awardInfoVO);
        }
        
        drawResult.setStrategyId(strategyDrawResult.getStrategyId());
        drawResult.setDrawState(strategyDrawResult.getDrawState());
        drawResult.setDrawStateName(strategyDrawResult.getDrawStateName());
        
        // 4. 如果中奖，发送MQ消息进行奖品发放（流程解耦）
        if (strategyDrawResult.getDrawState() == 1 && strategyDrawResult.getAwardInfo() != null) {
            GoodsReq goodsReq = new GoodsReq();
            goodsReq.setUId(req.getUId());
            goodsReq.setActivityId(req.getActivityId());
            goodsReq.setAwardId(strategyDrawResult.getAwardInfo().getAwardId());
            goodsReq.setAwardType(strategyDrawResult.getAwardInfo().getAwardType());
            goodsReq.setAwardName(strategyDrawResult.getAwardInfo().getAwardName());
            goodsReq.setAwardContent(strategyDrawResult.getAwardInfo().getAwardContent());
            
            // 发送MQ消息，异步处理奖品发放
            lotteryActivityStockProducer.sendMessage(goodsReq);
            
            log.info("中奖消息已发送到MQ，用户ID：{}，活动ID：{}，奖品ID：{}", 
                req.getUId(), req.getActivityId(), strategyDrawResult.getAwardInfo().getAwardId());
        }
        
        log.info("抽奖流程执行完成，用户ID：{}，活动ID：{}，中奖状态：{}", 
            req.getUId(), req.getActivityId(), drawResult.getDrawStateName());
        
        return drawResult;
    }
}


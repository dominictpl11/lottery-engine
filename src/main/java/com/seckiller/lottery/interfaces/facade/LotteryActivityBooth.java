package com.seckiller.lottery.interfaces.facade;

import com.seckiller.lottery.application.process.IActivityProcess;
import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.domain.activity.model.res.DrawResult;
import lombok.extern.slf4j.Slf4j;
import org.apache.dubbo.config.annotation.DubboService;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

/**
 * 抽奖活动展台实现（Dubbo服务）
 */
@Slf4j
@Service
@DubboService(version = "1.0.0")
public class LotteryActivityBooth implements ILotteryActivityBooth {
    
    @Resource
    private IActivityProcess activityProcess;
    
    @Override
    public DrawResult doDraw(PartakeReq req) {
        log.info("接收到抽奖请求，用户ID：{}，活动ID：{}", req.getUId(), req.getActivityId());
        return activityProcess.doDrawProcess(req);
    }
}


package com.seckiller.lottery.interfaces.controller;

import com.seckiller.lottery.application.process.IActivityProcess;
import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.domain.activity.model.res.DrawResult;
import com.seckiller.lottery.interfaces.assembler.ActivityMapping;
import com.seckiller.lottery.interfaces.dto.DrawLotteryDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;

/**
 * 抽奖活动控制器（REST接口）
 */
@Slf4j
@RestController
@RequestMapping("/api/lottery")
public class LotteryController {
    
    @Resource
    private IActivityProcess activityProcess;
    
    /**
     * 执行抽奖
     * 
     * @param dto 抽奖请求
     * @return 抽奖结果
     */
    @PostMapping("/draw")
    public DrawResult doDraw(@RequestBody DrawLotteryDTO dto) {
        log.info("接收到抽奖请求，用户ID：{}，活动ID：{}", dto.getUId(), dto.getActivityId());
        
        PartakeReq req = ActivityMapping.toPartakeReq(dto);
        return activityProcess.doDrawProcess(req);
    }
    
    /**
     * 健康检查
     */
    @GetMapping("/health")
    public String health() {
        return "OK";
    }
}


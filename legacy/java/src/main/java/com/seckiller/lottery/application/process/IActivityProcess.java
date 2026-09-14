package com.seckiller.lottery.application.process;

import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.domain.activity.model.res.DrawResult;

/**
 * 活动流程编排接口
 */
public interface IActivityProcess {
    
    /**
     * 执行抽奖流程
     * 
     * @param req 参与活动请求
     * @return 抽奖结果
     */
    DrawResult doDrawProcess(PartakeReq req);
}


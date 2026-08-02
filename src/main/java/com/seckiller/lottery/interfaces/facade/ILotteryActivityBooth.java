package com.seckiller.lottery.interfaces.facade;

import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.domain.activity.model.res.DrawResult;

/**
 * 抽奖活动展台接口（Dubbo服务）
 */
public interface ILotteryActivityBooth {
    
    /**
     * 执行抽奖
     * 
     * @param req 参与活动请求
     * @return 抽奖结果
     */
    DrawResult doDraw(PartakeReq req);
}


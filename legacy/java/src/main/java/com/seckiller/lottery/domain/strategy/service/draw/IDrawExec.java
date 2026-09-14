package com.seckiller.lottery.domain.strategy.service.draw;

import com.seckiller.lottery.domain.strategy.model.req.DrawReq;
import com.seckiller.lottery.domain.strategy.model.res.DrawResult;

/**
 * 抽奖执行接口
 */
public interface IDrawExec {
    
    /**
     * 执行抽奖
     * 
     * @param req 抽奖请求
     * @return 抽奖结果
     */
    DrawResult doDrawExec(DrawReq req);
}


package com.seckiller.lottery.domain.award.service.distribution;

import com.seckiller.lottery.domain.award.model.req.GoodsReq;

/**
 * 奖品发放接口
 */
public interface IDistributionGoods {
    
    /**
     * 发放奖品
     * 
     * @param req 奖品发放请求
     * @return 发放结果
     */
    boolean doDistribution(GoodsReq req);
}


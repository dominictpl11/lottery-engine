package com.seckiller.lottery.domain.activity.service.partake;

import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.domain.activity.model.res.PartakeResult;

/**
 * 活动参与接口
 */
public interface IActivityPartake {
    
    /**
     * 参与活动
     * 
     * @param req 参与请求
     * @return 参与结果
     */
    PartakeResult doPartake(PartakeReq req);
    
    /**
     * 记录奖品单
     * 
     * @param activityId 活动ID
     * @param uId 用户ID
     * @param awardId 奖品ID
     * @return 记录结果
     */
    boolean recordDrawOrder(Long activityId, String uId, String awardId);
}


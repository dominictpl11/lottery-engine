package com.seckiller.lottery.interfaces.assembler;

import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.interfaces.dto.DrawLotteryDTO;

/**
 * 活动对象转换
 */
public class ActivityMapping {
    
    /**
     * 转换为参与活动请求
     * 
     * @param dto DTO对象
     * @return 参与活动请求
     */
    public static PartakeReq toPartakeReq(DrawLotteryDTO dto) {
        PartakeReq req = new PartakeReq();
        req.setUId(dto.getUId());
        req.setActivityId(dto.getActivityId());
        req.setActivityTime(System.currentTimeMillis());
        return req;
    }
}


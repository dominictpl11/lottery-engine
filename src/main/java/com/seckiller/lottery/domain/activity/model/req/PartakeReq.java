package com.seckiller.lottery.domain.activity.model.req;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 参与活动请求
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PartakeReq {
    
    /** 用户ID */
    private String uId;
    
    /** 活动ID */
    private Long activityId;
    
    /** 活动时间 */
    private Long activityTime;
}


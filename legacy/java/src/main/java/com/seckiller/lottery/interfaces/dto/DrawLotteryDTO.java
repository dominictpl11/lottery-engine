package com.seckiller.lottery.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 抽奖请求DTO
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DrawLotteryDTO {
    
    /** 用户ID */
    private String uId;
    
    /** 活动ID */
    private Long activityId;
}


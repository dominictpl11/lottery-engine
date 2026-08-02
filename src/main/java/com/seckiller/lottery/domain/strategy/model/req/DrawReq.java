package com.seckiller.lottery.domain.strategy.model.req;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 抽奖请求
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DrawReq {
    
    /** 用户ID */
    private String uId;
    
    /** 策略ID */
    private Long strategyId;
}


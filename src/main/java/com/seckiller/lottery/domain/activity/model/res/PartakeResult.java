package com.seckiller.lottery.domain.activity.model.res;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 参与活动结果
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PartakeResult {
    
    /** 策略ID */
    private Long strategyId;
    
    /** 活动领取ID */
    private Long takeId;
    
    /** 库存 */
    private Integer stockCount;
    
    /** 库存剩余 */
    private Integer stockSurplusCount;
    
    /** 参与结果 */
    private String code;
    
    /** 描述信息 */
    private String info;
}


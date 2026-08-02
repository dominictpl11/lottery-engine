package com.seckiller.lottery.domain.activity.model.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 策略明细值对象
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StrategyDetailVO {
    
    /** 策略ID */
    private Long strategyId;
    
    /** 奖品ID */
    private String awardId;
    
    /** 奖品名称 */
    private String awardName;
    
    /** 奖品库存 */
    private Integer awardCount;
    
    /** 奖品剩余库存 */
    private Integer awardSurplusCount;
    
    /** 中奖概率 */
    private BigDecimal awardRate;
    
    /** 排序 */
    private Integer sort;
}


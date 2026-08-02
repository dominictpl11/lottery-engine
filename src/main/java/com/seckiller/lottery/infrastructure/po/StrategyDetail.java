package com.seckiller.lottery.infrastructure.po;

import lombok.Data;

import java.math.BigDecimal;
import java.util.Date;

/**
 * 策略明细表
 */
@Data
public class StrategyDetail {
    
    /** 自增ID */
    private Long id;
    
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
    
    /** 创建时间 */
    private Date createTime;
    
    /** 修改时间 */
    private Date updateTime;
}


package com.seckiller.lottery.domain.strategy.model.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 奖品概率信息
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AwardRateInfo {
    
    /** 奖品ID */
    private String awardId;
    
    /** 中奖概率 */
    private BigDecimal awardRate;
}


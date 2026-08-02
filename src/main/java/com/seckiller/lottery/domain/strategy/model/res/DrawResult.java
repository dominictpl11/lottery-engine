package com.seckiller.lottery.domain.strategy.model.res;

import com.seckiller.lottery.domain.strategy.model.vo.DrawAwardVO;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 抽奖结果（策略层）
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DrawResult {
    
    /** 用户ID */
    private String uId;
    
    /** 策略ID */
    private Long strategyId;
    
    /** 奖品ID */
    private String awardId;
    
    /** 奖品信息 */
    private DrawAwardVO awardInfo;
    
    /** 中奖状态：0未中奖、1已中奖、2兜底奖 */
    private Integer drawState;
    
    /** 中奖描述 */
    private String drawStateName;
}


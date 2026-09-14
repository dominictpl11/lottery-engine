package com.seckiller.lottery.domain.activity.model.res;

import com.seckiller.lottery.domain.activity.model.vo.AwardInfoVO;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 抽奖结果
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DrawResult {
    
    /** 用户ID */
    private String uId;
    
    /** 活动ID */
    private Long activityId;
    
    /** 奖品信息 */
    private AwardInfoVO awardInfo;
    
    /** 策略ID */
    private Long strategyId;
    
    /** 中奖状态：0未中奖、1已中奖、2兜底奖 */
    private Integer drawState;
    
    /** 中奖描述 */
    private String drawStateName;
}


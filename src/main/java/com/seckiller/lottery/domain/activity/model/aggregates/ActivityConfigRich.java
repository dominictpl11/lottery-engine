package com.seckiller.lottery.domain.activity.model.aggregates;

import com.seckiller.lottery.domain.activity.model.vo.ActivityInfoVO;
import com.seckiller.lottery.domain.activity.model.vo.AwardInfoVO;
import com.seckiller.lottery.domain.activity.model.vo.StrategyDetailVO;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 活动配置聚合对象
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ActivityConfigRich {
    
    /** 活动信息 */
    private ActivityInfoVO activityInfo;
    
    /** 策略信息(含策略明细) */
    private List<StrategyDetailVO> strategyDetailList;
    
    /** 奖品信息 */
    private List<AwardInfoVO> awardList;
}


package com.seckiller.lottery.domain.strategy.service;

import com.seckiller.lottery.domain.strategy.model.vo.AwardRateInfo;
import com.seckiller.lottery.infrastructure.po.Strategy;

import java.util.List;

/**
 * 抽奖策略接口
 */
public interface IDrawStrategy {
    
    /**
     * 查询策略配置
     * 
     * @param strategyId 策略ID
     * @return 策略配置
     */
    Strategy queryStrategy(Long strategyId);
    
    /**
     * 查询奖品概率配置列表
     * 
     * @param strategyId 策略ID
     * @return 奖品概率配置列表
     */
    List<AwardRateInfo> queryAwardRateInfoList(Long strategyId);
    
    /**
     * 扣减奖品库存
     * 
     * @param strategyId 策略ID
     * @param awardId 奖品ID
     * @return 是否扣减成功
     */
    boolean deductionAwardStock(Long strategyId, String awardId);
}


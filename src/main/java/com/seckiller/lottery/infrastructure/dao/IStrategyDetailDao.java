package com.seckiller.lottery.infrastructure.dao;

import com.seckiller.lottery.infrastructure.po.StrategyDetail;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 策略明细表DAO
 */
@Mapper
public interface IStrategyDetailDao {
    
    /**
     * 查询策略明细列表
     * 
     * @param strategyId 策略ID
     * @return 策略明细列表
     */
    List<StrategyDetail> queryStrategyDetailList(@Param("strategyId") Long strategyId);
    
    /**
     * 扣减奖品库存
     * 
     * @param strategyId 策略ID
     * @param awardId 奖品ID
     * @return 更新行数
     */
    int deductionAwardStock(@Param("strategyId") Long strategyId, @Param("awardId") String awardId);
}


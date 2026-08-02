package com.seckiller.lottery.infrastructure.dao;

import com.seckiller.lottery.infrastructure.po.Strategy;
import org.apache.ibatis.annotations.Mapper;

/**
 * 策略表DAO
 */
@Mapper
public interface IStrategyDao {
    
    /**
     * 查询策略信息
     * 
     * @param strategyId 策略ID
     * @return 策略信息
     */
    Strategy queryStrategy(Long strategyId);
}


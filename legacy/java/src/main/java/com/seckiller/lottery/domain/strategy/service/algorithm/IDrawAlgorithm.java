package com.seckiller.lottery.domain.strategy.service.algorithm;

import com.seckiller.lottery.domain.strategy.model.vo.AwardRateInfo;

import java.util.List;

/**
 * 抽奖算法接口
 * 策略模式：定义算法族，使它们可以互相替换
 */
public interface IDrawAlgorithm {
    
    /**
     * 程序启动时初始化概率元组，在初始化完成后使用过程中不允许修改元组数据
     * 
     * @param strategyId 策略ID
     * @param awardRateInfoList 奖品概率配置集合
     */
    void initRateTuple(Long strategyId, List<AwardRateInfo> awardRateInfoList);
    
    /**
     * 判断是否已经做了数据初始化
     * 
     * @param strategyId 策略ID
     * @return true-已初始化，false-未初始化
     */
    boolean isExistRateTuple(Long strategyId);
    
    /**
     * SecureRandom 生成随机数，索引到对应的奖品信息返回结果
     * 
     * @param strategyId 策略ID
     * @param excludeAwardIds 排除掉已经不能作为抽奖的奖品ID，留给风控和空库存使用
     * @return 中奖结果
     */
    String randomDraw(Long strategyId, List<String> excludeAwardIds);
}


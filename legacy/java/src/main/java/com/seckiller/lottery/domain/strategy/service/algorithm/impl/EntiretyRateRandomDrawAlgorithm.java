package com.seckiller.lottery.domain.strategy.service.algorithm.impl;

import com.seckiller.lottery.domain.strategy.model.vo.AwardRateInfo;
import com.seckiller.lottery.domain.strategy.service.algorithm.IDrawAlgorithm;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.List;

/**
 * 总体概率算法实现
 * 策略模式：具体策略实现
 */
@Slf4j
@Component("entiretyRateRandomDrawAlgorithm")
public class EntiretyRateRandomDrawAlgorithm implements IDrawAlgorithm {
    
    @Override
    public void initRateTuple(Long strategyId, List<AwardRateInfo> awardRateInfoList) {
        // 总体概率算法不需要初始化，因为它是基于每次抽奖时实时计算的
        log.info("总体概率算法，策略ID：{}，无需初始化概率元组", strategyId);
    }
    
    @Override
    public boolean isExistRateTuple(Long strategyId) {
        // 总体概率算法不需要初始化，所以总是返回true
        return true;
    }
    
    @Override
    public String randomDraw(Long strategyId, List<String> excludeAwardIds) {
        log.info("执行总体概率算法，策略ID：{}", strategyId);
        
        // 总体概率算法不需要初始化概率元组，每次抽奖时实时计算
        // 但需要外部提供奖品概率配置列表
        // 这里返回null，由调用方提供奖品概率配置后调用doDraw方法
        log.warn("总体概率算法需要外部提供奖品概率配置，策略ID：{}", strategyId);
        return null;
    }
    
    /**
     * 执行总体概率抽奖
     * 
     * @param awardRateInfoList 奖品概率配置列表
     * @param excludeAwardIds 排除的奖品ID列表
     * @return 中奖奖品ID
     */
    public String doDraw(List<AwardRateInfo> awardRateInfoList, List<String> excludeAwardIds) {
        if (awardRateInfoList == null || awardRateInfoList.isEmpty()) {
            return null;
        }
        
        // 过滤掉排除的奖品
        List<AwardRateInfo> availableAwards = new ArrayList<>();
        for (AwardRateInfo awardRateInfo : awardRateInfoList) {
            if (excludeAwardIds == null || !excludeAwardIds.contains(awardRateInfo.getAwardId())) {
                availableAwards.add(awardRateInfo);
            }
        }
        
        if (availableAwards.isEmpty()) {
            return null;
        }
        
        // 计算总概率
        BigDecimal totalRate = BigDecimal.ZERO;
        for (AwardRateInfo awardRateInfo : availableAwards) {
            totalRate = totalRate.add(awardRateInfo.getAwardRate());
        }
        
        // 生成随机数
        SecureRandom random = new SecureRandom();
        BigDecimal randomValue = BigDecimal.valueOf(random.nextDouble()).multiply(totalRate);
        
        // 遍历奖品列表，找到对应的奖品
        BigDecimal currentRate = BigDecimal.ZERO;
        for (AwardRateInfo awardRateInfo : availableAwards) {
            currentRate = currentRate.add(awardRateInfo.getAwardRate());
            if (randomValue.compareTo(currentRate) <= 0) {
                return awardRateInfo.getAwardId();
            }
        }
        
        // 兜底返回最后一个奖品
        return availableAwards.get(availableAwards.size() - 1).getAwardId();
    }
}


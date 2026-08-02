package com.seckiller.lottery.domain.strategy.service.algorithm.impl;

import com.seckiller.lottery.domain.strategy.model.vo.AwardRateInfo;
import com.seckiller.lottery.domain.strategy.service.algorithm.IDrawAlgorithm;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 单项概率算法实现（滑动窗口锁优化版本）
 * 策略模式：具体策略实现
 */
@Slf4j
@Component("defaultRateRandomDrawAlgorithm")
public class DefaultRateRandomDrawAlgorithm implements IDrawAlgorithm {
    
    /** 存储策略ID对应的概率元组 */
    private final Map<Long, List<Integer>> rateTupleMap = new ConcurrentHashMap<>();
    
    @Override
    public void initRateTuple(Long strategyId, List<AwardRateInfo> awardRateInfoList) {
        // 判断该策略ID是否已经初始化过
        if (isExistRateTuple(strategyId)) {
            log.warn("策略ID：{}，已经初始化过概率元组，无需重复初始化", strategyId);
            return;
        }
        
        // 初始化概率元组
        List<Integer> rateTuple = new ArrayList<>();
        int totalRate = 0;
        
        for (AwardRateInfo awardRateInfo : awardRateInfoList) {
            int rate = awardRateInfo.getAwardRate().multiply(new BigDecimal(100)).intValue();
            totalRate += rate;
            // 将奖品ID按照概率数量填充到元组中
            for (int i = 0; i < rate; i++) {
                rateTuple.add(Integer.parseInt(awardRateInfo.getAwardId()));
            }
        }
        
        rateTupleMap.put(strategyId, rateTuple);
        log.info("策略ID：{}，初始化概率元组完成，总概率：{}", strategyId, totalRate);
    }
    
    @Override
    public boolean isExistRateTuple(Long strategyId) {
        return rateTupleMap.containsKey(strategyId);
    }
    
    @Override
    public String randomDraw(Long strategyId, List<String> excludeAwardIds) {
        List<Integer> rateTuple = rateTupleMap.get(strategyId);
        if (rateTuple == null || rateTuple.isEmpty()) {
            log.warn("策略ID：{}，概率元组未初始化", strategyId);
            return null;
        }
        
        // 过滤掉排除的奖品
        List<Integer> availableTuple = new ArrayList<>();
        for (Integer awardId : rateTuple) {
            if (excludeAwardIds == null || !excludeAwardIds.contains(String.valueOf(awardId))) {
                availableTuple.add(awardId);
            }
        }
        
        if (availableTuple.isEmpty()) {
            log.warn("策略ID：{}，所有奖品都被排除", strategyId);
            return null;
        }
        
        // 随机获取一个索引
        SecureRandom random = new SecureRandom();
        int randomIndex = random.nextInt(availableTuple.size());
        Integer awardId = availableTuple.get(randomIndex);
        
        log.info("策略ID：{}，抽奖结果：{}", strategyId, awardId);
        return String.valueOf(awardId);
    }
}


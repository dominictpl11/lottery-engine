package com.seckiller.lottery.domain.strategy.service.algorithm.impl;

import com.seckiller.lottery.domain.strategy.service.algorithm.IDrawAlgorithm;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 算法工厂类
 * 工厂模式：根据策略模式类型创建对应的算法实现
 */
@Component
public class AlgorithmFactory {
    
    /** 存储算法实现 */
    private final Map<Integer, IDrawAlgorithm> algorithmMap = new ConcurrentHashMap<>();
    
    /**
     * 注册算法
     * 
     * @param strategyMode 策略模式（1:单项概率、2:总体概率）
     * @param algorithm 算法实现
     */
    public void registerAlgorithm(Integer strategyMode, IDrawAlgorithm algorithm) {
        algorithmMap.put(strategyMode, algorithm);
    }
    
    /**
     * 获取算法实现
     * 
     * @param strategyMode 策略模式
     * @return 算法实现
     */
    public IDrawAlgorithm getAlgorithm(Integer strategyMode) {
        IDrawAlgorithm algorithm = algorithmMap.get(strategyMode);
        if (algorithm == null) {
            throw new RuntimeException("未找到对应的算法实现，策略模式：" + strategyMode);
        }
        return algorithm;
    }
}


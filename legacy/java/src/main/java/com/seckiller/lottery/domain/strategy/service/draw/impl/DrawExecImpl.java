package com.seckiller.lottery.domain.strategy.service.draw.impl;

import com.seckiller.lottery.domain.strategy.model.req.DrawReq;
import com.seckiller.lottery.domain.strategy.model.res.DrawResult;
import com.seckiller.lottery.domain.strategy.model.vo.AwardRateInfo;
import com.seckiller.lottery.domain.strategy.model.vo.DrawAwardVO;
import com.seckiller.lottery.domain.strategy.service.algorithm.IDrawAlgorithm;
import com.seckiller.lottery.domain.strategy.service.algorithm.impl.AlgorithmFactory;
import com.seckiller.lottery.domain.strategy.service.algorithm.impl.EntiretyRateRandomDrawAlgorithm;
import com.seckiller.lottery.domain.strategy.service.draw.IDrawExec;
import com.seckiller.lottery.domain.strategy.service.IDrawStrategy;
import com.seckiller.lottery.infrastructure.dao.IAwardDao;
import com.seckiller.lottery.infrastructure.po.Award;
import com.seckiller.lottery.infrastructure.po.Strategy;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.List;

/**
 * 抽奖执行实现
 * 模板方法模式：定义算法骨架，具体步骤由子类实现
 */
@Slf4j
@Service
public class DrawExecImpl implements IDrawExec {
    
    @Resource
    private AlgorithmFactory algorithmFactory;
    
    @Autowired
    @Qualifier("defaultRateRandomDrawAlgorithm")
    private IDrawAlgorithm defaultRateRandomDrawAlgorithm;
    
    @Autowired
    @Qualifier("entiretyRateRandomDrawAlgorithm")
    private IDrawAlgorithm entiretyRateRandomDrawAlgorithm;
    
    @Resource
    private IDrawStrategy drawStrategy;
    
    @Resource
    private IAwardDao awardDao;
    
    @PostConstruct
    public void init() {
        // 注册算法实现
        algorithmFactory.registerAlgorithm(1, defaultRateRandomDrawAlgorithm); // 单项概率
        algorithmFactory.registerAlgorithm(2, entiretyRateRandomDrawAlgorithm); // 总体概率
    }
    
    @Override
    public DrawResult doDrawExec(DrawReq req) {
        log.info("执行抽奖，用户ID：{}，策略ID：{}", req.getUId(), req.getStrategyId());
        
        // 1. 获取策略配置
        Strategy strategy = drawStrategy.queryStrategy(req.getStrategyId());
        if (strategy == null) {
            log.warn("策略配置不存在，策略ID：{}", req.getStrategyId());
            return buildDrawResult(req, null, 0, "策略配置不存在");
        }
        
        Integer strategyMode = strategy.getStrategyMode();
        
        // 2. 获取算法实现
        IDrawAlgorithm drawAlgorithm = algorithmFactory.getAlgorithm(strategyMode);
        
        // 3. 获取奖品概率配置列表
        List<AwardRateInfo> awardRateInfoList = drawStrategy.queryAwardRateInfoList(req.getStrategyId());
        if (awardRateInfoList == null || awardRateInfoList.isEmpty()) {
            log.warn("奖品概率配置为空，策略ID：{}", req.getStrategyId());
            return buildDrawResult(req, null, 0, "奖品配置为空");
        }
        
        // 4. 初始化概率元组（单项概率算法需要初始化，总体概率算法不需要）
        if (strategyMode == 1 && !drawAlgorithm.isExistRateTuple(req.getStrategyId())) {
            drawAlgorithm.initRateTuple(req.getStrategyId(), awardRateInfoList);
        }
        
        // 5. 执行抽奖算法
        List<String> excludeAwardIds = new ArrayList<>(); // 排除的奖品ID列表（可用于风控）
        String awardId;
        
        if (strategyMode == 1) {
            // 单项概率算法
            awardId = drawAlgorithm.randomDraw(req.getStrategyId(), excludeAwardIds);
        } else {
            // 总体概率算法
            EntiretyRateRandomDrawAlgorithm entiretyAlgorithm = 
                (EntiretyRateRandomDrawAlgorithm) drawAlgorithm;
            awardId = entiretyAlgorithm.doDraw(awardRateInfoList, excludeAwardIds);
        }
        
        // 5. 封装结果
        DrawResult drawResult = buildDrawResult(req, awardId, strategyMode, 
            awardId != null ? "已中奖" : "未中奖");
        
        // 6. 封装奖品详细信息
        if (awardId != null) {
            Award award = awardDao.queryAwardInfo(awardId);
            if (award != null) {
                DrawAwardVO awardInfo = new DrawAwardVO();
                awardInfo.setUId(req.getUId());
                awardInfo.setAwardId(awardId);
                awardInfo.setAwardType(award.getAwardType());
                awardInfo.setAwardName(award.getAwardName());
                awardInfo.setAwardContent(award.getAwardContent());
                awardInfo.setStrategyMode(strategyMode);
                drawResult.setAwardInfo(awardInfo);
                
                // 扣减奖品库存
                drawStrategy.deductionAwardStock(req.getStrategyId(), awardId);
            }
        }
        
        return drawResult;
    }
    
    /**
     * 构建抽奖结果
     */
    private DrawResult buildDrawResult(DrawReq req, String awardId, Integer strategyMode, String stateName) {
        DrawResult drawResult = new DrawResult();
        drawResult.setUId(req.getUId());
        drawResult.setStrategyId(req.getStrategyId());
        drawResult.setAwardId(awardId);
        drawResult.setDrawState(awardId != null ? 1 : 0);
        drawResult.setDrawStateName(stateName);
        return drawResult;
    }
}


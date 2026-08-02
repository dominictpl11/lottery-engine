package com.seckiller.lottery.domain.strategy.service.impl;

import com.seckiller.lottery.domain.strategy.model.vo.AwardRateInfo;
import com.seckiller.lottery.domain.strategy.service.IDrawStrategy;
import com.seckiller.lottery.infrastructure.dao.IAwardDao;
import com.seckiller.lottery.infrastructure.dao.IStrategyDao;
import com.seckiller.lottery.infrastructure.dao.IStrategyDetailDao;
import com.seckiller.lottery.infrastructure.po.Strategy;
import com.seckiller.lottery.infrastructure.po.StrategyDetail;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.List;

/**
 * 抽奖策略实现
 */
@Slf4j
@Service
public class DrawStrategyImpl implements IDrawStrategy {
    
    @Resource
    private IStrategyDao strategyDao;
    
    @Resource
    private IStrategyDetailDao strategyDetailDao;
    
    @Resource
    private IAwardDao awardDao;
    
    @Override
    public Strategy queryStrategy(Long strategyId) {
        log.info("查询策略配置，策略ID：{}", strategyId);
        return strategyDao.queryStrategy(strategyId);
    }
    
    @Override
    public List<AwardRateInfo> queryAwardRateInfoList(Long strategyId) {
        log.info("查询奖品概率配置列表，策略ID：{}", strategyId);
        
        List<StrategyDetail> strategyDetailList = strategyDetailDao.queryStrategyDetailList(strategyId);
        List<AwardRateInfo> awardRateInfoList = new ArrayList<>();
        
        for (StrategyDetail strategyDetail : strategyDetailList) {
            // 只返回有库存的奖品
            if (strategyDetail.getAwardSurplusCount() > 0) {
                AwardRateInfo awardRateInfo = new AwardRateInfo();
                awardRateInfo.setAwardId(strategyDetail.getAwardId());
                awardRateInfo.setAwardRate(strategyDetail.getAwardRate());
                awardRateInfoList.add(awardRateInfo);
            }
        }
        
        log.info("查询到{}个有效奖品配置", awardRateInfoList.size());
        return awardRateInfoList;
    }
    
    @Override
    public boolean deductionAwardStock(Long strategyId, String awardId) {
        log.info("扣减奖品库存，策略ID：{}，奖品ID：{}", strategyId, awardId);
        int count = strategyDetailDao.deductionAwardStock(strategyId, awardId);
        return count > 0;
    }
}


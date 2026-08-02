package com.seckiller.lottery.domain.rule.service.engine.impl;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;
import com.seckiller.lottery.domain.rule.service.engine.IRuleEngine;
import com.seckiller.lottery.domain.rule.service.logic.IRuleLogicFilter;
import com.seckiller.lottery.domain.rule.service.logic.impl.ActivityStateRuleFilter;
import com.seckiller.lottery.domain.rule.service.logic.impl.FrequencyRuleFilter;
import com.seckiller.lottery.domain.rule.service.logic.impl.StockRuleFilter;
import com.seckiller.lottery.domain.rule.service.logic.impl.UserQualificationRuleFilter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.Resource;

/**
 * 规则引擎实现
 * 责任链模式：实现多规则链式校验
 */
@Slf4j
@Service
public class RuleEngineImpl implements IRuleEngine {
    
    @Resource
    private ActivityStateRuleFilter activityStateRuleFilter;
    
    @Resource
    private UserQualificationRuleFilter userQualificationRuleFilter;
    
    @Resource
    private StockRuleFilter stockRuleFilter;
    
    @Resource
    private FrequencyRuleFilter frequencyRuleFilter;
    
    /** 责任链头节点 */
    private IRuleLogicFilter ruleChain;
    
    /**
     * 初始化责任链
     * 责任链顺序：活动状态校验 -> 用户资格校验 -> 库存校验 -> 频率校验
     */
    @PostConstruct
    public void initRuleChain() {
        // 构建责任链：活动状态 -> 用户资格 -> 库存 -> 频率
        activityStateRuleFilter.setNext(userQualificationRuleFilter);
        userQualificationRuleFilter.setNext(stockRuleFilter);
        stockRuleFilter.setNext(frequencyRuleFilter);
        
        // 设置责任链头节点
        ruleChain = activityStateRuleFilter;
        
        log.info("规则引擎责任链初始化完成，责任链顺序：活动状态 -> 用户资格 -> 库存 -> 频率");
    }
    
    @Override
    public EngineResult process(DecisionMatterReq matter) {
        log.info("执行规则引擎，规则树ID：{}，用户ID：{}", matter.getTreeId(), matter.getUserId());
        
        try {
            // 使用责任链模式执行规则校验
            EngineResult engineResult = ruleChain.filter(matter);
            
            // 如果所有规则校验通过，设置默认节点信息
            if (engineResult.isSuccess() && engineResult.getNodeId() == null) {
                engineResult.setNodeId(10001L); // 默认节点ID
                if (engineResult.getNodeValue() == null || engineResult.getNodeValue().isEmpty()) {
                    engineResult.setNodeValue("允许参与");
                }
            }
            
            log.info("规则引擎执行完成，结果：{}，节点值：{}", engineResult.isSuccess(), engineResult.getNodeValue());
            return engineResult;
            
        } catch (Exception e) {
            log.error("规则引擎执行异常，规则树ID：{}，用户ID：{}", matter.getTreeId(), matter.getUserId(), e);
            return EngineResult.builder()
                    .isSuccess(false)
                    .userId(matter.getUserId())
                    .treeId(matter.getTreeId())
                    .nodeValue("规则引擎执行异常：" + e.getMessage())
                    .build();
        }
    }
}


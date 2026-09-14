package com.seckiller.lottery.domain.rule.service.logic.impl;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;
import com.seckiller.lottery.domain.rule.service.logic.IRuleLogicFilter;
import lombok.extern.slf4j.Slf4j;

/**
 * 规则逻辑过滤器基类
 * 责任链模式：提供责任链的基础实现
 */
@Slf4j
public abstract class BaseRuleLogicFilter implements IRuleLogicFilter {
    
    /** 下一个规则处理器 */
    private IRuleLogicFilter next;
    
    @Override
    public EngineResult filter(DecisionMatterReq matter) {
        // 执行当前规则校验
        EngineResult engineResult = doFilter(matter);
        
        // 如果当前规则校验失败，直接返回
        if (!engineResult.isSuccess()) {
            log.warn("规则校验失败，处理器：{}，用户ID：{}", getFilterName(), matter.getUserId());
            return engineResult;
        }
        
        // 如果还有下一个处理器，继续执行
        if (next != null) {
            log.debug("规则校验通过，处理器：{}，继续执行下一个处理器", getFilterName());
            return next.filter(matter);
        }
        
        // 所有规则校验通过
        log.info("所有规则校验通过，用户ID：{}", matter.getUserId());
        return engineResult;
    }
    
    /**
     * 执行具体的规则校验逻辑（由子类实现）
     * 
     * @param matter 决策物料
     * @return 规则引擎结果
     */
    protected abstract EngineResult doFilter(DecisionMatterReq matter);
    
    @Override
    public IRuleLogicFilter next() {
        return next;
    }
    
    @Override
    public void setNext(IRuleLogicFilter next) {
        this.next = next;
    }
}


package com.seckiller.lottery.domain.rule.service.logic;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;

/**
 * 规则逻辑过滤器接口
 * 责任链模式：定义规则处理器的标准接口
 */
public interface IRuleLogicFilter {
    
    /**
     * 规则过滤
     * 
     * @param matter 决策物料
     * @return 规则引擎结果
     */
    EngineResult filter(DecisionMatterReq matter);
    
    /**
     * 获取下一个规则处理器
     * 
     * @return 下一个规则处理器
     */
    IRuleLogicFilter next();
    
    /**
     * 设置下一个规则处理器
     * 
     * @param next 下一个规则处理器
     */
    void setNext(IRuleLogicFilter next);
    
    /**
     * 获取规则处理器名称
     * 
     * @return 规则处理器名称
     */
    String getFilterName();
}


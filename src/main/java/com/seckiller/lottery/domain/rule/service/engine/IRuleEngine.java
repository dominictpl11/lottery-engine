package com.seckiller.lottery.domain.rule.service.engine;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;

/**
 * 规则引擎接口
 */
public interface IRuleEngine {
    
    /**
     * 执行规则引擎
     * 
     * @param matter 决策物料
     * @return 决策结果
     */
    EngineResult process(DecisionMatterReq matter);
}


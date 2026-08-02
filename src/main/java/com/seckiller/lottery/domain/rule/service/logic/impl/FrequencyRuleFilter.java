package com.seckiller.lottery.domain.rule.service.logic.impl;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 频率规则过滤器
 * 责任链模式：校验用户参与频率是否超限
 */
@Slf4j
@Component
public class FrequencyRuleFilter extends BaseRuleLogicFilter {
    
    @Override
    protected EngineResult doFilter(DecisionMatterReq matter) {
        log.info("执行频率规则校验，用户ID：{}", matter.getUserId());
        
        // 从决策值中获取用户参与频率信息
        Object frequencyLimitObj = matter.getValMap() != null ? matter.getValMap().get("frequencyLimit") : null;
        Object currentFrequencyObj = matter.getValMap() != null ? matter.getValMap().get("currentFrequency") : null;
        
        if (frequencyLimitObj != null && currentFrequencyObj != null) {
            Integer frequencyLimit = Integer.parseInt(frequencyLimitObj.toString());
            Integer currentFrequency = Integer.parseInt(currentFrequencyObj.toString());
            
            if (currentFrequency >= frequencyLimit) {
                log.warn("用户参与频率超限，用户ID：{}，当前频率：{}，限制频率：{}", 
                        matter.getUserId(), currentFrequency, frequencyLimit);
                return EngineResult.builder()
                        .isSuccess(false)
                        .userId(matter.getUserId())
                        .treeId(matter.getTreeId())
                        .nodeValue("频率校验失败：参与频率超限，当前频率：" + currentFrequency + "，限制频率：" + frequencyLimit)
                        .build();
            }
        }
        
        log.info("频率校验通过，用户ID：{}", matter.getUserId());
        return EngineResult.builder()
                .isSuccess(true)
                .userId(matter.getUserId())
                .treeId(matter.getTreeId())
                .nodeValue("频率校验通过")
                .build();
    }
    
    @Override
    public String getFilterName() {
        return "频率规则过滤器";
    }
}


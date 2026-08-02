package com.seckiller.lottery.domain.rule.service.logic.impl;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 活动状态规则过滤器
 * 责任链模式：校验活动是否在运行状态
 */
@Slf4j
@Component
public class ActivityStateRuleFilter extends BaseRuleLogicFilter {
    
    @Override
    protected EngineResult doFilter(DecisionMatterReq matter) {
        log.info("执行活动状态规则校验，用户ID：{}", matter.getUserId());
        
        // 从决策值中获取活动状态
        Object stateObj = matter.getValMap() != null ? matter.getValMap().get("state") : null;
        
        if (stateObj == null) {
            log.warn("活动状态为空，用户ID：{}", matter.getUserId());
            return EngineResult.builder()
                    .isSuccess(false)
                    .userId(matter.getUserId())
                    .treeId(matter.getTreeId())
                    .nodeValue("活动状态校验失败：活动状态为空")
                    .build();
        }
        
        Integer state = Integer.parseInt(stateObj.toString());
        
        // 5表示活动运行中
        if (state != 5) {
            log.warn("活动未在运行状态，用户ID：{}，状态：{}", matter.getUserId(), state);
            return EngineResult.builder()
                    .isSuccess(false)
                    .userId(matter.getUserId())
                    .treeId(matter.getTreeId())
                    .nodeValue("活动状态校验失败：活动未在运行状态，当前状态：" + state)
                    .build();
        }
        
        log.info("活动状态校验通过，用户ID：{}", matter.getUserId());
        return EngineResult.builder()
                .isSuccess(true)
                .userId(matter.getUserId())
                .treeId(matter.getTreeId())
                .nodeValue("活动状态校验通过")
                .build();
    }
    
    @Override
    public String getFilterName() {
        return "活动状态规则过滤器";
    }
}


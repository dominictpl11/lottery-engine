package com.seckiller.lottery.domain.rule.service.logic.impl;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 用户资格规则过滤器
 * 责任链模式：校验用户是否有参与资格
 */
@Slf4j
@Component
public class UserQualificationRuleFilter extends BaseRuleLogicFilter {
    
    @Override
    protected EngineResult doFilter(DecisionMatterReq matter) {
        log.info("执行用户资格规则校验，用户ID：{}", matter.getUserId());
        
        // 从决策值中获取用户是否被限制参与
        Object isLimitObj = matter.getValMap() != null ? matter.getValMap().get("isLimit") : null;
        
        if (isLimitObj != null && Boolean.parseBoolean(isLimitObj.toString())) {
            log.warn("用户被限制参与，用户ID：{}", matter.getUserId());
            return EngineResult.builder()
                    .isSuccess(false)
                    .userId(matter.getUserId())
                    .treeId(matter.getTreeId())
                    .nodeValue("用户资格校验失败：用户被限制参与")
                    .build();
        }
        
        // 可以扩展更多用户资格校验逻辑
        // 例如：用户等级、用户类型、黑名单等
        
        log.info("用户资格校验通过，用户ID：{}", matter.getUserId());
        return EngineResult.builder()
                .isSuccess(true)
                .userId(matter.getUserId())
                .treeId(matter.getTreeId())
                .nodeValue("用户资格校验通过")
                .build();
    }
    
    @Override
    public String getFilterName() {
        return "用户资格规则过滤器";
    }
}


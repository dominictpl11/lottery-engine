package com.seckiller.lottery.domain.rule.service.logic.impl;

import com.seckiller.lottery.domain.rule.model.req.DecisionMatterReq;
import com.seckiller.lottery.domain.rule.model.res.EngineResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 库存规则过滤器
 * 责任链模式：校验活动库存是否充足
 */
@Slf4j
@Component
public class StockRuleFilter extends BaseRuleLogicFilter {
    
    @Override
    protected EngineResult doFilter(DecisionMatterReq matter) {
        log.info("执行库存规则校验，用户ID：{}", matter.getUserId());
        
        // 从决策值中获取库存信息
        Object stockCountObj = matter.getValMap() != null ? matter.getValMap().get("stockCount") : null;
        
        if (stockCountObj == null) {
            log.warn("库存信息为空，用户ID：{}", matter.getUserId());
            return EngineResult.builder()
                    .isSuccess(false)
                    .userId(matter.getUserId())
                    .treeId(matter.getTreeId())
                    .nodeValue("库存校验失败：库存信息为空")
                    .build();
        }
        
        Integer stockCount = Integer.parseInt(stockCountObj.toString());
        
        if (stockCount <= 0) {
            log.warn("活动库存不足，用户ID：{}，库存：{}", matter.getUserId(), stockCount);
            return EngineResult.builder()
                    .isSuccess(false)
                    .userId(matter.getUserId())
                    .treeId(matter.getTreeId())
                    .nodeValue("库存校验失败：活动库存不足，当前库存：" + stockCount)
                    .build();
        }
        
        log.info("库存校验通过，用户ID：{}，库存：{}", matter.getUserId(), stockCount);
        return EngineResult.builder()
                .isSuccess(true)
                .userId(matter.getUserId())
                .treeId(matter.getTreeId())
                .nodeValue("库存校验通过，当前库存：" + stockCount)
                .build();
    }
    
    @Override
    public String getFilterName() {
        return "库存规则过滤器";
    }
}


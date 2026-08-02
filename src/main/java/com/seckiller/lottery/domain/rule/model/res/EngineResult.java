package com.seckiller.lottery.domain.rule.model.res;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 规则引擎结果
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class EngineResult {
    
    /** 执行结果 */
    private boolean isSuccess;
    
    /** 用户ID */
    private String userId;
    
    /** 规则树ID */
    private Long treeId;
    
    /** 果实节点ID */
    private Long nodeId;
    
    /** 果实节点值 */
    private String nodeValue;
}


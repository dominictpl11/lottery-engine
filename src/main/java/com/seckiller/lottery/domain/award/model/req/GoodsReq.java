package com.seckiller.lottery.domain.award.model.req;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 奖品发放请求
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GoodsReq {
    
    /** 用户ID */
    private String uId;
    
    /** 活动ID */
    private Long activityId;
    
    /** 奖品ID */
    private String awardId;
    
    /** 奖品类型（1:文字描述、2:兑换码、3:优惠券、4:实物奖品） */
    private Integer awardType;
    
    /** 奖品名称 */
    private String awardName;
    
    /** 奖品内容 */
    private String awardContent;
    
    /** 订单ID */
    private Long orderId;
}


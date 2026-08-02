package com.seckiller.lottery.infrastructure.po;

import lombok.Data;

import java.util.Date;

/**
 * 活动表
 */
@Data
public class Activity {
    
    /** 自增ID */
    private Long id;
    
    /** 活动ID */
    private Long activityId;
    
    /** 活动名称 */
    private String activityName;
    
    /** 活动描述 */
    private String activityDesc;
    
    /** 开始时间 */
    private Date beginDateTime;
    
    /** 结束时间 */
    private Date endDateTime;
    
    /** 库存 */
    private Integer stockCount;
    
    /** 每人可参与次数 */
    private Integer takeCount;
    
    /** 活动状态：1编辑、2提审、3撤审、4通过、5运行(审核通过后worker扫描状态)、6拒绝、7关闭、8开启 */
    private Integer state;
    
    /** 创建人 */
    private String creator;
    
    /** 创建时间 */
    private Date createTime;
    
    /** 修改时间 */
    private Date updateTime;
}


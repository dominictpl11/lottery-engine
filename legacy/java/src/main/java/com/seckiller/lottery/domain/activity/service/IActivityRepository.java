package com.seckiller.lottery.domain.activity.service;

import com.seckiller.lottery.domain.activity.model.aggregates.ActivityConfigRich;

/**
 * 活动仓储接口
 */
public interface IActivityRepository {
    
    /**
     * 查询活动配置聚合对象
     * 
     * @param activityId 活动ID
     * @return 活动配置聚合对象
     */
    ActivityConfigRich queryActivityConfig(Long activityId);
}


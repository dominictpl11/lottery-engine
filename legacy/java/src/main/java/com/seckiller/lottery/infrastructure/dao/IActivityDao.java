package com.seckiller.lottery.infrastructure.dao;

import com.seckiller.lottery.infrastructure.po.Activity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 活动表DAO
 */
@Mapper
public interface IActivityDao {
    
    /**
     * 查询活动信息
     * 
     * @param activityId 活动ID
     * @return 活动信息
     */
    Activity queryActivityById(@Param("activityId") Long activityId);
    
    /**
     * 扣减活动库存
     * 
     * @param activityId 活动ID
     * @return 更新行数
     */
    int subtractionActivityStock(@Param("activityId") Long activityId);
}


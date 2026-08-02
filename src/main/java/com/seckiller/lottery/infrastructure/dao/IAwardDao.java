package com.seckiller.lottery.infrastructure.dao;

import com.seckiller.lottery.infrastructure.po.Award;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 奖品表DAO
 */
@Mapper
public interface IAwardDao {
    
    /**
     * 查询奖品信息
     * 
     * @param awardId 奖品ID
     * @return 奖品信息
     */
    Award queryAwardInfo(@Param("awardId") String awardId);
}


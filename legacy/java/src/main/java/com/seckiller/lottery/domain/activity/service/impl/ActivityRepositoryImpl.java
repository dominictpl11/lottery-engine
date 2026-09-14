package com.seckiller.lottery.domain.activity.service.impl;

import com.seckiller.lottery.domain.activity.model.aggregates.ActivityConfigRich;
import com.seckiller.lottery.domain.activity.model.vo.ActivityInfoVO;
import com.seckiller.lottery.domain.activity.model.vo.AwardInfoVO;
import com.seckiller.lottery.domain.activity.model.vo.StrategyDetailVO;
import com.seckiller.lottery.domain.activity.service.IActivityRepository;
import com.seckiller.lottery.infrastructure.dao.IActivityDao;
import com.seckiller.lottery.infrastructure.dao.IAwardDao;
import com.seckiller.lottery.infrastructure.dao.IStrategyDetailDao;
import com.seckiller.lottery.infrastructure.po.Activity;
import com.seckiller.lottery.infrastructure.po.Award;
import com.seckiller.lottery.infrastructure.po.StrategyDetail;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.List;

/**
 * 活动仓储实现
 */
@Slf4j
@Service
public class ActivityRepositoryImpl implements IActivityRepository {
    
    @Resource
    private IActivityDao activityDao;
    
    @Resource
    private IStrategyDetailDao strategyDetailDao;
    
    @Resource
    private IAwardDao awardDao;
    
    @Override
    public ActivityConfigRich queryActivityConfig(Long activityId) {
        log.info("查询活动配置，活动ID：{}", activityId);
        
        // 1. 查询活动信息
        Activity activity = activityDao.queryActivityById(activityId);
        if (activity == null) {
            log.warn("活动信息不存在，活动ID：{}", activityId);
            return null;
        }
        
        ActivityInfoVO activityInfo = convertActivityInfo(activity);
        
        // 2. 查询策略明细（这里简化处理，实际应该通过活动关联策略）
        // 假设活动ID就是策略ID
        Long strategyId = activityId;
        List<StrategyDetail> strategyDetailList = strategyDetailDao.queryStrategyDetailList(strategyId);
        List<StrategyDetailVO> strategyDetailVOList = new ArrayList<>();
        
        for (StrategyDetail strategyDetail : strategyDetailList) {
            StrategyDetailVO strategyDetailVO = new StrategyDetailVO();
            strategyDetailVO.setStrategyId(strategyDetail.getStrategyId());
            strategyDetailVO.setAwardId(strategyDetail.getAwardId());
            strategyDetailVO.setAwardName(strategyDetail.getAwardName());
            strategyDetailVO.setAwardCount(strategyDetail.getAwardCount());
            strategyDetailVO.setAwardSurplusCount(strategyDetail.getAwardSurplusCount());
            strategyDetailVO.setAwardRate(strategyDetail.getAwardRate());
            strategyDetailVO.setSort(strategyDetail.getSort());
            strategyDetailVOList.add(strategyDetailVO);
        }
        
        // 3. 查询奖品信息
        List<AwardInfoVO> awardList = new ArrayList<>();
        for (StrategyDetailVO strategyDetailVO : strategyDetailVOList) {
            Award award = awardDao.queryAwardInfo(strategyDetailVO.getAwardId());
            if (award != null) {
                AwardInfoVO awardInfoVO = new AwardInfoVO();
                awardInfoVO.setAwardId(award.getAwardId());
                awardInfoVO.setAwardType(award.getAwardType());
                awardInfoVO.setAwardName(award.getAwardName());
                awardInfoVO.setAwardContent(award.getAwardContent());
                awardList.add(awardInfoVO);
            }
        }
        
        // 4. 封装聚合对象
        ActivityConfigRich activityConfigRich = new ActivityConfigRich();
        activityConfigRich.setActivityInfo(activityInfo);
        activityConfigRich.setStrategyDetailList(strategyDetailVOList);
        activityConfigRich.setAwardList(awardList);
        
        log.info("查询活动配置完成，活动ID：{}", activityId);
        return activityConfigRich;
    }
    
    /**
     * 转换活动信息
     */
    private ActivityInfoVO convertActivityInfo(Activity activity) {
        ActivityInfoVO activityInfo = new ActivityInfoVO();
        activityInfo.setActivityId(activity.getActivityId());
        activityInfo.setActivityName(activity.getActivityName());
        activityInfo.setActivityDesc(activity.getActivityDesc());
        activityInfo.setBeginDateTime(activity.getBeginDateTime());
        activityInfo.setEndDateTime(activity.getEndDateTime());
        activityInfo.setStockCount(activity.getStockCount());
        activityInfo.setTakeCount(activity.getTakeCount());
        activityInfo.setState(activity.getState());
        activityInfo.setCreator(activity.getCreator());
        activityInfo.setCreateTime(activity.getCreateTime());
        activityInfo.setUpdateTime(activity.getUpdateTime());
        return activityInfo;
    }
}


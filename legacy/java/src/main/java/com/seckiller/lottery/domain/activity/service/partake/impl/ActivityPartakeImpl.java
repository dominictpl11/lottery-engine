package com.seckiller.lottery.domain.activity.service.partake.impl;

import com.seckiller.lottery.common.RedisKey;
import com.seckiller.lottery.domain.activity.model.aggregates.ActivityConfigRich;
import com.seckiller.lottery.domain.activity.model.req.PartakeReq;
import com.seckiller.lottery.domain.activity.model.res.PartakeResult;
import com.seckiller.lottery.domain.activity.service.IActivityRepository;
import com.seckiller.lottery.domain.activity.service.partake.IActivityPartake;
import com.seckiller.lottery.infrastructure.util.RedisUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;

/**
 * 活动参与实现
 * 使用滑动窗口锁优化高并发场景
 */
@Slf4j
@Service
public class ActivityPartakeImpl implements IActivityPartake {
    
    @Resource
    private RedisUtil redisUtil;
    
    @Resource
    private IActivityRepository activityRepository;
    
    /** 滑动窗口大小（秒） */
    private static final int SLIDING_WINDOW_SIZE = 60;
    
    /** 滑动窗口内最大请求次数 */
    private static final int MAX_REQUEST_COUNT = 10;
    
    @Override
    public PartakeResult doPartake(PartakeReq req) {
        log.info("用户参与活动，用户ID：{}，活动ID：{}", req.getUId(), req.getActivityId());
        
        // 1. 查询活动配置
        ActivityConfigRich activityConfigRich = activityRepository.queryActivityConfig(req.getActivityId());
        if (activityConfigRich == null || activityConfigRich.getActivityInfo() == null) {
            log.warn("活动配置不存在，活动ID：{}", req.getActivityId());
            PartakeResult result = new PartakeResult();
            result.setCode("0001");
            result.setInfo("活动配置不存在");
            return result;
        }
        
        // 2. 校验活动状态
        Integer state = activityConfigRich.getActivityInfo().getState();
        if (state == null || state != 5) { // 5表示运行中
            log.warn("活动未在运行状态，活动ID：{}，状态：{}", req.getActivityId(), state);
            PartakeResult result = new PartakeResult();
            result.setCode("0002");
            result.setInfo("活动未在运行状态");
            return result;
        }
        
        // 3. 滑动窗口锁校验（防止同一用户在短时间内重复参与）
        String lockKey = RedisKey.getSlidingWindowLockKey(req.getActivityId(), req.getUId());
        boolean lockAcquired = redisUtil.slidingWindowLock(lockKey, SLIDING_WINDOW_SIZE, MAX_REQUEST_COUNT);
        
        if (!lockAcquired) {
            log.warn("用户参与活动频率过高，用户ID：{}，活动ID：{}", req.getUId(), req.getActivityId());
            PartakeResult result = new PartakeResult();
            result.setCode("0003");
            result.setInfo("参与活动频率过高，请稍后再试");
            return result;
        }
        
        // 4. 检查库存（使用Redis原子操作）
        String stockKey = RedisKey.getActivityStockCountSurplusKey(req.getActivityId());
        Object stockObj = redisUtil.get(stockKey);
        
        Integer stockCount;
        if (stockObj == null) {
            // 如果Redis中没有库存信息，从活动配置加载
            stockCount = activityConfigRich.getActivityInfo().getStockCount();
            if (stockCount == null || stockCount <= 0) {
                log.warn("活动库存不足，活动ID：{}", req.getActivityId());
                PartakeResult result = new PartakeResult();
                result.setCode("0004");
                result.setInfo("活动库存不足");
                return result;
            }
            // 初始化到Redis
            redisUtil.set(stockKey, stockCount);
        } else {
            stockCount = Integer.parseInt(stockObj.toString());
        }
        
        if (stockCount <= 0) {
            log.warn("活动库存不足，活动ID：{}", req.getActivityId());
            PartakeResult result = new PartakeResult();
            result.setCode("0004");
            result.setInfo("活动库存不足");
            return result;
        }
        
        // 5. 扣减库存（使用Redis原子操作）
        Long decrementResult = redisUtil.decrement(stockKey);
        if (decrementResult < 0) {
            // 如果扣减后小于0，回滚
            redisUtil.increment(stockKey);
            log.warn("活动库存扣减失败，活动ID：{}", req.getActivityId());
            PartakeResult result = new PartakeResult();
            result.setCode("0005");
            result.setInfo("活动库存扣减失败");
            return result;
        }
        
        // 6. 记录用户参与信息
        String userTakeKey = RedisKey.getUserTakeActivityKey(req.getActivityId(), req.getUId());
        redisUtil.set(userTakeKey, System.currentTimeMillis(), 24, java.util.concurrent.TimeUnit.HOURS);
        
        // 7. 返回参与结果
        PartakeResult result = new PartakeResult();
        result.setCode("0000");
        result.setInfo("参与活动成功");
        result.setStockCount(stockCount);
        result.setStockSurplusCount(decrementResult.intValue());
        // 从策略明细中获取策略ID（简化处理，假设活动ID就是策略ID）
        result.setStrategyId(req.getActivityId());
        
        log.info("用户参与活动成功，用户ID：{}，活动ID：{}，剩余库存：{}", 
            req.getUId(), req.getActivityId(), decrementResult);
        
        return result;
    }
    
    @Override
    public boolean recordDrawOrder(Long activityId, String uId, String awardId) {
        log.info("记录奖品单，活动ID：{}，用户ID：{}，奖品ID：{}", activityId, uId, awardId);
        // 实际实现中应该保存到数据库
        return true;
    }
}


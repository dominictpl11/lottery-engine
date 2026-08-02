package com.seckiller.lottery.common;

/**
 * Redis Key 常量类
 */
public class RedisKey {
    
    /** 活动库存Key */
    private static final String ACTIVITY_STOCK_COUNT = "activity_stock_count_";
    
    /** 活动库存消耗Key */
    private static final String ACTIVITY_STOCK_COUNT_SURPLUS = "activity_stock_count_surplus_";
    
    /** 用户参与活动Key */
    private static final String USER_TAKE_ACTIVITY = "user_take_activity_";
    
    /** 滑动窗口锁Key */
    private static final String SLIDING_WINDOW_LOCK = "sliding_window_lock_";
    
    public static String getActivityStockCountKey(Long activityId) {
        return ACTIVITY_STOCK_COUNT + activityId;
    }
    
    public static String getActivityStockCountSurplusKey(Long activityId) {
        return ACTIVITY_STOCK_COUNT_SURPLUS + activityId;
    }
    
    public static String getUserTakeActivityKey(Long activityId, String uId) {
        return USER_TAKE_ACTIVITY + activityId + "_" + uId;
    }
    
    public static String getSlidingWindowLockKey(Long activityId, String uId) {
        return SLIDING_WINDOW_LOCK + activityId + "_" + uId;
    }
}


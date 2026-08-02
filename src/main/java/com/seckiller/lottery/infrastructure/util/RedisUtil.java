package com.seckiller.lottery.infrastructure.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

/**
 * Redis工具类
 */
@Slf4j
@Component
public class RedisUtil {
    
    @Resource
    private RedisTemplate<String, Object> redisTemplate;
    
    /**
     * 设置值
     */
    public void set(String key, Object value) {
        redisTemplate.opsForValue().set(key, value);
    }
    
    /**
     * 设置值（带过期时间）
     */
    public void set(String key, Object value, long timeout, TimeUnit unit) {
        redisTemplate.opsForValue().set(key, value, timeout, unit);
    }
    
    /**
     * 获取值
     */
    public Object get(String key) {
        return redisTemplate.opsForValue().get(key);
    }
    
    /**
     * 删除键
     */
    public Boolean delete(String key) {
        return redisTemplate.delete(key);
    }
    
    /**
     * 自增
     */
    public Long increment(String key) {
        return redisTemplate.opsForValue().increment(key);
    }
    
    /**
     * 自减
     */
    public Long decrement(String key) {
        return redisTemplate.opsForValue().decrement(key);
    }
    
    /**
     * 滑动窗口锁
     * 使用Redis实现滑动窗口限流，防止同一用户在短时间内重复参与
     * 
     * @param key 锁的key
     * @param windowSize 窗口大小（秒）
     * @param maxCount 最大请求次数
     * @return true-获取锁成功，false-获取锁失败
     */
    public boolean slidingWindowLock(String key, int windowSize, int maxCount) {
        try {
            String luaScript = 
                "local key = KEYS[1] " +
                "local window = tonumber(ARGV[1]) " +
                "local max = tonumber(ARGV[2]) " +
                "local now = tonumber(ARGV[3]) " +
                "local clearBefore = now - window " +
                "redis.call('ZREMRANGEBYSCORE', key, 0, clearBefore) " +
                "local current = redis.call('ZCARD', key) " +
                "if current < max then " +
                "    redis.call('ZADD', key, now, now) " +
                "    redis.call('EXPIRE', key, window) " +
                "    return 1 " +
                "else " +
                "    return 0 " +
                "end";
            
            DefaultRedisScript<Long> script = new DefaultRedisScript<>();
            script.setScriptText(luaScript);
            script.setResultType(Long.class);
            
            Long result = redisTemplate.execute(script, 
                Collections.singletonList(key), 
                String.valueOf(windowSize), 
                String.valueOf(maxCount), 
                String.valueOf(System.currentTimeMillis() / 1000));
            
            return result != null && result == 1;
        } catch (Exception e) {
            log.error("滑动窗口锁执行失败，key：{}", key, e);
            return false;
        }
    }
    
    @Resource
    private org.redisson.api.RedissonClient redissonClient;
    
    /**
     * 分布式锁（使用Redisson实现）
     * 
     * @param key 锁的key
     * @param waitTime 等待获取锁的时间
     * @param leaseTime 锁的持有时间
     * @param unit 时间单位
     * @return true-获取锁成功，false-获取锁失败
     */
    public boolean tryLock(String key, long waitTime, long leaseTime, TimeUnit unit) {
        try {
            org.redisson.api.RLock lock = redissonClient.getLock(key);
            boolean acquired = lock.tryLock(waitTime, leaseTime, unit);
            if (acquired) {
                log.info("获取分布式锁成功，key：{}", key);
            } else {
                log.warn("获取分布式锁失败，key：{}", key);
            }
            return acquired;
        } catch (InterruptedException e) {
            log.error("获取分布式锁被中断，key：{}", key, e);
            Thread.currentThread().interrupt();
            return false;
        } catch (Exception e) {
            log.error("获取分布式锁异常，key：{}", key, e);
            return false;
        }
    }
    
    /**
     * 释放锁
     * 
     * @param key 锁的key
     */
    public void unlock(String key) {
        try {
            org.redisson.api.RLock lock = redissonClient.getLock(key);
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
                log.info("释放分布式锁成功，key：{}", key);
            } else {
                log.warn("当前线程未持有锁，无法释放，key：{}", key);
            }
        } catch (Exception e) {
            log.error("释放分布式锁异常，key：{}", key, e);
        }
    }
    
    /**
     * 尝试获取锁（不等待）
     * 
     * @param key 锁的key
     * @param leaseTime 锁的持有时间
     * @param unit 时间单位
     * @return true-获取锁成功，false-获取锁失败
     */
    public boolean tryLock(String key, long leaseTime, TimeUnit unit) {
        try {
            org.redisson.api.RLock lock = redissonClient.getLock(key);
            boolean acquired = lock.tryLock(leaseTime, unit);
            if (acquired) {
                log.info("获取分布式锁成功，key：{}", key);
            } else {
                log.warn("获取分布式锁失败，key：{}", key);
            }
            return acquired;
        } catch (Exception e) {
            log.error("获取分布式锁异常，key：{}", key, e);
            return false;
        }
    }
    
    /**
     * 强制释放锁（谨慎使用）
     * 
     * @param key 锁的key
     */
    public void forceUnlock(String key) {
        try {
            org.redisson.api.RLock lock = redissonClient.getLock(key);
            lock.forceUnlock();
            log.info("强制释放分布式锁，key：{}", key);
        } catch (Exception e) {
            log.error("强制释放分布式锁异常，key：{}", key, e);
        }
    }
}


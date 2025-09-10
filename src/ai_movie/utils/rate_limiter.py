"""
API调用限流控制模块

实现智能的API调用频率控制和重试机制，解决DashScope API限流问题。
"""
import time
import asyncio
import threading
from typing import Optional, Dict, Any, Callable
from functools import wraps
from dataclasses import dataclass
from collections import defaultdict, deque

from ..core.exceptions import APIException, DashScopeAPIException
from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """限流配置"""
    max_calls_per_minute: int = 20  # 每分钟最大调用次数
    max_calls_per_second: int = 2   # 每秒最大调用次数
    min_interval: float = 0.5       # 最小调用间隔(秒)
    max_retries: int = 5           # 最大重试次数
    base_delay: float = 1.0        # 基础退避延迟(秒)
    max_delay: float = 60.0        # 最大退避延迟(秒)
    backoff_factor: float = 2.0    # 退避因子


class TokenBucket:
    """令牌桶算法实现"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        初始化令牌桶
        
        Args:
            capacity: 桶容量
            refill_rate: 令牌生成速率(每秒)
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        尝试获取令牌
        
        Args:
            tokens: 需要的令牌数量
            
        Returns:
            bool: 是否成功获取令牌
        """
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        tokens_to_add = (now - self.last_refill) * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class APIRateLimiter:
    """API调用限流器"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # 创建不同粒度的令牌桶
        self.minute_bucket = TokenBucket(
            capacity=self.config.max_calls_per_minute,
            refill_rate=self.config.max_calls_per_minute / 60.0
        )
        self.second_bucket = TokenBucket(
            capacity=self.config.max_calls_per_second,
            refill_rate=self.config.max_calls_per_second
        )
        
        # 记录最后调用时间
        self._last_call_time = 0
        self._call_times = deque()  # 记录调用时间用于统计
        self._lock = threading.Lock()
        
        logger.info(f"API限流器初始化: {self.config}")
    
    def acquire(self, timeout: float = 30.0) -> bool:
        """
        获取调用许可
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            bool: 是否获得许可
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查最小间隔
            with self._lock:
                now = time.time()
                time_since_last_call = now - self._last_call_time
                
                if time_since_last_call < self.config.min_interval:
                    sleep_time = self.config.min_interval - time_since_last_call
                    time.sleep(sleep_time)
                    now = time.time()
                
                # 尝试获取令牌
                if (self.minute_bucket.acquire() and 
                    self.second_bucket.acquire()):
                    self._last_call_time = now
                    self._record_call_time(now)
                    return True
            
            # 没有获得许可，等待一段时间再试
            time.sleep(0.1)
        
        return False
    
    def _record_call_time(self, call_time: float):
        """记录调用时间"""
        self._call_times.append(call_time)
        # 只保留最近1分钟的记录
        cutoff_time = call_time - 60
        while self._call_times and self._call_times[0] < cutoff_time:
            self._call_times.popleft()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取限流统计信息"""
        now = time.time()
        with self._lock:
            # 清理过期记录
            cutoff_time = now - 60
            while self._call_times and self._call_times[0] < cutoff_time:
                self._call_times.popleft()
            
            return {
                'calls_last_minute': len(self._call_times),
                'minute_bucket_tokens': self.minute_bucket.tokens,
                'second_bucket_tokens': self.second_bucket.tokens,
                'last_call_time': self._last_call_time,
                'config': self.config
            }


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        logger.info(f"重试处理器初始化: {self.config}")
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            error: 异常对象
            attempt: 当前尝试次数
            
        Returns:
            bool: 是否应该重试
        """
        if attempt >= self.config.max_retries:
            return False
        
        error_msg = str(error).lower()
        
        # 检查是否是可重试的错误
        retryable_errors = [
            'rate limit',
            'throttling',
            'quota',
            'too many requests',
            'timeout',
            '429',
            'service unavailable',
            '503',
            'connection',
            'network'
        ]
        
        return any(keyword in error_msg for keyword in retryable_errors)
    
    def get_delay(self, attempt: int, error: Exception) -> float:
        """
        计算退避延迟时间
        
        Args:
            attempt: 当前尝试次数
            error: 异常对象
            
        Returns:
            float: 延迟时间(秒)
        """
        error_msg = str(error).lower()
        
        # 根据错误类型调整延迟
        if 'rate limit' in error_msg or 'throttling' in error_msg:
            # 限流错误使用较长延迟
            base_delay = self.config.base_delay * 2
        elif 'timeout' in error_msg or 'network' in error_msg:
            # 网络错误使用中等延迟
            base_delay = self.config.base_delay
        else:
            # 其他错误使用较短延迟
            base_delay = self.config.base_delay * 0.5
        
        # 指数退避
        delay = base_delay * (self.config.backoff_factor ** (attempt - 1))
        
        # 添加随机抖动，避免雷群效应
        import random
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter
        
        return min(delay, self.config.max_delay)


# 全局限流器实例
_global_rate_limiter: Optional[APIRateLimiter] = None
_global_retry_handler: Optional[RetryHandler] = None


def get_rate_limiter() -> APIRateLimiter:
    """获取全局限流器实例"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = APIRateLimiter()
    return _global_rate_limiter


def get_retry_handler() -> RetryHandler:
    """获取全局重试处理器实例"""
    global _global_retry_handler
    if _global_retry_handler is None:
        _global_retry_handler = RetryHandler()
    return _global_retry_handler


def with_rate_limit(func: Optional[Callable] = None, *, 
                   timeout: float = 30.0,
                   enable_retry: bool = True) -> Callable:
    """
    API调用限流装饰器
    
    Args:
        func: 被装饰的函数
        timeout: 获取许可的超时时间
        enable_retry: 是否启用重试
        
    Returns:
        装饰后的函数
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            rate_limiter = get_rate_limiter()
            retry_handler = get_retry_handler()
            
            attempt = 0
            last_error = None
            
            while attempt < retry_handler.config.max_retries:
                attempt += 1
                
                try:
                    # 获取调用许可
                    if not rate_limiter.acquire(timeout=timeout):
                        raise APIException(
                            "API调用限流超时",
                            error_code="RATE_LIMIT_TIMEOUT",
                            details={'timeout': timeout}
                        )
                    
                    # 执行原函数
                    result = f(*args, **kwargs)
                    
                    # 记录成功调用
                    logger.debug(f"API调用成功: {f.__name__}, 尝试次数: {attempt}")
                    return result
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"API调用失败: {f.__name__}, 尝试次数: {attempt}, 错误: {e}")
                    
                    if not enable_retry or not retry_handler.should_retry(e, attempt):
                        break
                    
                    if attempt < retry_handler.config.max_retries:
                        delay = retry_handler.get_delay(attempt, e)
                        logger.info(f"等待 {delay:.2f} 秒后重试...")
                        time.sleep(delay)
            
            # 所有重试都失败了
            if isinstance(last_error, (APIException, DashScopeAPIException)):
                raise last_error
            else:
                raise DashScopeAPIException(
                    f"API调用失败，已重试 {attempt} 次: {str(last_error)}",
                    error_code="API_CALL_FAILED_AFTER_RETRIES",
                    details={'attempts': attempt, 'last_error': str(last_error)}
                )
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def configure_rate_limiting(max_calls_per_minute: int = 10,
                          max_calls_per_second: int = 1,
                          min_interval: float = 1.0,
                          max_retries: int = 3) -> None:
    """
    配置API限流参数
    
    Args:
        max_calls_per_minute: 每分钟最大调用次数
        max_calls_per_second: 每秒最大调用次数
        min_interval: 最小调用间隔(秒)
        max_retries: 最大重试次数
    """
    global _global_rate_limiter, _global_retry_handler
    
    config = RateLimitConfig(
        max_calls_per_minute=max_calls_per_minute,
        max_calls_per_second=max_calls_per_second,
        min_interval=min_interval,
        max_retries=max_retries
    )
    
    _global_rate_limiter = APIRateLimiter(config)
    _global_retry_handler = RetryHandler(config)
    
    logger.info(f"API限流配置已更新: {config}")
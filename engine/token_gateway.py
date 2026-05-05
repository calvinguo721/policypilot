"""
API网关
统一入口、API Key鉴权、限流、请求日志
"""
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from functools import wraps
from collections import defaultdict
import threading

from customers import (
    verify_api_key, 
    get_customer_by_api_key,
    get_db_connection
)
from billing import (
    log_api_usage,
    get_rate_limit_usage,
    calculate_cost
)


class RateLimiter:
    """基于滑动窗口的限流器"""
    
    def __init__(self):
        self._windows: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> Dict[str, Any]:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - window_seconds
        
        with self._lock:
            # 清理过期记录
            self._windows[key] = [
                ts for ts in self._windows[key] 
                if ts > window_start
            ]
            
            current_count = len(self._windows[key])
            
            if current_count >= limit:
                return {
                    "allowed": False,
                    "current": current_count,
                    "limit": limit,
                    "retry_after": int(self._windows[key][0] + window_seconds - now) + 1
                }
            
            # 记录新请求
            self._windows[key].append(now)
            
            return {
                "allowed": True,
                "current": current_count + 1,
                "limit": limit,
                "remaining": limit - current_count - 1
            }


# 全局限流器实例
rate_limiter = RateLimiter()


class TokenGateway:
    """Token API 网关"""
    
    def __init__(self):
        self.version = "v1"
        self.name = "PolicyPilot Token Gateway"
    
    def authenticate(self, api_key: str) -> Dict[str, Any]:
        """认证API Key"""
        if not api_key:
            return {
                "success": False,
                "error": "missing_api_key",
                "message": "请提供API Key"
            }
        
        # 验证格式
        if not api_key.startswith("pp_live_"):
            return {
                "success": False,
                "error": "invalid_api_key_format",
                "message": "API Key格式无效，应以 pp_live_ 开头"
            }
        
        # 验证有效性
        result = verify_api_key(api_key)
        
        if not result["valid"]:
            return {
                "success": False,
                "error": "invalid_api_key",
                "message": result["message"],
                "balance": result.get("balance")
            }
        
        return {
            "success": True,
            "customer_id": result["customer_id"],
            "customer_name": result["customer_name"],
            "balance": result["balance"],
            "rate_limit": result["rate_limit"]
        }
    
    def check_rate_limit(self, customer_id: int, rate_limit: int) -> Dict[str, Any]:
        """检查限流"""
        key = f"customer_{customer_id}"
        return rate_limiter.is_allowed(key, rate_limit, window_seconds=60)
    
    def execute_with_auth(
        self, 
        api_key: str, 
        query_type: str = "basic",
        endpoint: str = None
    ) -> Callable:
        """装饰器：验证API Key和限流"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 1. 认证
                auth_result = self.authenticate(api_key)
                if not auth_result["success"]:
                    return {
                        "success": False,
                        "error": auth_result["error"],
                        "message": auth_result["message"]
                    }, 401
                
                customer_id = auth_result["customer_id"]
                
                # 2. 限流检查
                rate_result = self.check_rate_limit(
                    customer_id, 
                    auth_result["rate_limit"]
                )
                
                if not rate_result["allowed"]:
                    return {
                        "success": False,
                        "error": "rate_limit_exceeded",
                        "message": f"请求过于频繁，请{rate_result['retry_after']}秒后重试",
                        "retry_after": rate_result["retry_after"]
                    }, 429
                
                # 3. 余额检查
                cost = calculate_cost(query_type)
                if auth_result["balance"] < cost:
                    return {
                        "success": False,
                        "error": "insufficient_balance",
                        "message": f"余额不足，当前余额{auth_result['balance']}元，查询费用{cost}元",
                        "balance": auth_result["balance"],
                        "required": cost
                    }, 402
                
                # 记录开始时间
                start_time = time.time()
                
                # 执行请求
                result = await func(
                    *args, 
                    customer_id=customer_id,
                    customer_name=auth_result["customer_name"],
                    **kwargs
                )
                
                # 计算耗时
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # 4. 记录日志（异步或同步）
                try:
                    log_api_usage(
                        customer_id=customer_id,
                        api_key=api_key,
                        endpoint=endpoint or func.__name__,
                        query_type=query_type,
                        result_count=result.get("total_matches", 0) if isinstance(result, dict) else 0,
                        response_time_ms=response_time_ms
                    )
                except Exception as e:
                    print(f"⚠️ 记录日志失败: {e}")
                
                return result, 200
            
            return wrapper
        return decorator
    
    def get_request_info(self, api_key: str) -> Dict[str, Any]:
        """获取请求信息"""
        auth = self.authenticate(api_key)
        if not auth["success"]:
            return auth
        
        customer_id = auth["customer_id"]
        rate_info = get_rate_limit_usage(customer_id)
        
        return {
            "authenticated": True,
            "customer_id": customer_id,
            "customer_name": auth["customer_name"],
            "balance": auth["balance"],
            "rate_limit": auth["rate_limit"],
            "usage": rate_info
        }


# 全局网关实例
gateway = TokenGateway()


def require_token_auth(query_type: str = "basic", endpoint: str = None):
    """API Key认证装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            # 从请求头获取API Key
            api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
            
            if not api_key:
                return {
                    "success": False,
                    "error": "missing_api_key",
                    "message": "请在请求头中提供 X-API-Key"
                }
            
            # 认证
            auth_result = gateway.authenticate(api_key)
            if not auth_result["success"]:
                return auth_result
            
            customer_id = auth_result["customer_id"]
            
            # 限流检查
            rate_result = gateway.check_rate_limit(
                customer_id, 
                auth_result["rate_limit"]
            )
            
            if not rate_result["allowed"]:
                return {
                    "success": False,
                    "error": "rate_limit_exceeded",
                    "message": f"请求过于频繁，请{rate_result['retry_after']}秒后重试",
                    "retry_after": rate_result["retry_after"]
                }
            
            # 余额检查
            cost = calculate_cost(query_type)
            if auth_result["balance"] < cost:
                return {
                    "success": False,
                    "error": "insufficient_balance",
                    "message": f"余额不足，当前余额{auth_result['balance']}元，查询费用{cost}元",
                    "balance": auth_result["balance"],
                    "required": cost
                }
            
            # 记录开始时间
            start_time = time.time()
            
            # 获取IP
            client_ip = request.client.host if request.client else None
            
            # 调用原函数
            result = await func(request, *args, **kwargs)
            
            # 计算耗时
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 记录日志
            try:
                result_count = 0
                if isinstance(result, dict) and "matched_policies" in result:
                    result_count = len(result.get("matched_policies", []))
                elif isinstance(result, dict) and "total_matches" in result:
                    result_count = result.get("total_matches", 0)
                
                log_api_usage(
                    customer_id=customer_id,
                    api_key=api_key,
                    endpoint=endpoint or request.url.path,
                    query_type=query_type,
                    params=json.dumps(request.__dict__.get("query_params", {})),
                    result_count=result_count,
                    response_time_ms=response_time_ms,
                    ip_address=client_ip
                )
            except Exception as e:
                print(f"⚠️ 记录日志失败: {e}")
            
            return result
        
        return wrapper
    return decorator


def get_client_ip(request) -> Optional[str]:
    """获取客户端IP"""
    # 优先从代理头获取
    for header in ["X-Forwarded-For", "X-Real-IP", "X-Client-IP"]:
        ip = request.headers.get(header)
        if ip:
            return ip.split(",")[0].strip()
    
    if request.client:
        return request.client.host
    
    return None

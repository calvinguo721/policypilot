"""
计费系统
Token API的定价和扣费逻辑
"""
from typing import Dict, Any, Optional
from enum import Enum


class OperationType(Enum):
    """操作类型枚举"""
    BASIC_QUERY = "basic_query"           # 基础查询 - 0.1元
    ADVANCED_QUERY = "advanced_query"      # 高级查询(AI解读) - 0.5元
    BATCH_QUERY = "batch_query"            # 批量查询 - 0.05元/条
    POLICY_DETAIL = "policy_detail"        # 政策详情 - 0.02元


class PricingConfig:
    """定价配置"""
    
    # 各操作类型的价格
    PRICES = {
        OperationType.BASIC_QUERY: 0.1,         # 基础查询 0.1元
        OperationType.ADVANCED_QUERY: 0.5,     # 高级查询 0.5元
        OperationType.BATCH_QUERY: 0.05,       # 批量查询 0.05元/条
        OperationType.POLICY_DETAIL: 0.02,     # 政策详情 0.02元
    }
    
    # 免费配额配置
    FREE_TIER = {
        "daily_basic_queries": 0,      # 每日免费基础查询次数
        "daily_advanced_queries": 0,   # 每日免费高级查询次数
    }
    
    # 限流配置
    RATE_LIMITS = {
        "basic": {"requests": 100, "window": 60},      # 100次/分钟
        "advanced": {"requests": 20, "window": 60},    # 20次/分钟
        "daily_limit": {"requests": 1000, "window": 86400},  # 1000次/天
    }
    
    # 最低余额警告阈值
    LOW_BALANCE_THRESHOLD = 10.0
    
    # 余额不足阈值(拒绝服务)
    MINIMUM_BALANCE = 0.1


class BillingService:
    """计费服务"""
    
    def __init__(self):
        self.pricing = PricingConfig()
    
    def get_price(self, operation_type: OperationType) -> float:
        """获取操作价格"""
        return self.pricing.PRICES.get(operation_type, 0.0)
    
    def calculate_cost(self, operation_type: OperationType, quantity: int = 1) -> float:
        """计算费用"""
        unit_price = self.get_price(operation_type)
        return round(unit_price * quantity, 2)
    
    def check_balance_sufficient(self, balance: float, operation_type: OperationType) -> tuple:
        """
        检查余额是否足够
        返回: (是否足够, 提示信息)
        """
        cost = self.get_price(operation_type)
        
        if balance < self.pricing.MINIMUM_BALANCE:
            return False, {
                "error": "INSUFFICIENT_BALANCE",
                "message": "余额不足，请先充值",
                "required": cost,
                "current": balance
            }
        
        if balance < cost:
            return False, {
                "error": "INSUFFICIENT_BALANCE",
                "message": f"余额({balance}元)不足以执行此操作({cost}元)",
                "required": cost,
                "current": balance
            }
        
        if balance < self.pricing.LOW_BALANCE_THRESHOLD:
            return True, {
                "warning": "LOW_BALANCE",
                "message": f"余额较低({balance}元)，建议及时充值",
                "required": cost,
                "current": balance
            }
        
        return True, {
            "message": "余额充足",
            "required": cost,
            "current": balance
        }
    
    def get_operation_display_name(self, operation_type: OperationType) -> str:
        """获取操作显示名称"""
        names = {
            OperationType.BASIC_QUERY: "基础政策查询",
            OperationType.ADVANCED_QUERY: "高级AI政策解读",
            OperationType.BATCH_QUERY: "批量政策查询",
            OperationType.POLICY_DETAIL: "政策详情查询",
        }
        return names.get(operation_type, str(operation_type))
    
    def get_rate_limit_config(self, operation_type: OperationType = None) -> Dict[str, Any]:
        """获取限流配置"""
        if operation_type == OperationType.ADVANCED_QUERY:
            return self.pricing.RATE_LIMITS["advanced"]
        elif operation_type == OperationType.BASIC_QUERY:
            return self.pricing.RATE_LIMITS["basic"]
        else:
            return self.pricing.RATE_LIMITS["daily_limit"]
    
    def get_pricing_summary(self) -> Dict[str, Any]:
        """获取定价摘要"""
        return {
            "pricing": {
                op.name: price 
                for op, price in self.pricing.PRICES.items()
            },
            "rate_limits": self.pricing.RATE_LIMITS,
            "low_balance_threshold": self.pricing.LOW_BALANCE_THRESHOLD,
            "minimum_balance": self.pricing.MINIMUM_BALANCE
        }


# 全局实例
billing_service = BillingService()

"""
Token API 网关
提供企业级API接口，包含认证、计费和限流
"""
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json

from engine.customers import (
    validate_api_key, 
    get_customer_info, 
    get_balance, 
    deduct_balance,
    record_usage,
    get_total_usage,
    get_usage_summary,
    check_rate_limit,
    register_customer as db_register_customer
)
from engine.billing import billing_service, OperationType
from engine.agent import policy_agent


# ========== 请求/响应模型 ==========

class TokenRegisterRequest(BaseModel):
    """Token注册请求"""
    company_name: str = Field(..., description="公司名称")
    contact: Optional[str] = Field(None, description="联系人")
    email: Optional[str] = Field(None, description="邮箱")


class TokenQueryRequest(BaseModel):
    """Token基础查询请求"""
    district: Optional[str] = Field(None, description="所属区：海珠区/天河区等")
    category: Optional[str] = Field(None, description="政策类别")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    max_results: int = Field(10, ge=1, le=100, description="最大返回条数")


class TokenAdvancedQueryRequest(BaseModel):
    """Token高级查询请求（AI解读）"""
    query: str = Field(..., description="自然语言查询，如'我们是海珠区的人工智能企业，有什么补贴可以申请？'")


class TokenResponse(BaseModel):
    """Token API通用响应"""
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    balance: Optional[float] = None
    cost: Optional[float] = None


# ========== API Key验证中间件 ==========

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    """验证API Key"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_API_KEY",
                "message": "请提供X-API-Key请求头"
            }
        )
    
    customer = validate_api_key(x_api_key)
    if not customer:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_API_KEY",
                "message": "API Key无效或已停用"
            }
        )
    
    return customer


async def check_operation_allowed(customer: Dict, operation_type: OperationType) -> None:
    """检查操作是否允许（余额和限流）"""
    balance = customer.get('balance', 0)
    
    # 检查余额
    allowed, result = billing_service.check_balance_sufficient(balance, operation_type)
    
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "error": result["error"],
                "message": result["message"],
                "required": result["required"],
                "current": result["current"]
            }
        )
    
    # 检查限流
    rate_limit_config = billing_service.get_rate_limit_config(operation_type)
    allowed, remaining, wait_seconds = check_rate_limit(
        customer['customer_id'],
        max_requests=rate_limit_config["requests"],
        window_seconds=rate_limit_config["window"]
    )
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": f"请求过于频繁，请等待{wait_seconds}秒后再试",
                "retry_after": wait_seconds,
                "limit": rate_limit_config["requests"],
                "window": rate_limit_config["window"]
            }
        )


# ========== Token API 端点 ==========

async def register_endpoint(request: TokenRegisterRequest) -> Dict[str, Any]:
    """注册新客户"""
    result = db_register_customer(
        company_name=request.company_name,
        contact=request.contact,
        email=request.email
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result)
    
    return {
        "success": True,
        "message": "注册成功",
        "customer_id": result["customer_id"],
        "api_key": result["api_key"],
        "api_secret": result["api_secret"],
        "balance": result["balance"],
        "note": "请妥善保管API Key和Secret，Secret仅显示一次"
    }


async def query_endpoint(
    request: TokenQueryRequest,
    matcher,
    customer: Dict
) -> Dict[str, Any]:
    """基础政策查询"""
    operation_type = OperationType.BASIC_QUERY
    
    # 检查操作允许
    await check_operation_allowed(customer, operation_type)
    
    # 执行查询
    try:
        policies = []
        
        if request.district:
            policies = matcher.get_policies_by_district(request.district)
        elif request.category:
            policies = matcher.get_policies_by_category(request.category)
        else:
            policies = matcher.get_all_policies()
        
        # 关键词过滤
        if request.keywords:
            filtered = []
            for p in policies:
                text = json.dumps(p.model_dump() if hasattr(p, 'model_dump') else p.__dict__, ensure_ascii=False)
                if any(kw in text for kw in request.keywords):
                    filtered.append(p)
            policies = filtered
        
        # 限制返回数量
        policies = policies[:request.max_results]
        
        # 计算费用
        cost = billing_service.get_price(operation_type)
        
        # 扣除余额
        if not deduct_balance(customer['customer_id'], cost):
            raise HTTPException(
                status_code=500,
                detail={"error": "DEDUCTION_FAILED", "message": "扣费失败"}
            )
        
        # 记录用量
        record_usage(
            customer_id=customer['customer_id'],
            operation_type=operation_type.value,
            amount=1,
            cost=cost,
            request_data=json.dumps(request.model_dump(), ensure_ascii=False),
            response_data=json.dumps({"count": len(policies)}, ensure_ascii=False)
        )
        
        # 获取更新后的余额
        new_balance = get_balance(customer['customer_id'])
        
        # 转换为字典
        policies_data = [p.model_dump() if hasattr(p, 'model_dump') else p.__dict__ for p in policies]
        
        return {
            "success": True,
            "message": "查询成功",
            "data": {
                "policies": policies_data,
                "total": len(policies),
                "query": {
                    "district": request.district,
                    "category": request.category,
                    "keywords": request.keywords
                }
            },
            "cost": cost,
            "balance": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "QUERY_FAILED", "message": f"查询失败: {str(e)}"}
        )


async def advanced_query_endpoint(
    request: TokenAdvancedQueryRequest,
    matcher,
    customer: Dict
) -> Dict[str, Any]:
    """高级政策查询（AI解读）"""
    operation_type = OperationType.ADVANCED_QUERY
    
    # 检查操作允许
    await check_operation_allowed(customer, operation_type)
    
    try:
        # 1. 从查询中提取企业信息
        extracted_info = policy_agent.llm.extract_company_info_from_query(request.query)
        
        # 2. 根据提取的信息进行政策匹配
        company_industries = extracted_info.get('industry', '其他') if extracted_info else '其他'
        district = extracted_info.get('district', '') if extracted_info else ''
        
        # 获取相关政策
        if district:
            policies = matcher.get_policies_by_district(district)
        else:
            policies = matcher.get_all_policies()
        
        # 简单匹配
        matched = []
        query_lower = request.query.lower()
        for p in policies:
            p_text = json.dumps(p.model_dump() if hasattr(p, 'model_dump') else p.__dict__, ensure_ascii=False)
            if any(kw in p_text.lower() for kw in [company_industries, '科技', '人工智能', '软件']):
                matched.append(p)
        
        # 取前10条
        matched = matched[:10]
        
        # 3. AI解读
        company_info = {
            'district': extracted_info.get('district', '') if extracted_info else '',
            'industry': extracted_info.get('industry', '') if extracted_info else ''
        }
        
        policies_data = [p.model_dump() if hasattr(p, 'model_dump') else p.__dict__ for p in matched]
        
        ai_response = policy_agent.process_query(
            query=request.query,
            customer_id=customer['customer_id'],
            matched_policies=policies_data,
            company_info=company_info
        )
        
        # 计算费用
        cost = billing_service.get_price(operation_type)
        
        # 扣除余额
        if not deduct_balance(customer['customer_id'], cost):
            raise HTTPException(
                status_code=500,
                detail={"error": "DEDUCTION_FAILED", "message": "扣费失败"}
            )
        
        # 记录用量
        record_usage(
            customer_id=customer['customer_id'],
            operation_type=operation_type.value,
            amount=1,
            cost=cost,
            request_data=json.dumps({"query": request.query}, ensure_ascii=False),
            response_data=json.dumps({"matched": len(matched)}, ensure_ascii=False)
        )
        
        # 获取更新后的余额
        new_balance = get_balance(customer['customer_id'])
        
        return {
            "success": True,
            "message": "AI解读完成",
            "data": {
                "ai_response": ai_response.get('response', ''),
                "intents": ai_response.get('intents', {}),
                "matched_policies": policies_data,
                "matched_count": len(matched),
                "query": request.query,
                "extracted_info": extracted_info
            },
            "cost": cost,
            "balance": new_balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "ADVANCED_QUERY_FAILED", "message": f"高级查询失败: {str(e)}"}
        )


async def balance_endpoint(customer: Dict) -> Dict[str, Any]:
    """查询余额"""
    balance = customer.get('balance', 0)
    
    return {
        "success": True,
        "balance": balance,
        "customer_id": customer['customer_id'],
        "company_name": customer.get('company_name', ''),
        "low_balance_warning": balance < 10.0,
        "message": "余额不足，请及时充值" if balance < 10.0 else "余额充足"
    }


async def usage_endpoint(customer: Dict, days: int = 30) -> Dict[str, Any]:
    """查询用量"""
    customer_id = customer['customer_id']
    
    # 获取总用量
    total_usage = get_total_usage(customer_id, days)
    
    # 获取用量明细
    usage_detail = get_usage_summary(customer_id, days)
    
    return {
        "success": True,
        "customer_id": customer_id,
        "period_days": days,
        "summary": total_usage,
        "details": usage_detail
    }


async def pricing_endpoint() -> Dict[str, Any]:
    """获取定价信息"""
    return {
        "success": True,
        "pricing": billing_service.get_pricing_summary()
    }

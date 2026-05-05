"""
政策通 PolicyPilot - FastAPI 后端服务 (含白标支持)
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel
import os
import json

from models import MatchRequest, MatchResponse, Policy, CompanyInfo
from matcher import PolicyMatcher
from generator import MaterialGenerator
from auth import register, login, get_current_user, get_user_info
from database import save_diagnosis_result, get_user_results, get_result_by_id


# 全局实例
matcher: PolicyMatcher = None
generator: MaterialGenerator = None


# ========== 合作伙伴配置 ==========

def load_partner_config():
    """加载合作伙伴配置"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "partners.json"
    )
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"partners": {}}

def get_partner_branding(partner_id: str = None):
    """获取合作伙伴的品牌配置"""
    default_branding = {
        "name": "政策通",
        "footer": "© 2024 政策通 PolicyPilot",
        "logo_url": "/static/logo.png"
    }
    
    if not partner_id:
        return default_branding
    
    config = load_partner_config()
    partners = config.get("partners", {})
    
    if partner_id in partners:
        partner_config = partners[partner_id]
        return {
            "name": partner_config.get("brand_name", default_branding["name"]),
            "footer": partner_config.get("brand_footer", default_branding["footer"]),
            "logo_url": partner_config.get("logo_url", default_branding["logo_url"])
        }
    
    return default_branding


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global matcher, generator
    # 启动时加载数据
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    policies_file = os.path.join(base_dir, "data", "policies.json")
    matcher = PolicyMatcher(policies_file)
    generator = MaterialGenerator(matcher)
    print(f"✅ 政策数据加载完成，共 {len(matcher.get_all_policies())} 条政策")
    yield
    # 关闭时清理
    print("👋 服务关闭")


# 前端目录
frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend"
)

app = FastAPI(
    title="政策通 PolicyPilot",
    description="AI政策补贴自动匹配与申报辅助工具",
    version="1.3.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def root():
    """根路径 - 返回前端首页"""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "name": "政策通 PolicyPilot",
        "version": "1.3.0",
        "description": "AI政策补贴自动匹配与申报辅助工具",
        "features": {
            "white_label": True,
            "partner_api": "/api/partner/chat"
        },
        "endpoints": {
            "match": "POST /match - 匹配企业政策",
            "policies": "GET /policies - 获取所有政策",
            "policy_detail": "GET /policy/{id} - 获取政策详情",
            "register": "POST /register - 用户注册",
            "login": "POST /login - 用户登录",
            "generate_materials": "POST /generate-materials - 生成申报材料",
            "partner_chat": "POST /api/partner/chat - 合作伙伴白标接口"
        }
    }


# ========== 原有API ==========

@app.post("/match", response_model=MatchResponse)
async def match_policies(request: MatchRequest, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """匹配企业适用的政策
    
    新增响应字段:
    - partner_id: 合作伙伴标识 (如果通过 X-Partner-ID header 传递)
    - branding: 品牌信息对象
    """
    try:
        matched = matcher.match(request.company)
        
        highly_recommended = [m for m in matched if m.is_highly_recommended]
        
        # 构建响应
        response_data = {
            "company_name": request.company.name,
            "total_matches": len(matched),
            "highly_recommended_count": len(highly_recommended),
            "matched_policies": matched,
            # 白标支持
            "partner_id": partner_id,
            "branding": get_partner_branding(partner_id)
        }
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配出错: {str(e)}")


@app.get("/policies", response_model=list[Policy])
async def get_policies(district: str = None, category: str = None, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """获取政策列表 (支持白标)"""
    result = []
    if district:
        result = matcher.get_policies_by_district(district)
    elif category:
        result = matcher.get_policies_by_category(category)
    else:
        result = matcher.get_all_policies()
    
    # 添加白标信息
    return {
        "data": result,
        "partner_id": partner_id,
        "branding": get_partner_branding(partner_id)
    }


@app.get("/policy/{policy_id}", response_model=Policy)
async def get_policy_detail(policy_id: str, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """获取政策详情 (支持白标)"""
    policy = matcher.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="未找到该政策")
    
    # 添加白标信息
    return {
        "data": policy,
        "partner_id": partner_id,
        "branding": get_partner_branding(partner_id)
    }


# ========== 认证API ==========

class RegisterRequest(BaseModel):
    phone: str
    verify_code: Optional[str] = "123456"


class LoginRequest(BaseModel):
    phone: str
    verify_code: Optional[str] = "123456"


@app.post("/register")
async def user_register(request: RegisterRequest, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """用户注册"""
    result = register(request.phone, request.verify_code)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    # 添加白标信息
    result['partner_id'] = partner_id
    result['branding'] = get_partner_branding(partner_id)
    return result


@app.post("/login")
async def user_login(request: LoginRequest, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """用户登录"""
    result = login(request.phone, request.verify_code)
    if not result['success']:
        raise HTTPException(status_code=401, detail=result['message'])
    
    # 添加白标信息
    result['partner_id'] = partner_id
    result['branding'] = get_partner_branding(partner_id)
    return result


@app.get("/user/info")
async def get_user_info_endpoint(authorization: Optional[str] = Header(None), partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """获取当前用户信息"""
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    
    # 提取token
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    return {
        "success": True,
        "user": get_user_info(user['id']),
        "partner_id": partner_id,
        "branding": get_partner_branding(partner_id)
    }


# ========== 诊断结果API ==========

class SaveResultRequest(BaseModel):
    company: dict
    match_result: dict


@app.post("/user/result")
async def save_result(
    request: SaveResultRequest,
    authorization: Optional[str] = Header(None),
    partner_id: Optional[str] = Header(None, alias="X-Partner-ID")
):
    """保存诊断结果"""
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    result_id = save_diagnosis_result(
        user_id=user['id'],
        company_data=request.company,
        match_result=request.match_result
    )
    
    return {
        "success": True,
        "message": "诊断结果已保存",
        "result_id": result_id,
        "partner_id": partner_id,
        "branding": get_partner_branding(partner_id)
    }


@app.get("/user/results")
async def get_results(authorization: Optional[str] = Header(None), partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """获取用户诊断历史"""
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    results = get_user_results(user['id'])
    
    return {
        "success": True,
        "results": results,
        "total": len(results),
        "partner_id": partner_id,
        "branding": get_partner_branding(partner_id)
    }


@app.get("/user/result/{result_id}")
async def get_result_detail(
    result_id: int,
    authorization: Optional[str] = Header(None),
    partner_id: Optional[str] = Header(None, alias="X-Partner-ID")
):
    """获取诊断结果详情"""
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    
    result = get_result_by_id(result_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="未找到该诊断结果")
    
    return {
        "success": True,
        "result": result,
        "partner_id": partner_id,
        "branding": get_partner_branding(partner_id)
    }


# ========== 材料生成API ==========

class GenerateMaterialsRequest(BaseModel):
    policy_id: str
    company_name: str
    district: str
    industry: str
    established_years: int
    employee_count: int
    revenue_scale: str
    has_ip: bool = False
    is_high_tech: bool = False
    is_specialized: bool = False
    has_vc_investment: bool = False


@app.post("/generate-materials")
async def generate_materials(request: GenerateMaterialsRequest, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """生成申报材料"""
    try:
        company_info = {
            'name': request.company_name,
            'district': request.district,
            'industry': request.industry,
            'established_years': request.established_years,
            'employee_count': request.employee_count,
            'revenue_scale': request.revenue_scale,
            'has_ip': request.has_ip,
            'is_high_tech': request.is_high_tech,
            'is_specialized': request.is_specialized,
            'has_vc_investment': request.has_vc_investment
        }
        
        result = generator.generate_materials(company_info, request.policy_id)
        
        if not result.get('success'):
            raise HTTPException(status_code=404, detail=result.get('error', '生成失败'))
        
        # 添加白标信息
        result['partner_id'] = partner_id
        result['branding'] = get_partner_branding(partner_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成申报材料出错: {str(e)}")


# ========== 合作伙伴白标API ==========

class PartnerChatRequest(BaseModel):
    """合作伙伴聊天请求"""
    query: str
    company_info: Optional[dict] = None
    custom_branding: Optional[dict] = None  # 自定义品牌覆盖


class PartnerChatResponse(BaseModel):
    """合作伙伴聊天响应"""
    response: str
    partner_id: str
    branding: dict
    metadata: dict


from fastapi import Request

@app.post("/api/partner/chat", response_model=PartnerChatResponse)
async def partner_chat(
    request_body: PartnerChatRequest,
    request: Request
):
    """
    合作伙伴白标接口
    
    - 请求头: X-Partner-ID (必填)
    - 支持自定义品牌覆盖
    - 当前只做框架，完整鉴权待合作伙伴接入时完善
    """
    # 获取合作伙伴ID (从请求头获取)
    partner_id = request.headers.get("x-partner-id")
    
    if not partner_id:
        partner_id = request_body.company_info.get('partner_id') if request_body.company_info else None
    
    if not partner_id:
        raise HTTPException(
            status_code=400, 
            detail="缺少合作伙伴标识，请通过 X-Partner-ID 请求头传递"
        )
    
    # 验证合作伙伴配置
    config = load_partner_config()
    partners = config.get("partners", {})
    
    if partner_id not in partners:
        # 预留给新合作伙伴，静默注册
        partners[partner_id] = {
            "name": f"Partner-{partner_id}",
            "status": "pending_activation",
            "created_at": "auto"
        }
        print(f"📝 新合作伙伴注册请求: {partner_id}")
    
    # 构建品牌信息
    branding = get_partner_branding(partner_id)
    
    # 如果请求中包含自定义品牌覆盖
    if request_body.custom_branding:
        branding.update(request_body.custom_branding)
    
    # TODO: 完整的AI对话逻辑
    # 目前返回框架响应
    response_text = f"[{branding['name']}] 收到您的咨询，正在处理中..."
    
    if request_body.company_info:
        # 如果提供了企业信息，执行政策匹配
        try:
            from models import Company
            
            company = Company(**request_body.company_info)
            matched = matcher.match(company)
            
            if matched:
                response_text = f"根据您的企业信息，我为您匹配到 {len(matched)} 条适用政策：\n"
                for i, p in enumerate(matched[:5], 1):
                    response_text += f"{i}. {p.policy.name} - {p.policy.subsidy_amount}\n"
            else:
                response_text = "抱歉，根据您的企业信息，暂未匹配到适用政策。"
        except Exception as e:
            response_text = f"政策匹配服务暂时不可用，请稍后再试。"
    
    return PartnerChatResponse(
        response=response_text,
        partner_id=partner_id,
        branding=branding,
        metadata={
            "api_version": "1.0",
            "status": "ready",
            "note": "完整鉴权功能待合作伙伴接入时完善"
        }
    )


@app.get("/api/partner/config/{partner_id}")
async def get_partner_config(partner_id: str):
    """
    获取合作伙伴配置 (供合作伙伴前端使用)
    
    返回可用于前端初始化的配置信息
    """
    branding = get_partner_branding(partner_id)
    config = load_partner_config()
    partners = config.get("partners", {})
    
    partner_info = partners.get(partner_id, {})
    
    return {
        "partner_id": partner_id,
        "branding": branding,
        "config": {
            "features": partner_info.get("features", {
                "match": True,
                "material_generation": True,
                "history": True
            }),
            "limits": partner_info.get("limits", {
                "daily_requests": 1000,
                "monthly_requests": 30000
            })
        },
        "status": partner_info.get("status", "active")
    }


# ========== 我的诊断页面 ==========

@app.get("/my-results")
async def my_results_page():
    """我的诊断页面"""
    page_path = os.path.join(frontend_dir, "my-results.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    raise HTTPException(status_code=404, detail="页面不存在")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ========== Token API 端点 ==========
# V1: Token化API网关 - 按查询计费模式

from customers import (
    register_customer, 
    get_customer_by_api_key, 
    get_customer_by_id,
    verify_api_key,
    recharge_balance,
    get_balance_transactions,
    get_all_customers
)
from billing import (
    get_usage_stats, 
    get_current_month_usage,
    get_monthly_bill,
    get_bill_history,
    get_pricing_info,
    calculate_cost
)
from token_gateway import require_token_auth, gateway
from pydantic import BaseModel, Field


# Token API 请求模型
class TokenQueryRequest(BaseModel):
    """Token查询请求"""
    name: str = Field(..., description="企业名称")
    district: str = Field(..., description="所属区：海珠/天河")
    industry: str = Field(..., description="所属行业")
    established_years: int = Field(..., ge=0, description="成立年限")
    revenue_scale: str = Field(..., description="营收规模")
    employee_count: int = Field(..., ge=0, description="员工数量")
    has_ip: bool = Field(False, description="是否有知识产权")
    is_high_tech: bool = Field(False, description="是否高新技术企业")
    is_specialized: bool = Field(False, description="是否专精特新企业")
    has_vc_investment: bool = Field(False, description="是否有风险投资")


class AdvancedQueryRequest(TokenQueryRequest):
    """高级查询请求（包含AI解读）"""
    include_ai_analysis: bool = Field(True, description="是否包含AI分析")


class CustomerRegisterRequest(BaseModel):
    """客户注册请求"""
    customer_name: str = Field(..., description="客户名称/联系人")
    company_name: str = Field(None, description="公司名称")
    email: str = Field(None, description="邮箱")
    phone: str = Field(None, description="电话")
    initial_balance: float = Field(0.0, description="初始充值金额")


class RechargeRequest(BaseModel):
    """充值请求"""
    amount: float = Field(..., gt=0, description="充值金额")


# ========== 客户管理端点 ==========

@app.post("/api/token/register", tags=["Token API"])
async def token_register(request: CustomerRegisterRequest):
    """
    注册Token API客户
    
    - 自动生成 API Key (格式: pp_live_xxxxxxxx)
    - 可选初始充值
    """
    result = register_customer(
        customer_name=request.customer_name,
        company_name=request.company_name,
        email=request.email,
        phone=request.phone,
        initial_balance=request.initial_balance
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "success": True,
        "message": "注册成功",
        "data": {
            "customer_id": result["customer_id"],
            "api_key": result["api_key"],
            "api_secret": result["api_secret"],
            "balance": result["balance"],
            "rate_limit": result["rate_limit"],
            "pricing": get_pricing_info()
        }
    }


@app.post("/api/token/recharge", tags=["Token API"])
async def token_recharge(
    request: RechargeRequest,
    authorization: Optional[str] = Header(None)
):
    """
    充值余额
    
    - 需要通过 X-API-Key header 提供API Key
    """
    api_key = authorization.replace("Bearer ", "") if authorization else None
    if not api_key:
        raise HTTPException(status_code=401, detail="请提供API Key")
    
    auth = gateway.authenticate(api_key)
    if not auth["success"]:
        raise HTTPException(status_code=401, detail=auth["message"])
    
    result = recharge_balance(
        customer_id=auth["customer_id"],
        amount=request.amount,
        description=f"Token API充值 {request.amount} 元"
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "success": True,
        "message": "充值成功",
        "amount": result["amount"],
        "new_balance": result["new_balance"]
    }


# ========== 查询端点 ==========

@app.post("/api/token/query", tags=["Token API"])
async def token_query(
    request: TokenQueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    基础政策查询
    
    - 按企业画像匹配，返回政策列表
    - 费用: 0.1元/次
    - 需要通过 X-API-Key header 提供API Key
    """
    api_key = x_api_key or ""
    
    # 使用网关装饰器验证
    auth = gateway.authenticate(api_key)
    if not auth["success"]:
        raise HTTPException(status_code=401, detail=auth["message"])
    
    # 限流检查
    rate_result = gateway.check_rate_limit(auth["customer_id"], auth["rate_limit"])
    if not rate_result["allowed"]:
        raise HTTPException(
            status_code=429, 
            detail=f"请求过于频繁，请{rate_result['retry_after']}秒后重试"
        )
    
    # 余额检查
    cost = calculate_cost("basic")
    if auth["balance"] < cost:
        raise HTTPException(
            status_code=402, 
            detail=f"余额不足，当前余额{auth['balance']}元，查询费用{cost}元"
        )
    
    # 执行查询
    import time
    start_time = time.time()
    
    try:
        company = CompanyInfo(**request.model_dump())
        matched = matcher.match(company)
        highly_recommended = [m for m in matched if m.is_highly_recommended]
        
        result = {
            "success": True,
            "company_name": request.name,
            "total_matches": len(matched),
            "highly_recommended_count": len(highly_recommended),
            "matched_policies": matched[:20],  # 限制返回20条
            "query_type": "basic",
            "cost": cost,
            "remaining_balance": auth["balance"] - cost
        }
        
        # 记录日志
        response_time_ms = int((time.time() - start_time) * 1000)
        from billing import log_api_usage
        log_api_usage(
            customer_id=auth["customer_id"],
            api_key=api_key,
            endpoint="/api/token/query",
            query_type="basic",
            result_count=len(matched),
            response_time_ms=response_time_ms
        )
        
        # 扣费
        from customers import deduct_balance
        deduct_balance(
            customer_id=auth["customer_id"],
            amount=cost,
            description="基础政策查询"
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询出错: {str(e)}")


@app.post("/api/token/query/advanced", tags=["Token API"])
async def token_query_advanced(
    request: AdvancedQueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    高级政策查询（含AI解读）
    
    - 包含政策解读、申报建议等AI分析
    - 费用: 0.5元/次
    - 需要通过 X-API-Key header 提供API Key
    """
    api_key = x_api_key or ""
    
    # 认证
    auth = gateway.authenticate(api_key)
    if not auth["success"]:
        raise HTTPException(status_code=401, detail=auth["message"])
    
    # 限流检查
    rate_result = gateway.check_rate_limit(auth["customer_id"], auth["rate_limit"])
    if not rate_result["allowed"]:
        raise HTTPException(
            status_code=429, 
            detail=f"请求过于频繁，请{rate_result['retry_after']}秒后重试"
        )
    
    # 余额检查
    cost = calculate_cost("advanced")
    if auth["balance"] < cost:
        raise HTTPException(
            status_code=402, 
            detail=f"余额不足，当前余额{auth['balance']}元，查询费用{cost}元"
        )
    
    import time
    start_time = time.time()
    
    try:
        company = CompanyInfo(**request.model_dump(exclude={"include_ai_analysis"}))
        matched = matcher.match(company)
        highly_recommended = [m for m in matched if m.is_highly_recommended]
        
        # 生成AI分析（简化版，实际可接入LLM）
        ai_analysis = None
        if request.include_ai_analysis and matched:
            top_policies = matched[:5]
            ai_analysis = {
                "summary": f"根据企业画像分析，为您匹配到 {len(matched)} 条适用政策，其中 {len(highly_recommended)} 条重点推荐。",
                "top_recommendations": [
                    {
                        "policy_name": p.policy.name,
                        "match_score": p.match_score,
                        "analysis": f"该政策匹配度{p.match_score}%，{' '.join(p.match_reasons[:2])}。",
                        "application_suggestion": f"建议优先申报 {p.policy.name}，补贴金额 {p.policy.subsidy_amount}。"
                    }
                    for p in top_policies
                ],
                "risk_alerts": [
                    f"注意申报截止时间：{p.policy.deadline}"
                    for p in top_policies[:3]
                ]
            }
        
        result = {
            "success": True,
            "company_name": request.name,
            "total_matches": len(matched),
            "highly_recommended_count": len(highly_recommended),
            "matched_policies": matched[:20],
            "ai_analysis": ai_analysis,
            "query_type": "advanced",
            "cost": cost,
            "remaining_balance": auth["balance"] - cost
        }
        
        # 记录日志
        response_time_ms = int((time.time() - start_time) * 1000)
        from billing import log_api_usage
        log_api_usage(
            customer_id=auth["customer_id"],
            api_key=api_key,
            endpoint="/api/token/query/advanced",
            query_type="advanced",
            result_count=len(matched),
            response_time_ms=response_time_ms
        )
        
        # 扣费
        from customers import deduct_balance
        deduct_balance(
            customer_id=auth["customer_id"],
            amount=cost,
            description="高级政策查询（含AI解读）"
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询出错: {str(e)}")


# ========== 用量与账单端点 ==========

@app.get("/api/token/usage", tags=["Token API"])
async def token_usage(
    days: int = 30,
    authorization: Optional[str] = Header(None)
):
    """
    查询用量统计
    
    - 返回每日/总调用统计
    - 默认查询最近30天
    """
    api_key = authorization.replace("Bearer ", "") if authorization else None
    if not api_key:
        raise HTTPException(status_code=401, detail="请提供API Key")
    
    auth = gateway.authenticate(api_key)
    if not auth["success"]:
        raise HTTPException(status_code=401, detail=auth["message"])
    
    stats = get_usage_stats(auth["customer_id"], days)
    
    return {
        "success": True,
        "customer_id": auth["customer_id"],
        "customer_name": auth["customer_name"],
        "current_balance": auth["balance"],
        "usage": stats
    }


@app.get("/api/token/bill", tags=["Token API"])
async def token_bill(
    month: str = None,
    authorization: Optional[str] = Header(None)
):
    """
    查询账单
    
    - 不带参数返回当月账单
    - 带 month 参数返回指定月份 (格式: YYYY-MM)
    """
    api_key = authorization.replace("Bearer ", "") if authorization else None
    if not api_key:
        raise HTTPException(status_code=401, detail="请提供API Key")
    
    auth = gateway.authenticate(api_key)
    if not auth["success"]:
        raise HTTPException(status_code=401, detail=auth["message"])
    
    if month:
        bill = get_monthly_bill(auth["customer_id"], month)
        if not bill:
            raise HTTPException(status_code=404, detail=f"未找到 {month} 的账单")
        history = [bill]
    else:
        history = get_bill_history(auth["customer_id"])
    
    return {
        "success": True,
        "customer_id": auth["customer_id"],
        "customer_name": auth["customer_name"],
        "current_balance": auth["balance"],
        "bills": history
    }


@app.get("/api/token/balance", tags=["Token API"])
async def token_balance(
    authorization: Optional[str] = Header(None)
):
    """
    查询余额
    
    - 返回当前余额
    - 返回最近余额变动记录
    """
    api_key = authorization.replace("Bearer ", "") if authorization else None
    if not api_key:
        raise HTTPException(status_code=401, detail="请提供API Key")
    
    auth = gateway.authenticate(api_key)
    if not auth["success"]:
        raise HTTPException(status_code=401, detail=auth["message"])
    
    transactions = get_balance_transactions(auth["customer_id"], 20)
    
    return {
        "success": True,
        "customer_id": auth["customer_id"],
        "customer_name": auth["customer_name"],
        "balance": auth["balance"],
        "rate_limit": auth["rate_limit"],
        "pricing": get_pricing_info(),
        "transactions": transactions
    }


# ========== Token API 信息端点 ==========

@app.get("/api/token/info", tags=["Token API"])
async def token_info():
    """
    获取Token API信息
    
    - 返回API版本、定价、端点说明
    """
    return {
        "name": "PolicyPilot Token API",
        "version": "v1",
        "description": "政策通Token化API网关 - 按查询计费",
        "pricing": get_pricing_info(),
        "endpoints": {
            "register": "POST /api/token/register - 注册客户",
            "recharge": "POST /api/token/recharge - 充值余额",
            "query": "POST /api/token/query - 基础查询 (0.1元/次)",
            "query_advanced": "POST /api/token/query/advanced - 高级查询 (0.5元/次)",
            "usage": "GET /api/token/usage - 用量统计",
            "bill": "GET /api/token/bill - 账单查询",
            "balance": "GET /api/token/balance - 余额查询"
        },
        "authentication": "通过 X-API-Key 请求头传递API Key"
    }


print("✅ Token API V1 端点注册完成")

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

from models import MatchRequest, MatchResponse, Policy
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

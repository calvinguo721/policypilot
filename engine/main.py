from dotenv import load_dotenv
load_dotenv()
"""
政策通 PolicyPilot - FastAPI 后端服务 (含白标支持 + Token API)
端口: 8002
"""
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from typing import Optional, List
from pydantic import BaseModel, Field
import os
import json
import re

from engine.models import MatchRequest, MatchResponse, Policy
from engine.matcher import PolicyMatcher
from engine.generator import MaterialGenerator
from engine.auth import register, login, get_current_user, get_user_info
from engine.database import save_diagnosis_result, get_user_results, get_result_by_id

# Token API 相关模块
from engine.customers import init_token_tables
from engine.token_gateway import (
    TokenRegisterRequest,
    TokenQueryRequest,
    TokenAdvancedQueryRequest,
    verify_api_key,
    register_endpoint,
    query_endpoint,
    advanced_query_endpoint,
    balance_endpoint,
    usage_endpoint,
    pricing_endpoint
)


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
    
    # 初始化Token表
    init_token_tables()
    
    print(f"✅ 政策数据加载完成，共 {len(matcher.get_all_policies())} 条政策")
    print("✅ Token API 网关已初始化")
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
    description="AI政策补贴自动匹配与申报辅助工具 - 含Token API企业版",
    version="1.4.0",
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
        "version": "1.4.0",
        "description": "AI政策补贴自动匹配与申报辅助工具",
        "features": {
            "white_label": True,
            "partner_api": "/api/partner/chat",
            "token_api": True
        },
        "endpoints": {
            "match": "POST /match - 匹配企业政策",
            "policies": "GET /policies - 获取所有政策",
            "policy_detail": "GET /policy/{id} - 获取政策详情",
            "register": "POST /register - 用户注册",
            "login": "POST /login - 用户登录",
            "generate_materials": "POST /generate-materials - 生成申报材料",
            "partner_chat": "POST /api/partner/chat - 合作伙伴白标接口",
            "token_api": {
                "register": "POST /api/token/register - 注册Token客户",
                "query": "POST /api/token/query - 基础政策查询(0.1元/次)",
                "advanced_query": "POST /api/token/query/advanced - AI政策解读(0.5元/次)",
                "balance": "GET /api/token/balance - 查询余额",
                "usage": "GET /api/token/usage - 查询用量"
            }
        }
    }


# ========== Token API 端点 ==========

@app.post("/api/token/register", summary="注册Token客户")
async def token_register(request: TokenRegisterRequest):
    """注册新客户，获取API Key"""
    return await register_endpoint(request)


@app.post("/api/token/query", summary="基础政策查询")
async def token_query(
    request: TokenQueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    基础政策查询
    
    费用: 0.1元/次
    限流: 100次/分钟
    """
    customer = await verify_api_key(x_api_key)
    return await query_endpoint(request, matcher, customer)


@app.post("/api/token/query/advanced", summary="高级政策查询(AI解读)")
async def token_advanced_query(
    request: TokenAdvancedQueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    高级政策查询 - AI智能解读
    
    费用: 0.5元/次
    限流: 20次/分钟
    
    支持自然语言查询，如：
    "我们是海珠区的人工智能企业，有什么补贴可以申请？"
    """
    customer = await verify_api_key(x_api_key)
    return await advanced_query_endpoint(request, matcher, customer)


@app.get("/api/token/balance", summary="查询余额")
async def token_balance(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """查询当前账户余额"""
    customer = await verify_api_key(x_api_key)
    return await balance_endpoint(customer)


@app.get("/api/token/usage", summary="查询用量")
async def token_usage(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    days: int = Query(30, ge=1, le=365, description="查询天数")
):
    """查询用量统计"""
    customer = await verify_api_key(x_api_key)
    return await usage_endpoint(customer, days)


@app.get("/api/token/pricing", summary="获取定价")
async def token_pricing():
    """获取API定价信息"""
    return await pricing_endpoint()


# ========== 原有API ==========

@app.post("/match", response_model=MatchResponse)
async def match_policies(request: MatchRequest, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """匹配企业适用的政策"""
    try:
        matched = matcher.match(request.company)
        
        highly_recommended = [m for m in matched if m.is_highly_recommended]
        
        response_data = {
            "company_name": request.company.name,
            "total_matches": len(matched),
            "highly_recommended_count": len(highly_recommended),
            "matched_policies": matched,
            "partner_id": partner_id,
            "branding": get_partner_branding(partner_id)
        }
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配出错: {str(e)}")


@app.get("/policies", response_model=List[Policy])
async def get_policies(district: str = None, category: str = None, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """获取政策列表"""
    result = []
    if district:
        result = matcher.get_policies_by_district(district)
    elif category:
        result = matcher.get_policies_by_category(category)
    else:
        result = matcher.get_all_policies()
    
    return result


@app.get("/policy/{policy_id}", response_model=Policy)
async def get_policy_detail(policy_id: str, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """获取政策详情"""
    policy = matcher.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="未找到该政策")
    
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
    
    result['partner_id'] = partner_id
    result['branding'] = get_partner_branding(partner_id)
    return result


@app.post("/login")
async def user_login(request: LoginRequest, partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """用户登录"""
    result = login(request.phone, request.verify_code)
    if not result['success']:
        raise HTTPException(status_code=401, detail=result['message'])
    
    result['partner_id'] = partner_id
    result['branding'] = get_partner_branding(partner_id)
    return result


@app.get("/user/info")
async def get_user_info_endpoint(authorization: Optional[str] = Header(None), partner_id: Optional[str] = Header(None, alias="X-Partner-ID")):
    """获取当前用户信息"""
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    
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
        
        result['partner_id'] = partner_id
        result['branding'] = get_partner_branding(partner_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成申报材料出错: {str(e)}")


# ========== 合作伙伴白标API ==========

class PartnerChatRequest(BaseModel):
    query: str
    company_info: Optional[dict] = None
    custom_branding: Optional[dict] = None


class PartnerChatResponse(BaseModel):
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
    """合作伙伴白标接口 - RAG增强版：基于真实政策数据库回答"""
    partner_id = request.headers.get("x-partner-id")
    
    if not partner_id:
        partner_id = request_body.company_info.get('partner_id') if request_body.company_info else None
    
    if not partner_id:
        partner_id = "web_guest"
    
    config = load_partner_config()
    partners = config.get("partners", {})
    
    if partner_id not in partners:
        partners[partner_id] = {
            "name": f"Partner-{partner_id}",
            "status": "pending_activation",
            "created_at": "auto"
        }
    
    branding = get_partner_branding(partner_id)
    
    if request_body.custom_branding:
        branding.update(request_body.custom_branding)
    
    # === 限流检查 ===
    daily_limit = 999
    usage_file = f"/tmp/chat_usage_{partner_id}.json"
    today_str = __import__('datetime').date.today().isoformat()
    
    try:
        if os.path.exists(usage_file):
            with open(usage_file, 'r') as f:
                usage = json.load(f)
        else:
            usage = {}
        
        if usage.get('date') != today_str:
            usage = {'date': today_str, 'count': 0}
        
        if usage['count'] >= daily_limit:
            return PartnerChatResponse(
                response=f"您今日的免费AI对话次数已用完（每日{daily_limit}次）。升级包月会员可享每月500次AI对话，首年仅899元/年。",
                partner_id=partner_id,
                branding=branding,
                metadata={"api_version": "1.0", "status": "rate_limited", "remaining_today": 0, "daily_limit": daily_limit}
            )
    except Exception:
        usage = {'date': today_str, 'count': 0}
    
    # === RAG：从政策数据库检索 ===
    query = request_body.query
    matched_policies_data = []
    keywords = []
    found_districts = []
    
    try:
        all_policies = matcher.get_all_policies()
        query_lower = query.lower()
        
        # 提取中文关键词 - 从连续中文串中提取2-5字子串
        keywords = []
        for seg in re.findall(r'[\u4e00-\u9fff]+', query):
            for length in range(2, min(len(seg)+1, 6)):
                for i in range(len(seg)-length+1):
                    kw = seg[i:i+length]
                    if kw not in keywords:
                        keywords.append(kw)
        
        # 地区关键词
        district_map = ["海珠", "天河", "越秀", "荔湾", "白云", "黄埔", "番禺", "花都", "南沙", "从化", "增城",
                       "广州", "深圳", "北京", "上海", "佛山", "东莞", "杭州", "苏州",
                       "越秀区", "荔湾区", "白云区", "黄埔区", "番禺区", "花都区", "南沙区", "从化区", "增城区"]
        found_districts = [d for d in district_map if d in query]
        
        # 类别/行业关键词
        cat_words = ["补贴", "创业", "人才", "融资", "研发", "技改", "知识产权", "税收", "租金", 
                    "人工智能", "AI", "大模型", "软件", "集成电路", "专精特新", "高新", "数字化",
                    "OPC", "运营", "入驻", "孵化器", "园区", "创新", "科技", "产业", "扶持",
                    "奖励", "资助", "认定", "申报", "减免", "贷款", "贴息"]
        found_cats = [c for c in cat_words if c.lower() in query_lower]
        
        # 评分搜索
        scored = []
        for p in all_policies:
            score = 0
            pd = p.model_dump() if hasattr(p, 'model_dump') else (p.dict() if hasattr(p, 'dict') else p)
            p_name = str(pd.get('name', ''))
            p_district = str(pd.get('district', ''))
            p_category = str(pd.get('category', ''))
            p_subsidy = str(pd.get('subsidy_amount', ''))
            p_cond = str(pd.get('conditions', ''))
            p_text = f"{p_name} {p_district} {p_category} {p_subsidy} {p_cond}".lower()
            
            for d in found_districts:
                if d in p_district or d in p_name:
                    score += 30
            
            for kw in keywords:
                if kw in p_text:
                    score += 8
            
            for c in found_cats:
                if c.lower() in p_text:
                    score += 12
            
            if pd.get('subsidy_amount') and str(pd['subsidy_amount']) not in ('未明确', '', 'None'):
                score += 5
            
            if score > 0:
                scored.append((score, pd))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        matched_policies_data = [p for _, p in scored[:8]]
        
    except Exception as e:
        print(f"Policy search error: {e}")
    
    # === 构建RAG上下文 ===
    policy_context = ""
    if matched_policies_data:
        policy_context = "\n\n## 以下是从政策通数据库检索到的相关政策（请严格基于这些真实数据回答）：\n\n"
        for i, p in enumerate(matched_policies_data, 1):
            policy_context += f"### 政策{i}: {p.get('name', '未知')}\n"
            policy_context += f"- 地区: {p.get('district', '未明确')}\n"
            sa = p.get('subsidy_amount', '')
            if sa and str(sa) not in ('未明确', '', 'None'):
                policy_context += f"- 补贴金额: {sa}\n"
            if p.get('category'):
                policy_context += f"- 类别: {p['category']}\n"
            conds = p.get('conditions', {})
            if isinstance(conds, dict):
                ind = conds.get('industry', [])
                if ind:
                    industry_str = ', '.join(ind[:5]) if isinstance(ind, list) else str(ind)
                    policy_context += f"- 适用行业: {industry_str}\n"
                other = conds.get('other', [])
                if other and isinstance(other, list):
                    for c in other[:3]:
                        if len(str(c)) < 100:
                            policy_context += f"- 条件: {c}\n"
            elif isinstance(conds, str) and conds:
                policy_context += f"- 条件: {conds[:200]}\n"
            dl = p.get('deadline', '')
            if dl and str(dl) not in ('未明确', '', 'None'):
                policy_context += f"- 截止时间: {dl}\n"
            lk = p.get('link', '')
            if lk and str(lk).startswith('http'):
                policy_context += f"- 政策链接: {lk}\n"
            policy_context += "\n"
    else:
        policy_context = "\n\n注意：未从政策通数据库中检索到直接匹配的政策，请基于通用知识回答，但明确告知这是通用建议，建议用户提供更具体信息以获得精准匹配。"
    
    # === 调用DeepSeek ===
    system_prompt = """你是政策通AI助手，专注中国政府补贴政策。核心原则：
1. 只基于提供的政策数据回答，绝不编造不存在的政策
2. 必须给出具体数字：补贴金额、申报条件、截止时间
3. 不要说"建议查阅""请联系"等推诿话术
4. 量化收益：能算出能拿多少钱就算
5. 用编号列表，每条政策含金额+条件+时间
6. 如果数据不够精准，说明需要什么额外信息来精准匹配

回答模板：
📊 匹配到X条政策：
1. **政策名**
   💰 金额：XXX
   📋 条件：XXX
   ⏰ 截止：XXX
💡 优先建议：XXX"""

    user_prompt = f"用户问题：{query}\n\n{policy_context}\n\n请基于以上真实政策数据直接回答。给出具体金额、条件、时间。"
    
    response_text = None
    from engine.llm_fallback import llm_fallback
    try:
        response_text = llm_fallback._call_deepseek(user_prompt, system_prompt)
    except Exception as e:
        print(f"DeepSeek error: {e}")
    
    # Fallback: 模板回答
    if not response_text and matched_policies_data:
        parts = [f"📊 根据您的查询，匹配到{len(matched_policies_data)}条政策：\n\n"]
        for i, p in enumerate(matched_policies_data[:5], 1):
            parts.append(f"{i}. **{p.get('name', '未知')}**\n")
            sa = p.get('subsidy_amount', '')
            if sa and str(sa) not in ('未明确', '', 'None'):
                parts.append(f"   💰 补贴：{sa}\n")
            if p.get('district'):
                parts.append(f"   📍 {p['district']}\n")
            conds = p.get('conditions', {})
            if isinstance(conds, dict):
                other = conds.get('other', [])
                if other and isinstance(other, list):
                    for c in other[:2]:
                        if len(str(c)) < 60:
                            parts.append(f"   📋 {c}\n")
            parts.append("\n")
        response_text = "".join(parts)
    
    if not response_text:
        response_text = "抱歉，暂时无法处理您的请求，请稍后再试。"
    
    # 更新用量
    try:
        usage['count'] = usage.get('count', 0) + 1
        with open(usage_file, 'w') as f:
            json.dump(usage, f)
    except Exception:
        pass
    
    remaining = max(0, daily_limit - usage.get('count', 0))
    
    return PartnerChatResponse(
        response=response_text,
        partner_id=partner_id,
        branding=branding,
        metadata={
            "api_version": "1.0",
            "status": "ready",
            "remaining_today": remaining,
            "daily_limit": daily_limit,
            "policies_found": len(matched_policies_data),
            "keywords": keywords[:5],
            "districts": found_districts
        }
    )



@app.get("/api/partner/config/{partner_id}")
async def get_partner_config(partner_id: str):
    """获取合作伙伴配置"""
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




@app.get("/ai-chat")
async def ai_chat_page():
    """AI对话页面"""
    page_path = os.path.join(frontend_dir, "ai-chat.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    raise HTTPException(status_code=404, detail="页面不存在")
# ========== 新增静态页面路由 ==========

@app.get("/api-docs")
async def api_docs_page():
    """API文档页面"""
    page_path = os.path.join(frontend_dir, "api-docs.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    raise HTTPException(status_code=404, detail="页面不存在")


@app.get("/console")
async def console_page():
    """控制台页面"""
    page_path = os.path.join(frontend_dir, "console.html")
    if os.path.exists(page_path):
        return FileResponse(page_path)
    raise HTTPException(status_code=404, detail="页面不存在")


# ========== Token API 补充端点 ==========

class TokenRechargeRequest(BaseModel):
    amount: float = Field(..., gt=0, description="充值金额")


class TokenBillResponse(BaseModel):
    success: bool
    bills: list
    total: int


@app.post("/api/token/recharge", summary="账户充值")
async def token_recharge(
    request: TokenRechargeRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """模拟充值接口"""
    from customers import verify_api_key
    customer = await verify_api_key(x_api_key)
    
    # 模拟充值逻辑
    from database import execute_sql
    execute_sql(
        "UPDATE token_customers SET balance = balance + %s WHERE api_key = %s",
        (request.amount, x_api_key)
    )
    
    # 记录账单
    execute_sql(
        "INSERT INTO token_bills (customer_id, type, amount, description, created_at) VALUES (%s, %s, %s, %s, NOW())",
        (customer['id'], 'recharge', request.amount, f'账户充值 {request.amount}元')
    )
    
    return {
        "success": True,
        "message": f"充值成功，已充值 {request.amount} 元",
        "amount": request.amount
    }


@app.get("/api/token/bill", summary="获取账单")
async def token_bill(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """获取账单记录"""
    from customers import verify_api_key
    from database import fetch_all, fetch_one
    
    customer = await verify_api_key(x_api_key)
    
    bills = fetch_all(
        "SELECT DATE(created_at) as date, type, amount FROM token_bills WHERE customer_id = %s ORDER BY created_at DESC LIMIT 50",
        (customer['id'],)
    )
    
    return {
        "success": True,
        "bills": bills or [],
        "total": len(bills) if bills else 0
    }


@app.get("/api/token/info", summary="获取API信息")
async def token_info():
    """获取API基本信息"""
    return {
        "success": True,
        "version": "1.0.0",
        "name": "政策通 Token API",
        "description": "政策数据Token化基础设施",
        "endpoints": {
            "register": "POST /api/token/register - 注册客户",
            "recharge": "POST /api/token/recharge - 账户充值",
            "query": "POST /api/token/query - 基础查询(0.1元/次)",
            "query_advanced": "POST /api/token/query/advanced - 高级查询(0.5元/次)",
            "balance": "GET /api/token/balance - 查询余额",
            "usage": "GET /api/token/usage - 用量统计",
            "bill": "GET /api/token/bill - 账单记录",
            "info": "GET /api/token/info - API信息"
        },
        "pricing": {
            "basic_query": 0.1,
            "advanced_query": 0.5,
            "currency": "CNY"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

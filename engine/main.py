"""
政策通 PolicyPilot - FastAPI 后端服务
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel
import os

from models import MatchRequest, MatchResponse, Policy
from matcher import PolicyMatcher
from generator import MaterialGenerator
from auth import register, login, get_current_user, get_user_info
from database import save_diagnosis_result, get_user_results, get_result_by_id


# 全局实例
matcher: PolicyMatcher = None
generator: MaterialGenerator = None


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
    version="1.2.0",
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
        "version": "1.1.0",
        "description": "AI政策补贴自动匹配与申报辅助工具",
        "endpoints": {
            "match": "POST /match - 匹配企业政策",
            "policies": "GET /policies - 获取所有政策",
            "policy_detail": "GET /policy/{id} - 获取政策详情",
            "register": "POST /register - 用户注册",
            "login": "POST /login - 用户登录",
            "generate_materials": "POST /generate-materials - 生成申报材料"
        }
    }


# ========== 原有API ==========

@app.post("/match", response_model=MatchResponse)
async def match_policies(request: MatchRequest):
    """匹配企业适用的政策"""
    try:
        matched = matcher.match(request.company)
        
        highly_recommended = [m for m in matched if m.is_highly_recommended]
        
        # 如果用户已登录，自动保存诊断结果
        # 注：在API层面暂不处理，由前端调用 save_result 接口
        
        return MatchResponse(
            company_name=request.company.name,
            total_matches=len(matched),
            highly_recommended_count=len(highly_recommended),
            matched_policies=matched
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配出错: {str(e)}")


@app.get("/policies", response_model=list[Policy])
async def get_policies(district: str = None, category: str = None):
    """获取政策列表"""
    if district:
        return matcher.get_policies_by_district(district)
    if category:
        return matcher.get_policies_by_category(category)
    return matcher.get_all_policies()


@app.get("/policy/{policy_id}", response_model=Policy)
async def get_policy_detail(policy_id: str):
    """获取政策详情"""
    policy = matcher.get_policy_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="未找到该政策")
    return policy


# ========== 认证API ==========

class RegisterRequest(BaseModel):
    phone: str
    verify_code: Optional[str] = "123456"


class LoginRequest(BaseModel):
    phone: str
    verify_code: Optional[str] = "123456"


@app.post("/register")
async def user_register(request: RegisterRequest):
    """用户注册"""
    result = register(request.phone, request.verify_code)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return result


@app.post("/login")
async def user_login(request: LoginRequest):
    """用户登录"""
    result = login(request.phone, request.verify_code)
    if not result['success']:
        raise HTTPException(status_code=401, detail=result['message'])
    return result


@app.get("/user/info")
async def get_user_info_endpoint(authorization: Optional[str] = Header(None)):
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
        "user": get_user_info(user['id'])
    }


# ========== 诊断结果API ==========

class SaveResultRequest(BaseModel):
    company: dict
    match_result: dict


@app.post("/user/result")
async def save_result(
    request: SaveResultRequest,
    authorization: Optional[str] = Header(None)
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
        "result_id": result_id
    }


@app.get("/user/results")
async def get_results(authorization: Optional[str] = Header(None)):
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
        "total": len(results)
    }


@app.get("/user/result/{result_id}")
async def get_result_detail(
    result_id: int,
    authorization: Optional[str] = Header(None)
):
    """获取诊断结果详情"""
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    
    result = get_result_by_id(result_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="未找到该诊断结果")
    
    return {
        "success": True,
        "result": result
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
async def generate_materials(request: GenerateMaterialsRequest):
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
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成申报材料出错: {str(e)}")


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

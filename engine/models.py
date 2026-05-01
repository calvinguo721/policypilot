"""
数据模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class PolicyCondition(BaseModel):
    """政策条件"""
    industry: List[str] = Field(default_factory=list, description="适用行业")
    scale: List[str] = Field(default_factory=list, description="企业规模")
    region: List[str] = Field(default_factory=list, description="适用区域")
    other: List[str] = Field(default_factory=list, description="其他条件")


class Policy(BaseModel):
    """政策模型"""
    id: str = Field(..., description="政策ID")
    name: str = Field(..., description="政策名称")
    district: str = Field(..., description="所属区")
    department: str = Field(..., description="发布部门")
    category: str = Field(..., description="政策类别")
    subsidy_amount: str = Field(..., description="补贴金额说明")
    subsidy_ratio: str = Field(..., description="补贴比例/方式")
    conditions: PolicyCondition = Field(..., description="申报条件")
    requirements: List[str] = Field(default_factory=list, description="基本要求")
    deadline: str = Field(..., description="申报时间")
    materials: List[str] = Field(default_factory=list, description="申报材料")
    max_amount: float = Field(0, description="最高金额(万元)")
    min_amount: float = Field(0, description="最低金额(万元)")
    link: str = Field("", description="政策原文链接")
    description: str = Field("", description="政策描述")


class CompanyInfo(BaseModel):
    """企业信息模型"""
    name: str = Field(..., description="企业名称")
    district: str = Field(..., description="所属区：海珠/天河")
    industry: str = Field(..., description="所属行业")
    established_years: int = Field(..., ge=0, description="成立年限")
    revenue_scale: str = Field(..., description="营收规模：小于500万/500-2000万/2000万-1亿/1亿以上")
    employee_count: int = Field(..., ge=0, description="员工数量")
    has_ip: bool = Field(False, description="是否有知识产权")
    is_high_tech: bool = Field(False, description="是否高新技术企业")
    is_specialized: bool = Field(False, description="是否专精特新企业")
    has_vc_investment: bool = Field(False, description="是否有风险投资")


class MatchedPolicy(BaseModel):
    """匹配结果模型"""
    policy: Policy
    match_score: float = Field(..., ge=0, le=100, description="匹配度评分(0-100)")
    match_reasons: List[str] = Field(default_factory=list, description="匹配原因")
    is_highly_recommended: bool = Field(False, description="是否重点推荐")


class MatchRequest(BaseModel):
    """匹配请求"""
    company: CompanyInfo


class MatchResponse(BaseModel):
    """匹配响应"""
    company_name: str
    total_matches: int
    highly_recommended_count: int
    matched_policies: List[MatchedPolicy]
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

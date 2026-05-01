"""
政策匹配引擎
"""
import json
import os
from typing import List, Dict, Tuple
from models import Policy, CompanyInfo, MatchedPolicy


class PolicyMatcher:
    """政策匹配器"""

    # 行业关键词映射（已扩充支持更多行业）
    INDUSTRY_KEYWORDS = {
        "人工智能": ["ai", "人工智能", "大模型", "机器学习", "深度学习", "算法", "智能", "科技"],
        "软件": ["软件", "开发", "it", "互联网", "云计算", "saas", "app", "工业软件"],
        "制造业": ["制造", "工业", "生产", "工厂", "加工", "制造", "装备"],
        "电子商务": ["电商", "零售", "商贸", "批发", "销售"],
        "科技服务": ["研发", "设计", "检测", "咨询", "服务"],
        "生物医药": ["生物", "医药", "医疗", "健康", "医疗器械", "药品"],
        "新一代信息技术": ["电子", "通信", "信息", "半导体", "集成电路", "芯片"],
        "新材料": ["材料", "化工", "新材料", "新能源材料"],
        "节能环保": ["环保", "节能", "绿色", "清洁", "低碳", "碳排放"],
        "现代农业": ["农业", "种植", "养殖", "农产品", "农机"],
        "文化创意": ["文化", "创意", "设计", "传媒", "影视", "动漫", "旅游"],
        "现代金融": ["金融", "银行", "保险", "证券", "基金", "投资"],
        "人力资源": ["人力资源", "人才", "猎头", "招聘", "劳务"],
        "专业服务": ["法律", "会计", "审计", "税务", "咨询", "评估", "检测"],
        "平台经济": ["平台", "共享", "众包", "灵活用工"],
        "跨境电商": ["跨境", "外贸", "进出口", "海关"],
        "军民融合": ["军民", "军工", "国防"],
        "低空经济": ["低空", "航空", "无人机", "通用航空"],
        "都市工业": ["都市工业", "楼宇工业", "工业上楼"],
        "其他": ["不限", "其他", "创业扶持", "人才补贴", "融资支持", "技改奖励", "知识产权", "税收优惠", "研发资助", "租金减免", "创业"]
    }
    
    # 政策类别关键词映射（新增）
    CATEGORY_KEYWORDS = {
        "创业扶持": ["创业", "创办", "开公司", "初创", "孵化", "众创空间", "创业大赛", "创业培训", "独角兽", "瞪羚"],
        "人才补贴": ["人才", "引进", "补贴", "安家", "博士", "博士后", "高层次", "领军人才", "青年人才", "毕业生", "入户"],
        "融资支持": ["融资", "贷款", "贴息", "担保", "投资", "上市", "上市后备", "风投", "创投", "信贷"],
        "研发资助": ["研发", "科研", "创新", "技术攻关", "产学研", "实验室", "研发中心", "新型研发机构"],
        "技改奖励": ["技术改造", "设备更新", "机器换人", "智能制造", "数字化转型", "绿色制造", "节能改造"],
        "知识产权": ["专利", "商标", "著作权", "版权", "知识产权", "贯标", "专利奖", "标准制定"],
        "税收优惠": ["税收", "减免", "加计扣除", "所得税", "增值税", "退税", "免税"],
        "租金减免": ["租金", "场地", "办公", "入驻", "免租", "房租", "孵化器"],
        "AI大模型": ["人工智能", "大模型", "AI", "算法", "机器学习"],
        "软件": ["软件", "IT", "互联网", "云计算"],
        "集成电路": ["集成电路", "芯片", "半导体", "IC"],
        "都市工业": ["都市工业", "楼宇工业"],
        "工业软件": ["工业软件", "CAD", "CAE", "ERP", "MES"],
        "数字化转型": ["数字化", "数字化转型", "四化", "上云", "工业互联网"],
        "专精特新": ["专精特新", "小巨人", "单项冠军"],
        "前沿产业": ["前沿", "未来产业", "战略性新兴产业"]
    }

    # 营收规模映射
    REVENUE_SCALES = {
        "小于500万": {"min": 0, "max": 500, "level": 1},
        "500-2000万": {"min": 500, "max": 2000, "level": 2},
        "2000万-1亿": {"min": 2000, "max": 10000, "level": 3},
        "1亿以上": {"min": 10000, "max": float('inf'), "level": 4}
    }

    def __init__(self, policies_file: str = None):
        """初始化匹配器"""
        if policies_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            policies_file = os.path.join(base_dir, "data", "policies.json")
        
        with open(policies_file, 'r', encoding='utf-8') as f:
            self.policies = [Policy(**p) for p in json.load(f)]

    def _normalize_industry(self, industry: str) -> List[str]:
        """标准化行业分类"""
        industry_lower = industry.lower()
        matched = []
        for category, keywords in self.INDUSTRY_KEYWORDS.items():
            if any(kw in industry_lower for kw in keywords):
                matched.append(category)
        if not matched:
            matched = ["其他"]
        return matched

    def _check_region_match(self, company_district: str, policy: Policy) -> bool:
        """检查区域是否匹配"""
        policy_district = policy.district
        # 如果是省级或国家级政策（广东省），则全市企业都适用
        if "广东省" in policy_district or "省级" in policy_district:
            return True
        # 如果是广州市级政策，则全市企业都适用
        if "广州市" in policy_district:
            return True
        # 如果企业所在区在政策适用区域
        if company_district in policy_district:
            return True
        return False

    def _check_industry_match(self, company_industries: List[str], policy: Policy) -> Tuple[bool, str]:
        """检查行业是否匹配"""
        policy_industries = policy.conditions.industry
        
        # 如果政策不限行业，直接匹配
        if "不限" in policy_industries:
            return True, "行业不限"
        
        # 检查是否有人工智能相关
        for company_ind in company_industries:
            if company_ind == "人工智能":
                for policy_ind in policy_industries:
                    if any(ai_kw in policy_ind.lower() for ai_kw in ["人工智能", "软件", "科技", "信息"]):
                        return True, f"符合AI/软件行业要求"
            
            if company_ind == "软件":
                for policy_ind in policy_industries:
                    if any(sw in policy_ind.lower() for sw in ["软件", "it", "互联网", "信息技术", "信息传输"]):
                        return True, f"符合软件行业要求"
            
            if company_ind == "制造业":
                for policy_ind in policy_industries:
                    if any(m in policy_ind for m in ["制造", "工业"]):
                        return True, f"符合制造业要求"
        
        # 直接匹配
        for company_ind in company_industries:
            if company_ind in policy_industries:
                return True, f"属于{company_ind}行业"
        
        return False, ""

    def _calculate_base_score(self, company: CompanyInfo, policy: Policy) -> float:
        """计算基础匹配分数"""
        score = 0.0
        reasons = []

        # 1. 区域匹配 (30分)
        if self._check_region_match(company.district, policy):
            score += 30
            reasons.append(f"位于{company.district}区，政策适用")

        # 2. 行业匹配 (30分)
        company_industries = self._normalize_industry(company.industry)
        industry_match, reason = self._check_industry_match(company_industries, policy)
        if industry_match:
            score += 30
            reasons.append(reason)

        # 3. 企业资质加成
        qualification_score = 0
        if company.is_high_tech:
            qualification_score += 10
            reasons.append("高新技术企业资质")
        
        if company.is_specialized:
            qualification_score += 15
            reasons.append("专精特新企业资质")
        
        if company.has_ip:
            qualification_score += 5
            reasons.append("拥有知识产权")
        
        if company.has_vc_investment:
            qualification_score += 5
            reasons.append("获得风险投资")

        # 4. 规模匹配加成 (10分)
        if company.established_years <= 3:
            # 初创企业加成
            for condition in policy.conditions.other:
                if any(kw in condition for kw in ["初创", "创业", "小微", "首", "新成立"]):
                    score += 5
                    reasons.append("初创/小微企业适用")
                    break
        
        # 大企业加成
        if company.revenue_scale == "1亿以上":
            for condition in policy.conditions.other:
                if any(kw in condition for kw in ["龙头", "规模以上", "大型", "营收亿"]):
                    score += 5
                    reasons.append("大型企业适用")
                    break

        # 5. 专精特新专项匹配
        if company.is_specialized:
            if "专精特新" in policy.name or "专精特新" in policy.category:
                score += 10
                reasons.append("专精特新专项政策")

        # 6. 高新企业专项匹配
        if company.is_high_tech:
            if "高新技术" in policy.name or "高新技术" in policy.category:
                score += 10
                reasons.append("高新技术企业专项政策")

        # 7. 研发/创新企业加成
        if company.has_ip or company.established_years <= 5:
            for condition in policy.conditions.other:
                if any(kw in condition for kw in ["研发", "创新", "专利", "自主知识产权"]):
                    score += 5
                    reasons.append("研发/创新型企业适用")
                    break

        score += min(qualification_score, 20)  # 资质加成最高20分

        return min(score, 100), reasons

    def _is_highly_recommended(self, score: float, policy: Policy) -> bool:
        """判断是否重点推荐"""
        if score >= 70:
            return True
        
        # 特定高价值政策优先推荐
        high_value_keywords = [
            "备案", "认定", "专精特新", "小巨人", "高新技术",
            "首升规", "单项冠军", "独角兽", "流片", "EDA"
        ]
        
        if any(kw in policy.name for kw in high_value_keywords):
            if score >= 50:
                return True
        
        return False

    def match(self, company: CompanyInfo) -> List[MatchedPolicy]:
        """匹配企业适用的政策"""
        results = []
        company_industries = self._normalize_industry(company.industry)

        for policy in self.policies:
            score, reasons = self._calculate_base_score(company, policy)
            
            if score > 0:  # 有任何匹配就返回
                matched = MatchedPolicy(
                    policy=policy,
                    match_score=round(score, 1),
                    match_reasons=reasons,
                    is_highly_recommended=self._is_highly_recommended(score, policy)
                )
                results.append(matched)

        # 按匹配度和金额排序
        results.sort(key=lambda x: (x.match_score, x.policy.max_amount), reverse=True)

        return results

    def get_policy_by_id(self, policy_id: str) -> Policy:
        """根据ID获取政策详情"""
        for policy in self.policies:
            if policy.id == policy_id:
                return policy
        return None

    def get_all_policies(self) -> List[Policy]:
        """获取所有政策"""
        return self.policies

    def get_policies_by_district(self, district: str) -> List[Policy]:
        """根据区获取政策"""
        return [p for p in self.policies if district in p.district]

    def get_policies_by_category(self, category: str) -> List[Policy]:
        """根据类别获取政策"""
        return [p for p in self.policies if category in p.category]

"""
政策通 PolicyPilot - AI Agent 核心服务
申报导航仪，不是搜索工具
"""
import os
import re
import json
import uuid
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# LLM配置（可配置）
LLM_CONFIG = {
    "provider": "deepseek",  # deepseek / siliconflow / groq / qwen / ollama
    "model": "deepseek-chat",
    "timeout": 30
}


@dataclass
class CompanyProfile:
    """企业画像"""
    district: Optional[str] = None  # 海珠区/天河区
    industry: Optional[str] = None  # 行业
    scale: Optional[str] = None  # 初创/小微/中型
    revenue: Optional[str] = None  # 营收规模
    qualifications: List[str] = field(default_factory=list)  # 资质列表
    established_years: Optional[int] = None  # 成立年限
    company_name: Optional[str] = None  # 企业名称


class PolicyAgent:
    """政策通AI Agent - 申报导航仪"""
    
    def __init__(self, matcher):
        self.matcher = matcher
        self.llm_client = None
        self._init_llm()
    
    def _init_llm(self):
        """初始化LLM客户端"""
        # 优先级：自定义Base URL > DeepSeek > SiliconFlow > Ollama > 环境变量
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")  # 支持自定义API endpoint
        
        # 检查是否使用本地Ollama
        use_ollama = os.getenv("USE_OLLAMA", "false").lower() == "true"
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        
        if use_ollama:
            try:
                self.llm_client = OpenAI(
                    api_key="ollama",  # Ollama不需要真实API key
                    base_url=ollama_base_url
                )
                LLM_CONFIG["provider"] = "ollama"
                LLM_CONFIG["model"] = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
                print(f"✅ LLM已配置：Ollama本地模型 ({LLM_CONFIG['model']})")
                return
            except Exception as e:
                print(f"⚠️ Ollama配置失败：{e}")
        
        if not api_key:
            print("⚠️ 未检测到LLM API Key，将使用规则匹配模式")
            return
        
        try:
            from openai import OpenAI
            
            # 自定义Base URL（支持Pekpik等代理）
            if base_url:
                self.llm_client = OpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
                LLM_CONFIG["model"] = "deepseek-chat"
                LLM_CONFIG["provider"] = "custom"
                print(f"✅ LLM已配置：自定义API ({base_url})")
                return
            
            # DeepSeek配置
            if os.getenv("DEEPSEEK_API_KEY"):
                self.llm_client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com"
                )
                LLM_CONFIG["model"] = "deepseek-chat"
                LLM_CONFIG["provider"] = "deepseek"
                print("✅ LLM已配置：DeepSeek")
                return
            
            # SiliconFlow配置
            if os.getenv("SILICONFLOW_API_KEY"):
                self.llm_client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.siliconflow.cn/v1"
                )
                LLM_CONFIG["model"] = "deepseek-ai/DeepSeek-V3"
                LLM_CONFIG["provider"] = "siliconflow"
                print("✅ LLM已配置：SiliconFlow")
                return
            
            # 默认OpenAI兼容接口
            self.llm_client = OpenAI(api_key=api_key)
            LLM_CONFIG["provider"] = "openai"
            print("✅ LLM已配置：OpenAI兼容接口")
            
        except ImportError:
            print("⚠️ openai库未安装，使用规则匹配模式")
        except Exception as e:
            print(f"⚠️ LLM初始化失败：{e}，使用规则匹配模式")
    
    def chat(self, user_message: str, session_id: str = None) -> Dict:
        """
        处理用户对话
        """
        # 1. 提取企业信息
        profile = self._extract_company_info(user_message)
        
        # 2. 匹配政策
        policies = []
        if profile:
            company_info = self._build_company_info(profile)
            matched = self.matcher.match(company_info)
            policies = [self._format_policy(p) for p in matched[:5]]
        
        # 2.5 检查区域覆盖
        if profile and profile.district and policies:
            # 检查匹配的政策是否真的属于用户所在区域
            user_district = profile.district
            same_region_policies = [p for p in policies if user_district in p.get("district", "") or "国家级" in p.get("district", "")]
            # 如果用户指定了区域但没有任何同区域政策
            guangzhou_districts = ["海珠区", "天河区", "白云区", "番禺区", "越秀区", "荔湾区", "黄埔区", "花都区", "南沙区", "增城区", "从化区"]
            is_guangzhou = user_district in guangzhou_districts or "广州" in user_district or "广东" in user_district
            if not is_guangzhou and not same_region_policies:
                reply = f"抱歉，目前政策数据库暂未覆盖【{user_district}】的区域政策 😔\n\n"
                reply += "当前已覆盖区域：广州市各区（海珠区、天河区、白云区、番禺区等）\n\n"
                if policies:
                    reply += "💡 以下省级/国家级政策可能对您也适用：\n\n"
                    reply += self._format_policy_list_text(policies[:3])
                    reply += "\n\n我们正在持续扩展全国政策数据，敬请期待！"
                else:
                    reply += "我们正在持续扩展全国政策数据，敬请期待！"
                return {
                    "reply": reply,
                    "policies": policies[:3] if policies else [],
                    "profile": profile.__dict__,
                    "suggestions": ["查询广州市政策", "查询海珠区AI创业补贴", "了解广东省政策"],
                    "session_id": session_id or self._generate_session_id()
                }
        
        # 3. 生成回复 - 优先使用LLM
        reply = self._generate_reply_with_llm(user_message, profile, policies)
        
        return {
            "reply": reply,
            "policies": policies,
            "profile": profile.__dict__ if profile else {},
            "suggestions": self._generate_suggestions(profile, policies),
            "session_id": session_id or self._generate_session_id()
        }
    
    def _generate_reply_with_llm(self, message: str, profile: Optional[CompanyProfile], policies: List) -> str:
        """使用LLM生成回复（带fallback）"""
        if not self.llm_client:
            return self._generate_reply(message, profile, policies)
        
        # 如果没有政策，使用简单的提示回复
        if not policies:
            return self._generate_reply(message, profile, policies)
        
        try:
            # 构建prompt让LLM解读政策
            profile_desc = self._build_profile_description(profile)
            
            # 构建政策信息摘要
            policies_summary = self._build_policies_summary(policies)
            
            system_prompt = """你是一个专业的政策申报顾问，擅长用通俗易懂的语言解读政策。

你的职责：
1. 用一句话总结政策核心内容
2. 把申报条件翻译成普通人能听懂的话
3. 根据用户画像判断用户是否满足条件
4. 给出实用建议

回复要求：
- 语言简洁友好，像朋友聊天
- 避免太官方的措辞
- 重点突出用户关心的补贴金额
- 如果用户可能不满足某些条件，要诚实指出

回复格式：
先说结论，再说详细解释，最后给建议。"""
            
            user_prompt = f"""用户情况：{profile_desc}

匹配到的政策：
{policies_summary}

请用友好的方式向用户介绍这些政策，告诉他们：
1. 这些政策是关于什么的（一句话总结）
2. 他们是否符合申请条件
3. 需要特别注意什么"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 使用fallback机制：DeepSeek → 备用Key → Ollama
            llm_reply = None
            try:
                from llm_fallback import get_llm_fallback
                fallback = get_llm_fallback()
                llm_reply = fallback.chat(messages, temperature=0.7, max_tokens=800)
            except ImportError:
                # fallback模块不存在时用原始方式
                if self.llm_client:
                    response = self.llm_client.chat.completions.create(
                        model=LLM_CONFIG["model"],
                        messages=messages,
                        temperature=0.7,
                        max_tokens=800,
                        timeout=LLM_CONFIG.get("timeout", 30)
                    )
                    llm_reply = response.choices[0].message.content.strip()
            
            if llm_reply:
                llm_reply += f"\n\n📋 为您匹配到 {len(policies)} 条政策，点击下方卡片查看详情 👇"
                return llm_reply
            
            return self._generate_reply(message, profile, policies)
            
        except Exception as e:
            print(f"⚠️ LLM生成回复失败：{e}，使用规则模式")
            return self._generate_reply(message, profile, policies)
    
    def _build_profile_description(self, profile: Optional[CompanyProfile]) -> str:
        """构建用户画像描述"""
        if not profile:
            return "未提供详细信息"
        
        parts = []
        if profile.district:
            parts.append(f"位于{profile.district}")
        if profile.industry:
            parts.append(f"属于{profile.industry}行业")
        if profile.scale:
            parts.append(f"企业规模：{profile.scale}")
        if profile.established_years:
            parts.append(f"成立约{profile.established_years}年")
        if profile.qualifications:
            parts.append(f"已获得资质：{', '.join(profile.qualifications)}")
        
        return "，".join(parts) if parts else "初创小企业"
    
    def _build_policies_summary(self, policies: List) -> str:
        """构建政策摘要"""
        lines = []
        for i, p in enumerate(policies[:5], 1):
            name = p.get('name', '未知政策')
            district = p.get('district', '')
            category = p.get('category', '')
            subsidy = p.get('subsidy_amount', '面议')
            deadline = p.get('deadline', '请关注官方通知')
            
            lines.append(f"{i}. {name}")
            lines.append(f"   区域：{district} | 类别：{category}")
            lines.append(f"   补贴：{subsidy}")
            lines.append(f"   截止：{deadline}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _extract_company_info(self, text: str) -> Optional[CompanyProfile]:
        """从文本中提取企业信息"""
        profile = CompanyProfile()
        
        # 区域提取 - 全国覆盖
        districts = {
            # 广州各区
            "海珠": "海珠区", "天河": "天河区", "白云": "白云区",
            "番禺": "番禺区", "越秀": "越秀区", "荔湾": "荔湾区",
            "黄埔": "黄埔区", "花都": "花都区", "南沙": "南沙区",
            "增城": "增城区", "从化": "从化区",
            # 深圳各区
            "南山": "南山区", "福田": "福田区", "罗湖": "罗湖区",
            "宝安": "宝安区", "龙岗": "龙岗区", "龙华": "龙华区",
            "坪山": "坪山区", "光明": "光明区", "盐田": "盐田区",
            # 北京各区
            "海淀": "海淀区", "朝阳": "朝阳区", "西城": "西城区",
            "东城": "东城区", "丰台": "丰台区", "通州": "通州区",
            "大兴": "大兴区", "顺义": "顺义区", "昌平": "昌平区",
            "北京": "北京市",
            # 上海各区
            "浦东": "浦东新区", "黄浦": "黄浦区", "徐汇": "徐汇区",
            "长宁": "长宁区", "静安": "静安区", "普陀": "普陀区",
            "虹口": "虹口区", "杨浦": "杨浦区", "闵行": "闵行区",
            "上海": "上海市",
            # 其他重点城市
            "杭州": "杭州市", "南京": "南京市", "苏州": "苏州市",
            "成都": "成都市", "武汉": "武汉市", "长沙": "长沙市",
            "重庆": "重庆市", "天津": "天津市", "西安": "西安市",
            "郑州": "郑州市", "合肥": "合肥市", "青岛": "青岛市",
            "厦门": "厦门市", "东莞": "东莞市", "佛山": "佛山市",
            "珠海": "珠海市", "惠州": "惠州市", "中山": "中山市",
            # 省级
            "广东": "广东省", "浙江": "浙江省", "江苏": "江苏省",
            "山东": "山东省", "四川": "四川省", "湖北": "湖北省",
            "福建": "福建省", "湖南": "湖南省", "河南": "河南省",
            "河北": "河北省", "安徽": "安徽省", "江西": "江西省",
        }
        for keyword, district in districts.items():
            if keyword in text:
                profile.district = district
                break
        
        # 行业提取
        industries = {
            "AI|人工智能|大模型|机器学习|算法|ChatGPT|AIGC|生成式AI": "人工智能",
            "软件|IT|互联网|云计算|SaaS|程序员": "软件和信息技术服务业",
            "制造|工业|工厂|生产|装备": "制造业",
            "电商|零售|商贸|批发|销售": "电子商务",
            "生物|医药|医疗|健康|医疗器械|药品": "生物医药",
            "电子|通信|半导体|芯片|集成电路|5G": "新一代信息技术",
            "文化|创意|设计|传媒|影视|动漫|游戏": "文化创意",
            "环保|节能|绿色|清洁|低碳": "节能环保",
            "农业|种植|养殖|农产品|农机": "现代农业"
        }
        for pattern, industry in industries.items():
            if re.search(pattern, text, re.IGNORECASE):
                profile.industry = industry
                break
        
        # 规模提取
        if "初创" in text or "创业" in text or "刚成立" in text:
            profile.scale = "初创"
            profile.established_years = 1
        elif "小微" in text or "小规模" in text:
            profile.scale = "小微"
        
        # 营收提取
        revenues = {
            ("小于500万", "500万以下", "500万以内"): "小于500万",
            ("500-2000万", "500万到2000万"): "500-2000万",
            ("2000万-1亿", "2000万到1亿"): "2000万-1亿",
            ("1亿以上", "1亿以上", "上亿"): "1亿以上"
        }
        for patterns, revenue in revenues.items():
            if any(p in text for p in patterns):
                profile.revenue = revenue
                break
        
        # 资质提取
        qualifications = []
        if any(k in text for k in ["高新", "高新技术企业", "国高"]):
            qualifications.append("高新技术企业")
        if "专精特新" in text or "小巨人" in text:
            qualifications.append("专精特新")
        if "知识产权" in text or "专利" in text or "软著" in text:
            qualifications.append("知识产权")
        if any(k in text for k in ["风投", "VC", "创投", "融资"]):
            qualifications.append("风险投资")
        profile.qualifications = qualifications
        
        # 只有当提取到关键信息时才返回
        if profile.district or profile.industry:
            return profile
        
        return None
    
    def _build_company_info(self, profile: CompanyProfile):
        """构建匹配器所需的企业信息"""
        from models import CompanyInfo
        
        return CompanyInfo(
            name=profile.company_name or "用户企业",
            district=profile.district or "",
            industry=profile.industry or "",
            established_years=profile.established_years or 1,
            revenue_scale=profile.revenue or "小于500万",
            employee_count=10,
            has_ip="知识产权" in profile.qualifications,
            is_high_tech="高新技术企业" in profile.qualifications,
            is_specialized="专精特新" in profile.qualifications,
            has_vc_investment="风险投资" in profile.qualifications
        )
    
    def _format_policy(self, matched) -> Dict:
        """格式化政策数据"""
        policy = matched.policy
        subsidy_text = policy.subsidy_amount if policy.subsidy_amount else "按条件奖励"
        
        return {
            "id": policy.id,
            "name": policy.name,
            "district": policy.district,
            "category": policy.category,
            "subsidy_amount": subsidy_text,
            "subsidy_ratio": policy.subsidy_ratio or "",
            "match_score": matched.match_score,
            "match_reasons": matched.match_reasons,
            "match_reason_text": "；".join(matched.match_reasons) if matched.match_reasons else "",
            "deadline": policy.deadline or "请关注官方通知",
            "link": policy.link or "",
            "is_highly_recommended": matched.is_highly_recommended,
            "department": policy.department or "",
            "max_amount": policy.max_amount or 0,
            "min_amount": policy.min_amount or 0,
            "conditions": {
                "region": policy.conditions.region if hasattr(policy, 'conditions') and policy.conditions else [],
                "industry": policy.conditions.industry if hasattr(policy, 'conditions') and policy.conditions else [],
                "scale": policy.conditions.scale if hasattr(policy, 'conditions') and policy.conditions else [],
                "other": policy.conditions.other if hasattr(policy, 'conditions') and policy.conditions else []
            }
        }
    
    def _generate_reply(self, message: str, profile: Optional[CompanyProfile], policies: List) -> str:
        """生成AI回复（规则模式fallback）"""
        if not profile:
            return """好的！我来帮您分析适合的政策。

为了给您更精准的推荐，请告诉我更多信息：
- 📍 您的企业所在区域（海珠区/天河区/其他）
- 🏢 企业类型（AI/软件/制造/电商等）
- 📊 企业规模（初创/小微/中型）

比如您可以说：
• "我是海珠区的AI创业公司"
• "天河区软件企业有什么补贴"
• "专精特新企业怎么申报" """
        
        # 构建用户画像描述
        profile_desc = []
        if profile.district:
            profile_desc.append(f"{profile.district}")
        if profile.industry:
            profile_desc.append(f"{profile.industry}")
        if profile.scale:
            profile_desc.append(f"{profile.scale}企业")
        if profile.qualifications:
            profile_desc.append("、".join(profile.qualifications))
        
        profile_text = "".join(profile_desc)
        
        if not policies:
            return f"""根据您描述的【{profile_text}】情况，我在当前政策库中暂未找到完全匹配的政策。

💡 建议您：
• 提供更多企业信息（如营收规模）
• 尝试其他区域或行业关键词
• 或直接告诉我您想申报的具体政策类型

需要我帮您分析其他情况吗？"""
        
        count = len(policies)
        highly = sum(1 for p in policies if p.get("is_highly_recommended"))
        
        return f"""根据您的情况【{profile_text}】，为您找到 **{count}条** 匹配政策 ✅

其中 **{highly}条** 为重点推荐 👇

{self._format_policies_text(policies)}

您想了解哪条政策的详细申报条件？或者需要我帮您生成申报材料吗？"""
    
    def _format_policies_text(self, policies: List) -> str:
        """格式化政策列表为文本"""
        lines = []
        for i, p in enumerate(policies[:5], 1):
            score = int(p.get("match_score", 0))
            stars = "⭐" * min(max(score // 20, 1), 5)
            recommended = "🏆" if p.get("is_highly_recommended") else "📋"
            lines.append(f"""
{recommended} **{i}. {p['name']}** {stars}
   • 区域：{p['district']} | 类别：{p['category']}
   • 💰 补贴：{p['subsidy_amount']}
   • ⏰ 申报：{p['deadline']}""")
        return "\n".join(lines)
    
    def _generate_suggestions(self, profile: Optional[CompanyProfile], policies: List) -> List[str]:
        """生成后续建议"""
        suggestions = [
            "查看详细申报条件",
            "生成申报材料",
            "了解申报截止时间"
        ]
        if profile and profile.district:
            suggestions.append(f"探索{profile.district}更多政策")
        return suggestions
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return str(uuid.uuid4())[:8]
    
    def interpret_policy(self, policy_id: str, detail_level: str = "simple") -> Dict:
        """解读单条政策"""
        policy = self.matcher.get_policy_by_id(policy_id)
        if not policy:
            return None
        
        conditions = policy.conditions
        
        # 提取关键条件
        key_conditions = []
        if conditions.region and "不限" not in conditions.region:
            key_conditions.append(f"📍 区域：{', '.join(conditions.region)}")
        if conditions.industry and "不限" not in conditions.industry:
            key_conditions.append(f"🏢 行业：{', '.join(conditions.industry)}")
        if conditions.scale and "不限" not in conditions.scale:
            key_conditions.append(f"📊 规模：{', '.join(conditions.scale)}")
        for other in conditions.other:
            if other:
                key_conditions.append(f"📋 {other}")
        
        # 申报步骤
        steps = [
            "1️⃣ 准备申报材料",
            "2️⃣ 在线/线下提交申请",
            "3️⃣ 等待部门审核",
            "4️⃣ 公示后发放补贴"
        ]
        
        # 常见误区
        mistakes = [
            "❌ 以为有了备案就能拿钱 → 需要审核通过",
            "❌ 材料准备不齐全 → 对照清单逐一检查",
            "❌ 错过申报时间 → 提前关注截止日期"
        ]
        
        # 一句话总结
        summary = f"对符合条件的{policy.category}企业，提供{policy.subsidy_amount}的{policy.subsidy_ratio}。"
        
        # 谁能申请
        who_can = f"{policy.district}的{', '.join(conditions.industry) if conditions.industry and '不限' not in conditions.industry else '所有企业'}"
        
        return {
            "id": policy.id,
            "name": policy.name,
            "summary": summary,
            "who_can_apply": who_can,
            "how_much": policy.subsidy_amount,
            "key_conditions": key_conditions,
            "deadline": policy.deadline or "请关注官方通知",
            "steps": steps,
            "common_mistakes": mistakes,
            "materials": policy.materials or [],
            "requirements": policy.requirements or [],
            "department": policy.department,
            "link": policy.link,
            "detail_level": detail_level,
            "requires_upgrade": detail_level == "detailed"
        }
    
    def generate_interpretation(self, policy_id: str) -> Dict:
        """使用LLM生成政策解读"""
        return self.interpret_policy(policy_id, "simple")

    def _format_policy_list_text(self, policies: List) -> str:
        """格式化政策列表为纯文本"""
        lines = []
        for i, p in enumerate(policies, 1):
            lines.append(f"📋 {i}. {p.get('name', '未知政策')}")
            lines.append(f"   区域：{p.get('district', '')} | 类别：{p.get('category', '')}")
            if p.get('subsidy_amount'):
                lines.append(f"   💰 补贴：{p['subsidy_amount']}")
            lines.append("")
        return "\n".join(lines)


# 修复导入问题
from openai import OpenAI

"""
LLM Fallback 服务
当主LLM服务不可用时的回退方案
"""
import os
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


class LLMFallback:
    """LLM回退服务 - 提供本地化的政策解读能力"""
    
    def __init__(self):
        self.intent_keywords = {
            "补贴申请": ["申请", "补贴", "资助", "奖励", "扶持", "申报", "领取", "获取"],
            "资格查询": ["资格", "符合", "条件", "可以", "能否", "有没有", "能不能"],
            "金额计算": ["多少", "金额", "额度", "补贴多少", "资助多少", "奖励多少"],
            "流程指导": ["怎么", "如何", "流程", "步骤", "材料", "准备", "需要什么"],
            "时间查询": ["时间", "截止", "期限", "多久", "什么时候", "申报时间"],
            "条件解读": ["条件", "要求", "限制", "需要满足", "适用于"],
        }
        
        self.response_templates = {
            "welcome": "您好！我是政策通AI助手，根据您的情况，我为您解读以下政策：\n\n",
            "match_intro": "根据您的企业信息「{company_info}」，我为您匹配到以下政策：\n\n",
            "policy_intro": "📌 {policy_name}\n",
            "policy_amount": "💰 补贴金额：{amount}\n",
            "policy_conditions": "📋 适用条件：\n{conditions}\n",
            "policy_materials": "📦 申报材料：\n{materials}\n",
            "policy_deadline": "⏰ 申报时间：{deadline}\n",
            "policy_link": "🔗 政策原文：{link}\n",
            "summary": "\n📊 总结：{summary}\n",
            "advice": "\n💡 建议：{advice}\n",
            "closing": "\n如有更多问题，欢迎继续咨询！",
        }
    
    def analyze_intent(self, query: str) -> Dict[str, Any]:
        """分析用户查询意图"""
        query_lower = query.lower()
        matched_intents = []
        
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    matched_intents.append(intent)
                    break
        
        if not matched_intents:
            matched_intents = ["general_query"]
        
        return {
            "intents": matched_intents,
            "is_policy_related": True,  # 假设政策相关的
        }
    
    def generate_response(self, query: str, matched_policies: List[Dict], company_info: Dict = None) -> str:
        """生成AI解读响应"""
        if not matched_policies:
            return self._generate_no_match_response(query, company_info)
        
        response_parts = []
        
        # 开场白
        if company_info:
            company_desc = f"{company_info.get('district', '')}的{company_info.get('industry', '')}企业"
            response_parts.append(self.response_templates["welcome"])
            response_parts.append(self.response_templates["match_intro"].format(company_info=company_desc))
        else:
            response_parts.append(self.response_templates["welcome"])
        
        # 分析意图
        intent_info = self.analyze_intent(query)
        
        # 遍历匹配的政策
        for i, policy in enumerate(matched_policies[:5], 1):  # 最多展示5条
            policy_text = self._format_policy(policy, intent_info)
            response_parts.append(f"**{i}. {policy.get('name', '政策')[:50]}**\n")
            response_parts.append(policy_text)
            response_parts.append("\n---\n\n")
        
        # 总结和建议
        summary = self._generate_summary(matched_policies, intent_info)
        response_parts.append(self.response_templates["summary"].format(summary=summary))
        
        advice = self._generate_advice(matched_policies, intent_info)
        if advice:
            response_parts.append(self.response_templates["advice"].format(advice=advice))
        
        # 结束语
        response_parts.append(self.response_templates["closing"])
        
        return "".join(response_parts)
    
    def _format_policy(self, policy: Dict, intent_info: Dict) -> str:
        """格式化单个政策"""
        parts = []
        
        # 补贴金额
        if policy.get('subsidy_amount'):
            parts.append(self.response_templates["policy_amount"].format(
                amount=policy['subsidy_amount']
            ))
        
        # 条件摘要
        conditions = policy.get('conditions', {})
        if conditions:
            industry = conditions.get('industry', [])
            if industry:
                parts.append(f"行业：{', '.join(industry[:3])}\n")
        
        # 关键条件
        other_conditions = conditions.get('other', []) if conditions else []
        if other_conditions:
            key_conditions = [c for c in other_conditions if len(c) < 50][:3]
            if key_conditions:
                parts.append(self.response_templates["policy_conditions"].format(
                    conditions="\n".join(f"  • {c}" for c in key_conditions)
                ))
        
        # 申报材料
        materials = policy.get('materials', [])
        if materials and "申报材料" in intent_info.get('intents', []):
            parts.append(self.response_templates["policy_materials"].format(
                materials="\n".join(f"  • {m}" for m in materials[:5])
            ))
        
        # 申报时间
        if policy.get('deadline'):
            parts.append(self.response_templates["policy_deadline"].format(
                deadline=policy['deadline']
            ))
        
        # 链接
        if policy.get('link'):
            parts.append(self.response_templates["policy_link"].format(
                link=policy['link']
            ))
        
        return "".join(parts)
    
    def _generate_summary(self, policies: List[Dict], intent_info: Dict) -> str:
        """生成总结"""
        total = len(policies)
        
        # 计算总补贴金额
        total_amount = 0
        for p in policies:
            max_amt = p.get('max_amount', 0)
            if isinstance(max_amt, (int, float)) and max_amt > 0:
                total_amount += max_amt
        
        summaries = []
        
        if total > 0:
            summaries.append(f"共为您匹配到{total}条相关政策")
        
        if total_amount > 0:
            summaries.append(f"潜在最高补贴约{total_amount:.0f}万元")
        
        highly_recommended = [p for p in policies if p.get('match_score', 0) >= 70]
        if highly_recommended:
            summaries.append(f"其中{len(highly_recommended)}条为高度匹配")
        
        return "；".join(summaries) if summaries else "根据您的条件，暂未匹配到高度相关的政策"
    
    def _generate_advice(self, policies: List[Dict], intent_info: Dict) -> str:
        """生成建议"""
        advices = []
        
        # 基于意图的建议
        if "补贴申请" in intent_info.get('intents', []):
            # 检查是否有即将截止的政策
            urgent = [p for p in policies if '紧急' in p.get('deadline', '') or '近期' in p.get('deadline', '')]
            if urgent:
                advices.append("注意：有政策即将截止，请尽快申报")
        
        # 基于政策质量的建议
        highly_matched = [p for p in policies if p.get('match_score', 0) >= 70]
        if highly_matched:
            advices.append(f"优先关注{len(highly_matched)}条高度匹配的政策，成功率更高")
        
        # 基于企业资质的建议
        for p in policies[:3]:
            if '高新技术企业' in p.get('name', '') or '专精特新' in p.get('name', ''):
                advices.append("您具备相关资质，建议重点关注此政策")
                break
        
        return "；".join(advices) if advices else ""
    
    def _generate_no_match_response(self, query: str, company_info: Dict = None) -> str:
        """生成无匹配结果的响应"""
        response = "抱歉，根据您提供的信息，暂时没有匹配到适合的政策。\n\n"
        
        if company_info:
            response += "可能的原因：\n"
            if company_info.get('industry'):
                response += f"• 您的行业「{company_info.get('industry')}」可能暂时没有适用政策\n"
            if company_info.get('district'):
                response += f"• 所在区域「{company_info.get('district')}」的政策可能尚未收录\n"
        
        response += "\n💡 建议：\n"
        response += "• 尝试调整行业关键词或地区\n"
        response += "• 关注省级或国家级政策（适用范围更广）\n"
        response += "• 如有特殊资质（高新、专精特新等），可获得更多匹配\n"
        
        response += "\n\n如需了解更多政策，请随时告诉我您的具体情况！"
        
        return response
    
    def extract_company_info_from_query(self, query: str) -> Optional[Dict[str, str]]:
        """从查询中提取企业信息（简单的规则匹配）"""
        info = {}
        
        # 区域提取
        districts = ["海珠", "天河", "越秀", "荔湾", "白云", "黄埔", "番禺", "花都", "南沙", "从化", "增城"]
        for d in districts:
            if d in query:
                info['district'] = d + "区"
                break
        
        # 行业提取
        industries = ["人工智能", "软件", "互联网", "电子商务", "制造业", "生物医药", "新材料", "科技", "文化创意"]
        for ind in industries:
            if ind in query:
                info['industry'] = ind
                break
        
        return info if info else None


# 全局实例
llm_fallback = LLMFallback()

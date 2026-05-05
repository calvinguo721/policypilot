"""
AI Agent - 政策解读和智能问答代理
"""
import json
from typing import Dict, Any, List, Optional
from engine.llm_fallback import llm_fallback


class PolicyAgent:
    """政策智能代理"""
    
    def __init__(self, matcher=None):
        self.matcher = matcher
        self.llm = llm_fallback
        self.conversation_history: Dict[str, List[Dict]] = {}  # 按客户ID存储对话历史
    
    def process_query(self, query: str, customer_id: str = None, matched_policies: List[Dict] = None, 
                      company_info: Dict = None, conversation_id: str = None) -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            query: 用户查询文本
            customer_id: 客户ID（可选，用于存储对话历史）
            matched_policies: 已匹配的政策列表
            company_info: 企业信息
            conversation_id: 对话ID
            
        Returns:
            包含AI解读结果的字典
        """
        try:
            # 分析意图
            intent = self.llm.analyze_intent(query)
            
            # 生成响应
            response_text = self.llm.generate_response(
                query=query,
                matched_policies=matched_policies or [],
                company_info=company_info
            )
            
            # 提取企业信息
            extracted_info = self.llm.extract_company_info_from_query(query)
            
            # 保存对话历史
            if customer_id:
                self._save_conversation(
                    customer_id, 
                    query, 
                    response_text,
                    conversation_id
                )
            
            return {
                "success": True,
                "response": response_text,
                "intents": intent,
                "extracted_company_info": extracted_info,
                "matched_policies_count": len(matched_policies) if matched_policies else 0,
                "model": "policy_agent_v1_fallback",
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"处理查询时出错: {str(e)}"
            }
    
    def chat(self, query: str, customer_id: str = None, context: Dict = None) -> Dict[str, Any]:
        """
        对话模式 - 保持上下文
        """
        conversation_id = context.get("conversation_id") if context else None
        
        # 获取对话历史
        history = []
        if customer_id and conversation_id:
            history = self._get_conversation_history(customer_id, conversation_id)
        
        # 处理查询
        result = self.process_query(
            query=query,
            customer_id=customer_id,
            conversation_id=conversation_id
        )
        
        # 添加历史上下文
        if history:
            result["conversation_context"] = {
                "turns": len(history),
                "recent_policies_discussed": self._extract_discussed_policies(history)
            }
        
        return result
    
    def _save_conversation(self, customer_id: str, query: str, response: str, conversation_id: str = None):
        """保存对话到历史记录"""
        if not conversation_id:
            conversation_id = f"{customer_id}_{len(self.conversation_history.get(customer_id, []))}"
        
        if customer_id not in self.conversation_history:
            self.conversation_history[customer_id] = []
        
        self.conversation_history[customer_id].append({
            "conversation_id": conversation_id,
            "query": query,
            "response": response,
            "timestamp": self._get_timestamp()
        })
        
        # 限制历史记录长度
        if len(self.conversation_history[customer_id]) > 50:
            self.conversation_history[customer_id] = self.conversation_history[customer_id][-50:]
    
    def _get_conversation_history(self, customer_id: str, conversation_id: str = None) -> List[Dict]:
        """获取对话历史"""
        if customer_id not in self.conversation_history:
            return []
        
        history = self.conversation_history[customer_id]
        
        if conversation_id:
            history = [h for h in history if h.get("conversation_id") == conversation_id]
        
        return history
    
    def _extract_discussed_policies(self, history: List[Dict]) -> List[str]:
        """从历史中提取讨论过的政策"""
        policies = set()
        for entry in history:
            # 简单地从响应中提取政策名（如果存在）
            response = entry.get("response", "")
            # 这里可以添加更复杂的提取逻辑
        return list(policies)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def generate_policy_recommendations(self, policies: List[Dict], company_info: Dict) -> Dict[str, Any]:
        """
        基于企业信息生成政策推荐
        
        Args:
            policies: 政策列表
            company_info: 企业信息
            
        Returns:
            推荐结果
        """
        recommendations = []
        
        for policy in policies:
            score = policy.get('match_score', 0)
            
            # 计算推荐优先级
            priority = "medium"
            reasons = []
            
            if score >= 80:
                priority = "high"
                reasons.append("匹配度极高")
            elif score >= 60:
                priority = "medium"
                reasons.append("匹配度较高")
            else:
                priority = "low"
                reasons.append("可能适用")
            
            # 检查特殊资质匹配
            conditions = policy.get('conditions', {})
            other = conditions.get('other', []) if conditions else []
            
            if company_info.get('is_high_tech'):
                if any('高新' in str(other) or '高新技术' in policy.get('name', '') for _ in [1]):
                    priority = "high"
                    reasons.append("符合高新技术企业资质")
            
            if company_info.get('is_specialized'):
                if any('专精特新' in str(other) or '专精特新' in policy.get('name', '') for _ in [1]):
                    priority = "high"
                    reasons.append("符合专精特新企业资质")
            
            # 检查金额吸引力
            max_amount = policy.get('max_amount', 0)
            if isinstance(max_amount, (int, float)) and max_amount >= 100:
                reasons.append(f"最高可获{max_amount:.0f}万元补贴")
            
            recommendations.append({
                "policy_id": policy.get('id'),
                "policy_name": policy.get('name'),
                "priority": priority,
                "match_score": score,
                "reasons": reasons,
                "subsidy_amount": policy.get('subsidy_amount'),
                "deadline": policy.get('deadline'),
            })
        
        # 按优先级和匹配度排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(
            key=lambda x: (priority_order.get(x['priority'], 3), -x['match_score'])
        )
        
        return {
            "success": True,
            "total_recommendations": len(recommendations),
            "high_priority_count": len([r for r in recommendations if r['priority'] == 'high']),
            "recommendations": recommendations[:10]  # 最多返回10条
        }


# 全局实例
policy_agent = PolicyAgent()

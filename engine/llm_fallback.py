"""
LLM Fallback - 自动降级策略
DeepSeek API → 备用Key → Ollama本地模型 → 规则匹配
"""
import os
import time

class LLMFallback:
    """LLM自动降级管理器"""
    
    def __init__(self):
        self.primary_client = None
        self.fallback_client = None
        self.primary_config = {}
        self.fallback_config = {}
        self._last_failure_time = 0
        self._consecutive_failures = 0
        self._fallback_mode = False
        self._init_clients()
    
    def _init_clients(self):
        """初始化主用和备用客户端"""
        from openai import OpenAI
        
        # 主用：DeepSeek via Pekpik
        primary_key = os.getenv("DEEPSEEK_API_KEY")
        primary_url = os.getenv("OPENAI_BASE_URL")
        if primary_key and primary_url:
            try:
                self.primary_client = OpenAI(api_key=primary_key, base_url=primary_url)
                self.primary_config = {"model": "deepseek-chat", "name": "DeepSeek(Pekpik)"}
                print(f"✅ 主LLM：{self.primary_config['name']}")
            except Exception as e:
                print(f"⚠️ 主LLM初始化失败：{e}")
        
        # 备用：Ollama本地
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        try:
            self.fallback_client = OpenAI(api_key="ollama", base_url=ollama_url)
            self.fallback_config = {"model": ollama_model, "name": f"Ollama({ollama_model})"}
            print(f"✅ 备用LLM：{self.fallback_config['name']}")
        except Exception as e:
            print(f"⚠️ 备用LLM初始化失败：{e}")
    
    def chat(self, messages, temperature=0.7, max_tokens=800, timeout=30):
        """调用LLM，自动降级"""
        # 如果已经连续失败3次，直接走fallback
        if self._consecutive_failures >= 3:
            self._fallback_mode = True
        
        # 如果在fallback模式且距上次失败不到5分钟，直接用备用
        if self._fallback_mode and (time.time() - self._last_failure_time) < 300:
            return self._call_fallback(messages, temperature, max_tokens)
        
        # 尝试主用
        if self.primary_client and not self._fallback_mode:
            try:
                response = self.primary_client.chat.completions.create(
                    model=self.primary_config["model"],
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                self._consecutive_failures = 0
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"⚠️ 主LLM调用失败：{e}，切换备用")
                self._consecutive_failures += 1
                self._last_failure_time = time.time()
        
        # 尝试备用Key
        backup_key = os.getenv("DEEPSEEK_API_KEY_BACKUP")
        if backup_key and self.primary_client:
            try:
                backup_url = os.getenv("OPENAI_BASE_URL")
                backup_client = OpenAI(api_key=backup_key, base_url=backup_url)
                response = backup_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                print("✅ 备用Key调用成功")
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"⚠️ 备用Key也失败了：{e}")
        
        # 最终fallback：Ollama
        return self._call_fallback(messages, temperature, max_tokens)
    
    def _call_fallback(self, messages, temperature, max_tokens):
        """调用Ollama本地模型"""
        if not self.fallback_client:
            return None
        
        try:
            # Ollama用更短的max_tokens避免超时
            response = self.fallback_client.chat.completions.create(
                model=self.fallback_config["model"],
                messages=messages,
                temperature=temperature,
                max_tokens=min(max_tokens, 500),  # 小模型限制输出长度
                timeout=60  # 本地模型给更长超时
            )
            print("✅ Ollama本地模型调用成功")
            self._fallback_mode = True
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Ollama也失败了：{e}")
            return None
    
    def reset_fallback(self):
        """重置fallback状态（主LLM恢复时调用）"""
        self._fallback_mode = False
        self._consecutive_failures = 0

# 全局实例
llm_fallback = None

def get_llm_fallback():
    global llm_fallback
    if llm_fallback is None:
        llm_fallback = LLMFallback()
    return llm_fallback

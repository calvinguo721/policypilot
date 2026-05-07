#!/usr/bin/env python3
"""Fix all frontend issues"""
import os

FRONTEND = "/var/www/policypilot/frontend"

# 1. Fix console.html - add API functions
c = open(f"{FRONTEND}/console.html").read()
if "async function getBalance" not in c:
    pos = c.find("async function loadUserData")
    if pos > 0:
        api_code = '''    async function getBalance(apiKey) {
      try {
        const r = await fetch("/api/token/balance", { headers: { "X-API-Key": apiKey } });
        return await r.json();
      } catch(e) { return { success: false }; }
    }

    async function getUsage(apiKey) {
      try {
        const r = await fetch("/api/token/usage", { headers: { "X-API-Key": apiKey } });
        const d = await r.json();
        if (d.success) {
          const s = d.summary || {};
          return { success: true, total_calls: s.total_requests||0, daily_usage: (d.details||[]).slice(-7).map(x=>x.request_count||0) };
        }
        return { success: false };
      } catch(e) { return { success: false }; }
    }

    async function getBill(apiKey) {
      try {
        const r = await fetch("/api/token/bill", { headers: { "X-API-Key": apiKey } });
        return await r.json();
      } catch(e) { return { success: false, bills: [] }; }
    }

'''
        c = c[:pos] + api_code + c[pos:]
        open(f"{FRONTEND}/console.html", "w").write(c)
        print("1. console.html - API functions added")
    else:
        print("1. console.html - loadUserData not found!")
else:
    print("1. console.html - API functions already exist")

# 2. Console - 包月标识
c = open(f"{FRONTEND}/console.html").read()
if "899" not in c:
    c = c.replace("充值余额", "包月899元/年 · 余额查询")
    open(f"{FRONTEND}/console.html", "w").write(c)
    print("2. console.html - pricing label added")
else:
    print("2. console.html - pricing label already exists")

# 3. AI Chat - quick questions
c = open(f"{FRONTEND}/ai-chat.html").read()
if "handleQuickQuestion" not in c:
    # Add function
    pos = c.find("function sendMessage")
    if pos > 0:
        qf = '''    function handleQuickQuestion(btn) {
      document.getElementById("chatInput").value = btn.textContent;
      sendMessage();
    }

    function clearChat() {
      if (confirm("清空所有对话记录？")) {
        document.getElementById("chatMessages").innerHTML = "";
        localStorage.removeItem("chatHistory");
      }
    }

'''
        c = c[:pos] + qf + c[pos:]
        print("3. ai-chat.html - functions added")
    
    # Add quick question buttons
    c = c.replace(
        '<div class="chat-input-container">',
        '''<div class="quick-questions" style="display:flex;gap:8px;padding:0 20px 12px;flex-wrap:wrap;">
      <button onclick="handleQuickQuestion(this)" style="padding:8px 16px;border-radius:20px;border:1px solid rgba(0,212,255,0.3);background:rgba(0,212,255,0.08);color:#00d4ff;cursor:pointer;font-size:13px;">我司能拿哪些补贴？</button>
      <button onclick="handleQuickQuestion(this)" style="padding:8px 16px;border-radius:20px;border:1px solid rgba(0,212,255,0.3);background:rgba(0,212,255,0.08);color:#00d4ff;cursor:pointer;font-size:13px;">深圳科技企业有什么政策？</button>
      <button onclick="handleQuickQuestion(this)" style="padding:8px 16px;border-radius:20px;border:1px solid rgba(0,212,255,0.3);background:rgba(0,212,255,0.08);color:#00d4ff;cursor:pointer;font-size:13px;">创业补贴怎么申请？</button>
    </div>
    <div class="chat-input-container">'''
    )
    
    # Add clear button
    c = c.replace(
        'PolicyPilot AI 助手',
        '<span onclick="clearChat()" style="cursor:pointer;float:right;font-size:12px;color:#8899aa;padding:4px 12px;border:1px solid rgba(255,255,255,0.1);border-radius:6px;">清空对话</span> PolicyPilot AI 助手'
    )
    
    open(f"{FRONTEND}/ai-chat.html", "w").write(c)
    print("3. ai-chat.html - UI updated")
else:
    print("3. ai-chat.html - already has quick questions")

# 4. API Docs - auth section
c = open(f"{FRONTEND}/api-docs.html").read()
if "认证方式" not in c:
    c = c.replace(
        '<p class="docs-desc">采用包月订阅模式',
        '''<div style="background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.2);border-radius:12px;padding:20px;margin-bottom:24px;">
      <h3 style="color:#f5a623;margin-bottom:12px;">认证方式</h3>
      <p style="color:#8899aa;line-height:1.8;">所有API请求需在HTTP Header中携带 <code style="background:rgba(0,0,0,0.3);padding:2px 8px;border-radius:4px;color:#00d4ff;">X-API-Key</code> 进行身份验证。注册后即可获得API Key。</p>
    </div>
    <p class="docs-desc">采用包月订阅模式'''
    )
    open(f"{FRONTEND}/api-docs.html", "w").write(c)
    print("4. api-docs.html - auth section added")
else:
    print("4. api-docs.html - auth section already exists")

# 5. Restart
os.system("rm -rf /var/www/policypilot/engine/__pycache__")
os.system("systemctl restart policypilot")
print("5. Service restarted")
print("ALL DONE")

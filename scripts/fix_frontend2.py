#!/usr/bin/env python3
import os

FRONTEND = "/var/www/policypilot/frontend"

# 1. AI Chat - clear button & quick questions
c = open(f"{FRONTEND}/ai-chat.html").read()

# Add clear button to header
if "清空对话" not in c:
    c = c.replace(
        'PolicyPilot AI 助手',
        '<span onclick="clearChat()" style="cursor:pointer;float:right;font-size:12px;color:#8899aa;padding:4px 12px;border:1px solid rgba(255,255,255,0.1);border-radius:6px;">清空对话</span> PolicyPilot AI 助手'
    )
    print("1a. clearChat button added")

# Add quick questions - find the FIRST chat-input-container only
if "我司能拿" not in c:
    # Find position of first chat-input-container
    pos = c.find('<div class="chat-input-container">')
    if pos > 0:
        # Find the parent div context to insert before it
        insert_html = '''<div class="quick-questions" style="display:flex;gap:8px;padding:0 20px 12px;flex-wrap:wrap;">
      <button onclick="handleQuickQuestion(this)" style="padding:8px 16px;border-radius:20px;border:1px solid rgba(0,212,255,0.3);background:rgba(0,212,255,0.08);color:#00d4ff;cursor:pointer;font-size:13px;">我司能拿哪些补贴？</button>
      <button onclick="handleQuickQuestion(this)" style="padding:8px 16px;border-radius:20px;border:1px solid rgba(0,212,255,0.3);background:rgba(0,212,255,0.08);color:#00d4ff;cursor:pointer;font-size:13px;">深圳科技企业有什么政策？</button>
      <button onclick="handleQuickQuestion(this)" style="padding:8px 16px;border-radius:20px;border:1px solid rgba(0,212,255,0.3);background:rgba(0,212,255,0.08);color:#00d4ff;cursor:pointer;font-size:13px;">创业补贴怎么申请？</button>
    </div>
    '''
        c = c[:pos] + insert_html + c[pos:]
        print("1b. quick questions added")
    
    open(f"{FRONTEND}/ai-chat.html", "w").write(c)
else:
    print("1. already has quick questions")

# 2. API Docs - auth section  
c = open(f"{FRONTEND}/api-docs.html").read()
if "认证方式" not in c:
    # Find the actual text pattern
    for pattern in ['采用首年包月', '采用包月订阅模式', '采用包月', '包月订阅']:
        if pattern in c:
            c = c.replace(
                f'<p class="docs-desc">{pattern}',
                f'''<div style="background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.2);border-radius:12px;padding:20px;margin-bottom:24px;">
      <h3 style="color:#f5a623;margin-bottom:12px;">认证方式</h3>
      <p style="color:#8899aa;line-height:1.8;">所有API请求需在HTTP Header中携带 <code style="background:rgba(0,0,0,0.3);padding:2px 8px;border-radius:4px;color:#00d4ff;">X-API-Key</code> 进行身份验证。注册后即可获得API Key。</p>
    </div>
    <p class="docs-desc">{pattern}'''
            )
            open(f"{FRONTEND}/api-docs.html", "w").write(c)
            print(f"2. api-docs.html - auth added (pattern: {pattern})")
            break
    else:
        print("2. api-docs.html - no matching pattern found")
else:
    print("2. api-docs.html - auth already exists")

print("DONE")

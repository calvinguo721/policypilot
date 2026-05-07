#!/usr/bin/env python3
"""Complete rewrite of console.html - remove all old billing, keep only subscription model"""
import re

FRONTEND = "/var/www/policypilot/frontend"
c = open(f"{FRONTEND}/console.html", encoding="utf-8").read()

# 找到 <main> 到 </main> 之间的内容，替换为全新的订阅模式控制台
main_start = c.find('<main class="console-layout"')
main_end = c.find('</main>') + len('</main>')

# 找到 <style> 到 </style>，替换为简化版样式
style_start = c.find('<style>')
style_end = c.find('</style>') + len('</style>')

new_style = '''<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0e1a;--dark:#141929;--cyan:#00d4ff;--gold:#f5a623;--white:#f0f0f0;--gray:#8899aa}
body{background:var(--bg);color:var(--white);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}
.nav{position:fixed;top:0;left:0;right:0;z-index:100;padding:16px 40px;display:flex;align-items:center;justify-content:space-between;background:rgba(10,14,26,0.85);backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,255,255,0.06)}
.logo{font-size:20px;font-weight:700;color:var(--white);text-decoration:none}.logo span{color:var(--gold)}
.nav-links{display:flex;gap:20px;align-items:center}
.nav-links a{color:var(--gray);font-size:14px;text-decoration:none;transition:color .2s}
.nav-links a:hover{color:var(--white)}
.btn{padding:8px 20px;border-radius:8px;border:none;cursor:pointer;font-size:14px;font-weight:600;transition:all .2s}
.btn-primary{background:var(--gold);color:#000}
.btn-ghost{background:transparent;color:var(--gray);border:1px solid rgba(255,255,255,0.1)}
.btn-ghost:hover{color:var(--white);border-color:rgba(255,255,255,0.3)}

.main{max-width:800px;margin:0 auto;padding:100px 24px 60px}
.card{background:var(--dark);border:1px solid rgba(255,255,255,0.06);border-radius:16px;padding:32px;margin-bottom:24px}
.card h2{font-size:1.1rem;margin-bottom:20px;display:flex;align-items:center;gap:10px}
.card h2 svg{width:20px;height:20px;stroke:var(--cyan)}

.api-key-box{display:flex;align-items:center;gap:12px;background:rgba(0,0,0,0.3);border-radius:10px;padding:16px 20px}
.api-key-value{flex:1;font-family:monospace;font-size:14px;color:var(--cyan);word-break:break-all}
.api-key-hint{color:#556;font-size:12px;margin-top:8px}

.sub-status{display:flex;align-items:center;justify-content:space-between;padding:20px;background:rgba(245,166,35,0.06);border:1px solid rgba(245,166,35,0.15);border-radius:12px;margin-bottom:16px}
.sub-status .plan{font-size:18px;font-weight:700;color:var(--gold)}
.sub-status .expire{color:var(--gray);font-size:13px;margin-top:4px}

.quick-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.quick-action{display:flex;flex-direction:column;align-items:center;gap:8px;padding:24px 16px;background:rgba(0,0,0,0.2);border-radius:12px;text-decoration:none;transition:background .2s}
.quick-action:hover{background:rgba(0,212,255,0.06)}
.quick-action svg{width:32px;height:32px;stroke:var(--cyan)}
.quick-action span{color:var(--white);font-size:14px;font-weight:600}
.quick-action small{color:var(--gray);font-size:12px}

/* Auth Modal */
.modal-overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:200;display:flex;align-items:center;justify-content:center}
.modal-box{background:var(--dark);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:40px;max-width:420px;width:90%}
.modal-box h2{font-size:1.4rem;margin-bottom:8px}
.modal-box p{color:var(--gray);font-size:14px;margin-bottom:24px}
.form-group{margin-bottom:16px}
.form-group label{display:block;color:var(--gray);font-size:13px;margin-bottom:6px}
.form-group input{width:100%;padding:12px 16px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:var(--white);font-size:14px;outline:none}
.form-group input:focus{border-color:var(--cyan)}
.form-btn{width:100%;padding:14px;background:var(--gold);color:#000;font-size:15px;font-weight:700;border:none;border-radius:10px;cursor:pointer}
.form-btn:disabled{opacity:0.5}
.switch-link{color:var(--cyan);cursor:pointer;font-size:13px}
.hidden{display:none!important}
.toast{position:fixed;top:80px;right:20px;padding:14px 24px;border-radius:10px;font-size:14px;z-index:300;animation:slideIn .3s}
.toast-success{background:#10b981;color:#fff}
.toast-error{background:#ef4444;color:#fff}
.toast-info{background:#3b82f6;color:#fff}
@keyframes slideIn{from{transform:translateX(100px);opacity:0}to{transform:translateX(0);opacity:1}}
</style>'''

new_main = '''<main class="main" id="consoleContent" style="display:none">
  <!-- 企业信息 -->
  <div class="card">
    <h2><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>企业信息</h2>
    <div id="companyInfo" style="font-size:1.2rem;font-weight:600;margin-bottom:4px">-</div>
    <div id="customerId" style="color:var(--gray);font-size:13px">-</div>
  </div>

  <!-- 订阅状态 -->
  <div class="card">
    <h2><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>订阅状态</h2>
    <div class="sub-status">
      <div>
        <div class="plan" id="planName">免费版</div>
        <div class="expire" id="planExpire">每日1次AI对话</div>
      </div>
      <a href="/subscribe.html" class="btn btn-primary" id="upgradeBtn">升级包月 899元/年</a>
    </div>
  </div>

  <!-- API Key -->
  <div class="card">
    <h2><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>API Key</h2>
    <div class="api-key-box">
      <span class="api-key-value" id="apiKeyDisplay">-</span>
      <button class="btn btn-ghost" onclick="copyApiKey()" style="padding:6px 14px;font-size:12px">复制</button>
    </div>
    <p class="api-key-hint">请妥善保管您的 API Key，不要泄露给他人</p>
  </div>

  <!-- 快速操作 -->
  <div class="card">
    <h2><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>快速操作</h2>
    <div class="quick-actions">
      <a href="/ai-chat.html" class="quick-action">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>AI对话</span>
        <small>智能政策咨询</small>
      </a>
      <a href="/api-docs.html" class="quick-action">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        <span>API文档</span>
        <small>开发接入指南</small>
      </a>
      <a href="/" class="quick-action">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <span>政策搜索</span>
        <small>快速查找政策</small>
      </a>
    </div>
  </div>
</main>

<!-- Auth Modal -->
<div class="modal-overlay" id="authModal">
  <div class="modal-box">
    <!-- Login Form -->
    <div id="loginForm">
      <h2>登录控制台</h2>
      <p>输入您的 API Key 登录</p>
      <div class="form-group">
        <label>API Key</label>
        <input type="text" id="loginApiKey" placeholder="pp_xxxxxxxxxxxx">
      </div>
      <button class="form-btn" onclick="handleLogin()">登录</button>
      <p style="text-align:center;margin-top:16px">还没有账号？<span class="switch-link" onclick="showRegisterForm()">立即注册</span></p>
    </div>
    <!-- Register Form -->
    <div id="registerForm" class="hidden">
      <h2>注册账号</h2>
      <p>注册后获取 API Key</p>
      <div class="form-group">
        <label>企业名称</label>
        <input type="text" id="companyName" placeholder="您的企业名称">
      </div>
      <div class="form-group">
        <label>联系电话</label>
        <input type="tel" id="contactPhone" placeholder="11位手机号">
      </div>
      <button class="form-btn" onclick="handleRegister()">注册</button>
      <p style="text-align:center;margin-top:16px">已有账号？<span class="switch-link" onclick="showLoginForm()">登录</span></p>
    </div>
  </div>
</div>

<script>
let currentApiKey = null;

document.addEventListener('DOMContentLoaded', () => {
  const savedKey = localStorage.getItem('api_key');
  if (savedKey) {
    currentApiKey = savedKey;
    showConsole(savedKey);
  }
});

function showLoginForm() {
  document.getElementById('loginForm').classList.remove('hidden');
  document.getElementById('registerForm').classList.add('hidden');
}
function showRegisterForm() {
  document.getElementById('loginForm').classList.add('hidden');
  document.getElementById('registerForm').classList.remove('hidden');
}

async function handleLogin() {
  const apiKey = document.getElementById('loginApiKey').value.trim();
  if (!apiKey) { showToast('请输入API Key','error'); return; }
  try {
    const r = await fetch('/api/token/balance', { headers: { 'X-API-Key': apiKey } });
    const d = await r.json();
    if (d.success) {
      localStorage.setItem('api_key', apiKey);
      localStorage.setItem('company_name', d.company_name || '企业用户');
      currentApiKey = apiKey;
      showConsole(apiKey);
      showToast('登录成功','success');
    } else {
      showToast('API Key 无效','error');
    }
  } catch(e) { showToast('登录失败','error'); }
}

async function handleRegister() {
  const name = document.getElementById('companyName').value.trim();
  const phone = document.getElementById('contactPhone').value.trim();
  if (!name || !phone) { showToast('请填写完整信息','error'); return; }
  if (!/^1\d{10}$/.test(phone)) { showToast('请输入有效的11位手机号','error'); return; }
  try {
    const r = await fetch('/api/token/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company_name: name, contact_phone: phone })
    });
    const d = await r.json();
    if (d.success) {
      localStorage.setItem('api_key', d.api_key);
      localStorage.setItem('company_name', name);
      currentApiKey = d.api_key;
      showConsole(d.api_key);
      showToast('注册成功！请保管好您的API Key','success');
    } else {
      showToast(d.detail?.message || d.message || '注册失败','error');
    }
  } catch(e) { showToast('注册失败','error'); }
}

async function showConsole(apiKey) {
  document.getElementById('authModal').classList.add('hidden');
  document.getElementById('consoleContent').style.display = 'block';
  document.getElementById('apiKeyDisplay').textContent = apiKey;
  
  try {
    const r = await fetch('/api/token/balance', { headers: { 'X-API-Key': apiKey } });
    const d = await r.json();
    if (d.success) {
      document.getElementById('companyInfo').textContent = d.company_name || '企业用户';
      document.getElementById('customerId').textContent = d.customer_id || '';
      document.getElementById('planName').textContent = '免费版';
      document.getElementById('planExpire').textContent = '每日1次AI对话';
    }
  } catch(e) {}
}

function handleLogout() {
  localStorage.removeItem('api_key');
  localStorage.removeItem('company_name');
  location.reload();
}

function copyApiKey() {
  navigator.clipboard.writeText(currentApiKey || '');
  showToast('已复制','success');
}

function showToast(msg, type) {
  const t = document.createElement('div');
  t.className = 'toast toast-' + type;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
</script>'''

# 替换
c = c[:style_start] + new_style + c[style_end:main_start] + new_main + c[main_end:]

# 保留导航栏的退出按钮逻辑
# 确保nav里有logout
if 'handleLogout()' not in c:
    # 在nav里加退出按钮
    c = c.replace('</nav>', '<div class="nav-links"><a href="/" class="btn btn-ghost" style="font-size:13px">首页</a><a href="#" class="btn btn-ghost" style="font-size:13px" onclick="handleLogout()">退出</a></div></nav>')

open(f"{FRONTEND}/console.html", "w", encoding="utf-8").write(c)
print("console.html completely rewritten - subscription model only")

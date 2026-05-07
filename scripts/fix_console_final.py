#!/usr/bin/env python3
"""Complete rewrite of console.html - standalone, no main.js dependency"""

FRONTEND = "/var/www/policypilot/frontend"

html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>控制台 - 政策通 PolicyPilot</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0e1a;--dark:#141929;--cyan:#00d4ff;--gold:#f5a623;--white:#f0f0f0;--gray:#8899aa;--border:rgba(255,255,255,0.06)}
body{background:var(--bg);color:var(--white);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}

/* Nav */
.nav{position:fixed;top:0;left:0;right:0;z-index:100;padding:16px 32px;display:flex;align-items:center;justify-content:space-between;background:rgba(10,14,26,0.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.logo{font-size:18px;font-weight:700;color:var(--white);text-decoration:none}.logo span{color:var(--gold)}
.nav-right{display:flex;gap:12px;align-items:center}
.btn{padding:8px 18px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:all .2s;text-decoration:none}
.btn-primary{background:var(--gold);color:#000}
.btn-ghost{background:transparent;color:var(--gray);border:1px solid rgba(255,255,255,0.1)}
.btn-ghost:hover{color:var(--white);border-color:rgba(255,255,255,0.3)}

/* Main */
.main{max-width:720px;margin:0 auto;padding:90px 20px 60px}

/* Cards */
.card{background:var(--dark);border:1px solid var(--border);border-radius:16px;padding:28px;margin-bottom:20px}
.card-title{font-size:15px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px}
.card-title svg{width:18px;height:18px;stroke:var(--cyan)}

/* Sub Status */
.sub-row{display:flex;align-items:center;justify-content:space-between;padding:20px;background:rgba(245,166,35,0.06);border:1px solid rgba(245,166,35,0.15);border-radius:12px}
.sub-plan{font-size:18px;font-weight:700;color:var(--gold)}
.sub-desc{color:var(--gray);font-size:13px;margin-top:4px}

/* API Key */
.key-box{display:flex;align-items:center;gap:10px;background:rgba(0,0,0,0.3);border-radius:10px;padding:14px 18px}
.key-val{flex:1;font-family:monospace;font-size:13px;color:var(--cyan);word-break:break-all}
.key-hint{color:#556;font-size:12px;margin-top:8px}

/* Quick Actions */
.actions{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.action{display:flex;flex-direction:column;align-items:center;gap:6px;padding:20px 12px;background:rgba(0,0,0,0.2);border-radius:12px;text-decoration:none;transition:background .2s}
.action:hover{background:rgba(0,212,255,0.06)}
.action svg{width:28px;height:28px;stroke:var(--cyan)}
.action span{color:var(--white);font-size:13px;font-weight:600}
.action small{color:var(--gray);font-size:11px}

/* Modal */
.overlay{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:200;display:flex;align-items:center;justify-content:center}
.overlay.hide{display:none}
.modal{background:var(--dark);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:36px;max-width:400px;width:92%}
.modal h2{font-size:1.3rem;margin-bottom:6px}
.modal p{color:var(--gray);font-size:13px;margin-bottom:20px}
.field{margin-bottom:14px}
.field label{display:block;color:var(--gray);font-size:12px;margin-bottom:5px}
.field input{width:100%;padding:11px 14px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:8px;color:var(--white);font-size:14px;outline:none}
.field input:focus{border-color:var(--cyan)}
.submit{width:100%;padding:13px;background:var(--gold);color:#000;font-size:15px;font-weight:700;border:none;border-radius:10px;cursor:pointer}
.submit:disabled{opacity:.5;cursor:not-allowed}
.switch{color:var(--cyan);cursor:pointer;font-size:12px}

/* Toast */
.toast{position:fixed;top:70px;right:16px;padding:12px 20px;border-radius:10px;font-size:13px;z-index:300;animation:fadeIn .3s;color:#fff}
.toast-success{background:#10b981}
.toast-error{background:#ef4444}
.toast-info{background:#3b82f6}
@keyframes fadeIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}

.hide{display:none}
</style>
</head>
<body>

<!-- Nav -->
<nav class="nav">
  <a href="/" class="logo">Policy<span>Pilot</span></a>
  <div class="nav-right">
    <a href="/" class="btn btn-ghost">首页</a>
    <a href="/ai-chat.html" class="btn btn-ghost">AI对话</a>
    <button class="btn btn-ghost" id="logoutBtn" style="display:none" onclick="doLogout()">退出</button>
  </div>
</nav>

<!-- Main Content (hidden until login) -->
<div class="main" id="mainContent" style="display:none">

  <div class="card">
    <div class="card-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>企业信息</div>
    <div id="companyName" style="font-size:1.1rem;font-weight:600">-</div>
    <div id="customerId" style="color:var(--gray);font-size:12px;margin-top:2px">-</div>
  </div>

  <div class="card">
    <div class="card-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>订阅状态</div>
    <div class="sub-row">
      <div>
        <div class="sub-plan" id="planName">免费版</div>
        <div class="sub-desc" id="planDesc">每日1次AI对话</div>
      </div>
      <a href="/subscribe.html" class="btn btn-primary">升级包月 899元/年</a>
    </div>
  </div>

  <div class="card">
    <div class="card-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>API Key</div>
    <div class="key-box">
      <span class="key-val" id="apiKeyText">-</span>
      <button class="btn btn-ghost" onclick="copyKey()" style="padding:5px 12px;font-size:11px">复制</button>
    </div>
    <div class="key-hint">请妥善保管，不要泄露给他人</div>
  </div>

  <div class="card">
    <div class="card-title"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>快速操作</div>
    <div class="actions">
      <a href="/ai-chat.html" class="action">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <span>AI对话</span><small>智能政策咨询</small>
      </a>
      <a href="/api-docs.html" class="action">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        <span>API文档</span><small>开发接入指南</small>
      </a>
      <a href="/" class="action">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
        <span>政策搜索</span><small>快速查找政策</small>
      </a>
    </div>
  </div>
</div>

<!-- Auth Modal -->
<div class="overlay" id="authOverlay">
  <div class="modal">
    <div id="loginView">
      <h2>登录控制台</h2>
      <p>输入API Key登录</p>
      <div class="field">
        <label>API Key</label>
        <input type="text" id="inputKey" placeholder="pp_xxxxxxxxxxxx">
      </div>
      <button class="submit" id="loginBtn">登录</button>
      <p style="text-align:center;margin-top:14px">还没有账号？<span class="switch" id="toRegister">立即注册</span></p>
    </div>
    <div id="registerView" class="hide">
      <h2>注册账号</h2>
      <p>注册后获取API Key</p>
      <div class="field">
        <label>企业名称</label>
        <input type="text" id="inputCompany" placeholder="您的企业名称">
      </div>
      <div class="field">
        <label>联系电话</label>
        <input type="tel" id="inputPhone" placeholder="11位手机号">
      </div>
      <button class="submit" id="registerBtn">注册</button>
      <p style="text-align:center;margin-top:14px">已有账号？<span class="switch" id="toLogin">登录</span></p>
    </div>
  </div>
</div>

<script>
(function(){
  const $=id=>document.getElementById(id);
  let apiKey=null;

  // Init
  const saved=localStorage.getItem('api_key');
  if(saved){apiKey=saved;enterConsole();}
  else{$('authOverlay').classList.remove('hide');}

  // Switch views
  $('toRegister').onclick=()=>{$('loginView').classList.add('hide');$('registerView').classList.remove('hide');};
  $('toLogin').onclick=()=>{$('registerView').classList.add('hide');$('loginView').classList.remove('hide');};

  // Login
  $('loginBtn').onclick=async()=>{
    const key=$('inputKey').value.trim();
    if(!key){toast('请输入API Key','error');return;}
    $('loginBtn').disabled=true;$('loginBtn').textContent='登录中...';
    try{
      const r=await fetch('/api/token/balance',{headers:{'X-API-Key':key}});
      const d=await r.json();
      if(d.success){
        apiKey=key;localStorage.setItem('api_key',key);localStorage.setItem('company_name',d.company_name||'');
        enterConsole();toast('登录成功','success');
      }else{toast('API Key无效','error');}
    }catch(e){toast('网络错误','error');}
    $('loginBtn').disabled=false;$('loginBtn').textContent='登录';
  };

  // Register
  $('registerBtn').onclick=async()=>{
    const name=$('inputCompany').value.trim();
    const phone=$('inputPhone').value.trim();
    if(!name){toast('请输入企业名称','error');return;}
    if(!/^1\d{10}$/.test(phone)){toast('请输入11位手机号','error');return;}
    $('registerBtn').disabled=true;$('registerBtn').textContent='注册中...';
    try{
      const r=await fetch('/api/token/register',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({company_name:name,contact_phone:phone})
      });
      const d=await r.json();
      if(d.success){
        apiKey=d.api_key;localStorage.setItem('api_key',d.api_key);localStorage.setItem('company_name',name);
        enterConsole();toast('注册成功！API Key已生成','success');
      }else{
        const msg=d.detail?.message||d.message||'注册失败';
        toast(msg,'error');
      }
    }catch(e){toast('网络错误','error');}
    $('registerBtn').disabled=false;$('registerBtn').textContent='注册';
  };

  // Enter console
  async function enterConsole(){
    $('authOverlay').classList.add('hide');
    $('mainContent').style.display='block';
    $('logoutBtn').style.display='inline-block';
    $('apiKeyText').textContent=apiKey;
    // Fetch company info
    try{
      const r=await fetch('/api/token/balance',{headers:{'X-API-Key':apiKey}});
      const d=await r.json();
      if(d.success){
        $('companyName').textContent=d.company_name||'企业用户';
        $('customerId').textContent=d.customer_id||'';
      }
    }catch(e){}
  }

  // Logout
  window.doLogout=function(){
    localStorage.removeItem('api_key');localStorage.removeItem('company_name');
    location.reload();
  };

  // Copy key
  window.copyKey=function(){
    navigator.clipboard.writeText(apiKey||'').then(()=>toast('已复制','success')).catch(()=>toast('复制失败','error'));
  };

  // Toast
  function toast(msg,type){
    const t=document.createElement('div');
    t.className='toast toast-'+type;
    t.textContent=msg;
    document.body.appendChild(t);
    setTimeout(()=>t.remove(),3000);
  }
})();
</script>
</body>
</html>'''

open(f"{FRONTEND}/console.html", "w", encoding="utf-8").write(html)
print("console.html completely rewritten - standalone, no main.js")

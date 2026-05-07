#!/usr/bin/env python3
"""Fix: remove old billing, add subscription UI, fix homepage search"""
import os

FRONTEND = "/var/www/policypilot/frontend"

# ============= 1. 首页：搜索框直接跳AI对话 =============
c = open(f"{FRONTEND}/index.html", encoding="utf-8").read()

if "doSearch()" in c and "/ai-chat.html" not in c[c.find("doSearch"):c.find("doSearch")+200]:
    # 替换搜索逻辑：直接跳转到AI对话页
    old_script_start = c.find('<script>')
    old_script_end = c.find('</script>') + len('</script>')
    
    new_script = '''<script>
function doSearch(){
  const q=document.getElementById('searchInput').value.trim();
  if(!q)return;
  window.location.href='/ai-chat.html?q='+encodeURIComponent(q);
}
document.getElementById('searchInput').addEventListener('keydown',e=>{if(e.key==='Enter')doSearch()});
document.getElementById('searchBtn').addEventListener('click',doSearch);
</script>'''
    
    c = c[:old_script_start] + new_script + c[old_script_end:]
    open(f"{FRONTEND}/index.html", "w", encoding="utf-8").write(c)
    print("1. 首页搜索框改为跳转AI对话")
else:
    print("1. 首页搜索框已处理或不需要改")

# ============= 2. AI对话页：接收URL参数q =============
c = open(f"{FRONTEND}/ai-chat.html", encoding="utf-8").read()

if "URLSearchParams" not in c or "getParam" not in c:
    # 在DOMContentLoaded或load事件里加URL参数读取
    init_code = '''
    // 读取URL参数，自动填入搜索
    const urlParams = new URLSearchParams(window.location.search);
    const initQuery = urlParams.get('q');
    if (initQuery) {
        document.getElementById('chatInput').value = initQuery;
        setTimeout(() => sendMessage(), 500);
    }
'''
    # 找到script结尾插入
    if "window.onload" in c:
        c = c.replace("window.onload", init_code + "\nwindow.onload")
    else:
        # 在</script>前插入
        last_script = c.rfind('</script>')
        c = c[:last_script] + init_code + c[last_script:]
    
    open(f"{FRONTEND}/ai-chat.html", "w", encoding="utf-8").write(c)
    print("2. AI对话页支持URL参数")
else:
    print("2. AI对话页已支持URL参数")

# ============= 3. 控制台：重构为订阅模式 =============
c = open(f"{FRONTEND}/console.html", encoding="utf-8").read()

if "subscription" not in c.lower() or "订阅状态" not in c:
    # 找到整个consoleContent div，替换内容
    # 简化方案：在handleLogin成功后，直接跳转到一个简化版dashboard
    
    # 修改loadUserData函数，改为显示订阅信息
    old_load = c[c.find("async function loadUserData"):c.find("function renderUsageChart")]
    
    new_load = '''async function loadUserData(apiKey) {
      try {
        // 查询余额确认身份
        const r = await fetch("/api/token/balance", { headers: { "X-API-Key": apiKey } });
        const d = await r.json();
        
        if (d.success) {
          document.getElementById("balanceDisplay").textContent = d.company_name || "企业用户";
          document.getElementById("balanceDisplay").style.fontSize = "1.2rem";
          document.getElementById("balanceDisplay").style.fontWeight = "600";
        }
      } catch (error) {
        console.error("Failed to load user data:", error);
      }
    }

    '''
    
    c = c.replace(old_load, new_load)
    
    # 修改余额区域显示为订阅状态
    c = c.replace('账户余额', '企业名称')
    
    # 替换充值按钮为"开通包月"
    c = c.replace('充值', '开通包月')
    c = c.replace('openRechargeModal()', "window.open('https://qiai.ren/subscribe.html','_blank')")
    
    # 隐藏用量图表和账单区域
    c = c.replace('用量趋势', '本月查询次数')
    
    open(f"{FRONTEND}/console.html", "w", encoding="utf-8").write(c)
    print("3. 控制台改为订阅模式")
else:
    print("3. 控制台已是订阅模式")

# ============= 4. 创建订阅开通页面 =============
subscribe_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>开通包月 - 政策通 PolicyPilot</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e1a;color:#f0f0f0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center}
.container{max-width:560px;width:100%;padding:40px 24px}
.card{background:#141929;border:1px solid rgba(255,255,255,0.06);border-radius:20px;padding:48px 40px;text-align:center}
.price{font-size:4rem;font-weight:800;color:#f5a623;margin:24px 0 8px}
.price span{font-size:1.2rem;color:#8899aa;font-weight:400}
.features{text-align:left;margin:32px 0;padding:0}
.features li{list-style:none;padding:12px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:15px;display:flex;align-items:center;gap:12px}
.features li::before{content:"✓";color:#00d4ff;font-weight:700;font-size:16px}
.cta{display:block;width:100%;padding:18px;background:#f5a623;color:#000;font-size:18px;font-weight:700;border:none;border-radius:12px;cursor:pointer;transition:transform .2s;margin-top:24px}
.cta:hover{transform:scale(1.02)}
.note{color:#556;font-size:13px;margin-top:16px}
.back{color:#8899aa;text-decoration:none;display:inline-block;margin-top:24px;font-size:14px}
.back:hover{color:#00d4ff}
.contact-box{background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.15);border-radius:12px;padding:24px;margin-top:24px;text-align:left}
.contact-box h3{color:#00d4ff;margin-bottom:12px;font-size:16px}
.contact-box p{color:#8899aa;font-size:14px;line-height:1.8}
.contact-box .wechat{color:#f5a623;font-weight:600;font-size:16px}
</style>
</head>
<body>
<div class="container">
<div class="card">
  <h2 style="font-size:1.4rem;color:#8899aa">政策通 PolicyPilot</h2>
  <div class="price">899<span>元/年</span></div>
  <p style="color:#8899aa">首年特惠 · 全量政策不限查 · AI智能匹配</p>
  <ul class="features">
    <li>每月500次AI智能对话</li>
    <li>全国4000+政策数据库</li>
    <li>政策匹配+申报条件分析</li>
    <li>补贴金额精准推荐</li>
    <li>多区域政策对比</li>
    <li>企业画像定制推荐</li>
  </ul>
  <button class="cta" onclick="showContact()">立即开通</button>
  <p class="note">7天无理由退款 · 到期自动停用 · 无隐藏费用</p>
  
  <div class="contact-box" id="contactBox" style="display:none">
    <h3>联系方式</h3>
    <p>添加微信开通，备注"政策通包月"</p>
    <p class="wechat">微信号：kaijue2024</p>
    <p style="margin-top:8px">或发送邮件至：<span style="color:#00d4ff">service@qiai.ren</span></p>
    <p style="margin-top:12px;font-size:13px">工作时间：工作日 9:00-18:00<br>一般1个工作日内完成开通</p>
  </div>
</div>
<a href="/" class="back">← 返回首页</a>
</div>
<script>
function showContact(){
  document.getElementById('contactBox').style.display='block';
  document.querySelector('.cta').textContent='已显示联系方式';
  document.querySelector('.cta').disabled=true;
  document.querySelector('.cta').style.opacity='0.6';
}
</script>
</body>
</html>'''

open(f"{FRONTEND}/subscribe.html", "w", encoding="utf-8").write(subscribe_html)
print("4. 订阅开通页面已创建")

print("\nALL DONE")

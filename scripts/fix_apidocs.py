#!/usr/bin/env python3

FRONTEND = "/var/www/policypilot/frontend"
c = open(f"{FRONTEND}/api-docs.html", encoding="utf-8").read()

if "认证方式" not in c:
    # 精确匹配实际文本
    target = 'PolicyPilot 采用首年包月订阅模式'
    if target in c:
        auth_html = '''<div style="background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.2);border-radius:12px;padding:20px;margin-bottom:24px;">
      <h3 style="color:#f5a623;margin-bottom:12px;">认证方式</h3>
      <p style="color:#8899aa;line-height:1.8;">所有API请求需在HTTP Header中携带 <code style="background:rgba(0,0,0,0.3);padding:2px 8px;border-radius:4px;color:#00d4ff;">X-API-Key</code> 进行身份验证。注册后即可获得API Key。</p>
    </div>
    '''
        # 在target所在行之前插入
        c = c.replace(f'<p class="docs-desc">{target}', f'{auth_html}<p class="docs-desc">{target}')
        open(f"{FRONTEND}/api-docs.html", "w", encoding="utf-8").write(c)
        print("auth section added")
    else:
        # 找更宽松的匹配
        for line in c.split('\n'):
            if 'docs-desc' in line and '899' in line:
                print(f"Found line: {line[:100]}")
                break
        print("target pattern not found")
else:
    print("already exists")

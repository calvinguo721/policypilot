#!/usr/bin/env python3
"""Remove all old billing HTML and JS from console.html"""

FRONTEND = "/var/www/policypilot/frontend"
c = open(f"{FRONTEND}/console.html", encoding="utf-8").read()

# 1. 删除 rechargeModal 整个div
start = c.find('<div class="modal hidden" id="rechargeModal"')
if start > 0:
    # 找匹配的</div> - 简单方法：找到下一个同等层级的modal结束
    end = c.find('</div>\n    </div>', start) + len('</div>\n    </div>')
    # 更精确：找到 rechargeModal 的结束
    # 数div的嵌套层级
    temp = c[start:]
    depth = 0
    i = 0
    while i < len(temp):
        if temp[i:i+4] == '<div':
            depth += 1
        elif temp[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                end = start + i + 6
                break
        i += 1
    c = c[:start] + c[end:]
    print("1. rechargeModal removed")

# 2. 删除旧的JS函数（在<script>里，但不在新的script块里）
# 找第二个script块（第一个是新的简洁版，第二个是旧的残留）
scripts = []
idx = 0
while True:
    s = c.find('<script>', idx)
    if s < 0: break
    e = c.find('</script>', s) + len('</script>')
    scripts.append((s, e, c[s:e]))
    idx = e

print(f"Found {len(scripts)} script blocks")
for i, (s, e, content) in enumerate(scripts):
    has_old = any(kw in content for kw in ['confirmRecharge', 'rechargeModal', 'renderBills', 'billsContainer', 'getBillTypeName'])
    has_new = 'handleLogin' in content or 'showConsole' in content
    print(f"  Script {i}: {len(content)} chars, old={has_old}, new={has_new}")

# 保留第一个新script，删除包含旧计费逻辑的script
# 但要注意不要删掉新的登录/注册JS
# 策略：保留包含handleLogin的script，删除包含confirmRecharge/renderBills的script

for i, (s, e, content) in enumerate(scripts):
    if 'confirmRecharge' in content or 'renderBills' in content:
        # 这是旧的script块，删除
        c = c[:s] + c[e:]
        print(f"2. Removed old script block {i}")
        break

# 3. 删除残留的旧模态框
for modal_id in ['rechargeModal']:
    # 清理可能留下的空行和空div
    c = c.replace(f'id="{modal_id}"', '')
    
# 4. 删除旧的CSS样式（充值/账单相关）
# 找style块中旧的class定义
old_css_classes = [
    '.recharge-option', '.recharge-options', '.recharge-custom', '.recharge-option-value',
    '.recharge-option-bonus', '.recharge-option.selected', '.bill-table', '.bill-type',
    '.bill-type-dot', '.bill-amount', '.bill-amount-positive', '.bill-amount-negative',
    '.console-balance', '.balance-label', '.balance-value', '.balance-actions',
    '.console-grid', '.stats-grid', '.stat-card', '.stat-card-value', '.stat-card-label',
    '.usage-chart', '.chart-bar', '.chart-labels'
]

# 简单方案：直接删除style中包含这些class的行
lines = c.split('\n')
new_lines = []
skip = False
for line in lines:
    stripped = line.strip()
    # 检查是否是旧的CSS类定义开始
    if any(stripped.startswith(cls) or stripped.startswith(cls.replace('.', '')) for cls in old_css_classes):
        skip = True
    if skip and stripped == '}':
        skip = False
        continue
    if not skip:
        new_lines.append(line)

c = '\n'.join(new_lines)
print("3. Old CSS cleaned")

# 5. 确认没有残留的旧计费元素
remaining_old = ['充值余额', '¥10', '¥50', '¥100', '赠送', 'confirmRecharge', 'renderBills', 'billsContainer', 'rechargeModal']
for kw in remaining_old:
    if kw in c:
        print(f"  ⚠️ Still has: {kw}")

open(f"{FRONTEND}/console.html", "w", encoding="utf-8").write(c)
print("4. File saved")
print("DONE")

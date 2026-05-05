#!/bin/bash
# PolicyPilot Token API V1 测试脚本

BASE_URL="http://localhost:8002"

echo "============================================"
echo " PolicyPilot Token API V1 测试脚本"
echo "============================================"
echo ""

# 注册客户
echo "【1】注册新客户"
echo "命令: POST /api/token/register"
RESPONSE=$(curl -s -X POST "$BASE_URL/api/token/register" \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"测试企业","company_name":"测试科技有限公司","email":"test@test.com","initial_balance":100.0}')
echo "$RESPONSE" | python3 -m json.tool

# 提取API Key
API_KEY=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('api_key',''))" 2>/dev/null)
if [ -z "$API_KEY" ]; then
  echo "使用已有API Key测试..."
  API_KEY="pp_live_33b61111f41033ec"
fi
echo "API_KEY: $API_KEY"
echo ""

# 基础政策查询
echo "【2】基础政策查询 (0.1元/次)"
echo "命令: POST /api/token/query"
curl -s -X POST "$BASE_URL/api/token/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name":"测试科技有限公司",
    "district":"海珠",
    "industry":"人工智能",
    "established_years":2,
    "revenue_scale":"500-2000万",
    "employee_count":50,
    "has_ip":true,
    "is_high_tech":true
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✅ 成功! 匹配{d[\"total_matches\"]}条政策，费用{d[\"cost\"]}元')"
echo ""

# 高级政策查询
echo "【3】高级政策查询 (0.5元/次)"
echo "命令: POST /api/token/query/advanced"
curl -s -X POST "$BASE_URL/api/token/query/advanced" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "name":"测试科技有限公司",
    "district":"天河",
    "industry":"软件",
    "established_years":5,
    "revenue_scale":"2000万-1亿",
    "employee_count":100,
    "has_ip":true,
    "is_high_tech":true,
    "is_specialized":true,
    "include_ai_analysis":true
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✅ 成功! 匹配{d[\"total_matches\"]}条政策，费用{d[\"cost\"]}元'); print(f'AI分析: {\"有\" if d.get(\"ai_analysis\") else \"无\"}')"
echo ""

# 查询用量
echo "【4】查询用量统计"
echo "命令: GET /api/token/usage"
curl -s "$BASE_URL/api/token/usage" -H "Authorization: Bearer $API_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d['usage']['total']; print(f'✅ 总调用: {u[\"total_calls\"]}次 (基础{u[\"basic_calls\"]}次, 高级{u[\"advanced_calls\"]}次)'); print(f'   总费用: {u[\"total_cost\"]}元, 剩余余额: {d[\"current_balance\"]}元')"
echo ""

# 查询账单
echo "【5】查询月度账单"
echo "命令: GET /api/token/bill"
curl -s "$BASE_URL/api/token/bill" -H "Authorization: Bearer $API_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); b=d['bills'][0] if d['bills'] else {}; print(f'✅ 账单月份: {b.get(\"bill_month\",\"N/A\")}'); print(f'   总调用: {b.get(\"total_calls\",0)}次'); print(f'   总费用: {b.get(\"total_cost\",0)}元')"
echo ""

# 查询余额
echo "【6】查询余额"
echo "命令: GET /api/token/balance"
curl -s "$BASE_URL/api/token/balance" -H "Authorization: Bearer $API_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✅ 当前余额: {d[\"balance\"]}元'); print(f'   限流配置: {d[\"rate_limit\"]}次/分钟')"
echo ""

echo "============================================"
echo " 测试完成!"
echo "============================================"

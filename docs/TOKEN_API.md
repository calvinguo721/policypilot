# PolicyPilot Token API V1 文档

## 概述

Token API是政策通PolicyPilot的计费API接口，采用按查询计费模式，支持基础查询和高级查询（含AI解读）。

## 定价

| 查询类型 | 价格 | 说明 |
|---------|------|------|
| 基础查询 | 0.1元/次 | 按企业画像匹配，返回政策列表 |
| 高级查询 | 0.5元/次 | 包含AI政策解读、申报建议、风险提醒 |

## API端点

### 1. 注册客户
```
POST /api/token/register
Content-Type: application/json

{
  "customer_name": "联系人名称",
  "company_name": "公司名称",
  "email": "email@example.com",
  "phone": "13800138000",
  "initial_balance": 100.0
}
```

响应:
```json
{
  "success": true,
  "data": {
    "customer_id": 1,
    "api_key": "pp_live_xxxxxxxxxxxxxxxx",
    "api_secret": "32位密钥",
    "balance": 100.0,
    "rate_limit": 60
  }
}
```

### 2. 充值余额
```
POST /api/token/recharge
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "amount": 50.0
}
```

### 3. 基础政策查询
```
POST /api/token/query
X-API-Key: <API_KEY>
Content-Type: application/json

{
  "name": "企业名称",
  "district": "海珠",
  "industry": "人工智能",
  "established_years": 2,
  "revenue_scale": "500-2000万",
  "employee_count": 50,
  "has_ip": true,
  "is_high_tech": true,
  "is_specialized": false,
  "has_vc_investment": false
}
```

### 4. 高级政策查询（含AI解读）
```
POST /api/token/query/advanced
X-API-Key: <API_KEY>
Content-Type: application/json

{
  "name": "企业名称",
  "district": "海珠",
  "industry": "人工智能",
  "established_years": 2,
  "revenue_scale": "500-2000万",
  "employee_count": 50,
  "has_ip": true,
  "is_high_tech": true,
  "is_specialized": false,
  "has_vc_investment": false,
  "include_ai_analysis": true
}
```

### 5. 查询用量统计
```
GET /api/token/usage?days=30
Authorization: Bearer <API_KEY>
```

### 6. 查询账单
```
GET /api/token/bill?month=2026-05
Authorization: Bearer <API_KEY>
```

### 7. 查询余额
```
GET /api/token/balance
Authorization: Bearer <API_KEY>
```

### 8. API信息
```
GET /api/token/info
```

## 认证方式

API Key通过请求头传递，支持两种方式：
1. `X-API-Key: <API_KEY>`
2. `Authorization: Bearer <API_KEY>`

## 限流配置

- 默认每分钟60次请求
- 可根据客户需求调整（1-1000次/分钟）

## 错误码

| HTTP状态码 | error | 说明 |
|-----------|-------|------|
| 401 | missing_api_key | 未提供API Key |
| 401 | invalid_api_key | API Key无效 |
| 402 | insufficient_balance | 余额不足 |
| 429 | rate_limit_exceeded | 请求过于频繁 |

## 测试脚本

```bash
./test_token_api.sh
```

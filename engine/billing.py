"""
计量计费系统
调用次数统计、Token计价、账单生成
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

# 数据库文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "policy_pilot.db")

# ========== 计费配置 ==========
PRICING = {
    "basic": 0.1,      # 基础查询：0.1元/次
    "advanced": 0.5,    # 高级查询（含AI解读）：0.5元/次
}

# 每分钟最大请求数限制
DEFAULT_RATE_LIMIT = 60


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def log_api_usage(
    customer_id: int,
    api_key: str,
    endpoint: str,
    query_type: str = "basic",
    params: str = None,
    result_count: int = 0,
    response_time_ms: int = 0,
    ip_address: str = None
) -> int:
    """记录API调用日志"""
    cost = PRICING.get(query_type, PRICING["basic"])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO api_usage_logs 
            (customer_id, api_key, endpoint, query_type, params, result_count, cost, response_time_ms, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_id, api_key, endpoint, query_type, params, result_count, cost, response_time_ms, ip_address))
        
        conn.commit()
        log_id = cursor.lastrowid
        
        # 更新月度账单
        _update_monthly_bill(customer_id, query_type, cost)
        
        return log_id
        
    except Exception as e:
        print(f"❌ 记录API日志失败: {e}")
        return -1
    finally:
        conn.close()


def _update_monthly_bill(customer_id: int, query_type: str, cost: float):
    """更新月度账单"""
    now = datetime.now()
    bill_month = now.strftime("%Y-%m")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查是否存在当月账单
        cursor.execute("""
            SELECT id, total_calls, basic_calls, advanced_calls, total_cost
            FROM monthly_bills
            WHERE customer_id = ? AND bill_month = ?
        """, (customer_id, bill_month))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有账单
            if query_type == "advanced":
                cursor.execute("""
                    UPDATE monthly_bills
                    SET total_calls = total_calls + 1,
                        advanced_calls = advanced_calls + 1,
                        total_cost = total_cost + ?
                    WHERE id = ?
                """, (cost, existing['id']))
            else:
                cursor.execute("""
                    UPDATE monthly_bills
                    SET total_calls = total_calls + 1,
                        basic_calls = basic_calls + 1,
                        total_cost = total_cost + ?
                    WHERE id = ?
                """, (cost, existing['id']))
        else:
            # 创建新账单
            basic_calls = 1 if query_type == "basic" else 0
            advanced_calls = 1 if query_type == "advanced" else 0
            
            cursor.execute("""
                INSERT INTO monthly_bills 
                (customer_id, bill_month, total_calls, basic_calls, advanced_calls, total_cost)
                VALUES (?, ?, 1, ?, ?, ?)
            """, (customer_id, bill_month, basic_calls, advanced_calls, cost))
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ 更新月度账单失败: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_usage_stats(customer_id: int, days: int = 30) -> Dict[str, Any]:
    """获取用量统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    # 每日统计
    cursor.execute("""
        SELECT DATE(created_at) as date,
               COUNT(*) as total_calls,
               SUM(CASE WHEN query_type = 'basic' THEN 1 ELSE 0 END) as basic_calls,
               SUM(CASE WHEN query_type = 'advanced' THEN 1 ELSE 0 END) as advanced_calls,
               SUM(cost) as total_cost
        FROM api_usage_logs
        WHERE customer_id = ? AND created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date DESC
    """, (customer_id, start_date))
    
    daily_stats = [dict(row) for row in cursor.fetchall()]
    
    # 总计
    cursor.execute("""
        SELECT COUNT(*) as total_calls,
               SUM(CASE WHEN query_type = 'basic' THEN 1 ELSE 0 END) as basic_calls,
               SUM(CASE WHEN query_type = 'advanced' THEN 1 ELSE 0 END) as advanced_calls,
               SUM(cost) as total_cost,
               SUM(response_time_ms) / COUNT(*) as avg_response_time
        FROM api_usage_logs
        WHERE customer_id = ? AND created_at >= ?
    """, (customer_id, start_date))
    
    total = dict(cursor.fetchone())
    
    # 最近10次调用
    cursor.execute("""
        SELECT id, endpoint, query_type, result_count, cost, response_time_ms, created_at
        FROM api_usage_logs
        WHERE customer_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (customer_id,))
    
    recent_calls = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "customer_id": customer_id,
        "period_days": days,
        "start_date": start_date,
        "end_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "daily_stats": daily_stats,
        "recent_calls": recent_calls
    }


def get_monthly_bill(customer_id: int, bill_month: str = None) -> Optional[Dict[str, Any]]:
    """获取月度账单"""
    if bill_month is None:
        bill_month = datetime.now().strftime("%Y-%m")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM monthly_bills
        WHERE customer_id = ? AND bill_month = ?
    """, (customer_id, bill_month))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None


def get_bill_history(customer_id: int, limit: int = 12) -> List[Dict[str, Any]]:
    """获取账单历史"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM monthly_bills
        WHERE customer_id = ?
        ORDER BY bill_month DESC
        LIMIT ?
    """, (customer_id, limit))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results


def get_current_month_usage(customer_id: int) -> Dict[str, Any]:
    """获取当月使用情况"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    bill_month = datetime.now().strftime("%Y-%m")
    
    cursor.execute("""
        SELECT total_calls, basic_calls, advanced_calls, total_cost
        FROM monthly_bills
        WHERE customer_id = ? AND bill_month = ?
    """, (customer_id, bill_month))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    
    return {
        "total_calls": 0,
        "basic_calls": 0,
        "advanced_calls": 0,
        "total_cost": 0.0
    }


def get_rate_limit_usage(customer_id: int) -> Dict[str, Any]:
    """获取当前限流窗口使用情况"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取限流配置
    cursor.execute("SELECT rate_limit FROM api_customers WHERE id = ?", (customer_id,))
    customer = cursor.fetchone()
    rate_limit = customer['rate_limit'] if customer else DEFAULT_RATE_LIMIT
    
    # 获取最近1分钟的调用次数
    one_minute_ago = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        SELECT COUNT(*) as calls_in_window
        FROM api_usage_logs
        WHERE customer_id = ? AND created_at >= ?
    """, (customer_id, one_minute_ago))
    
    calls_in_window = cursor.fetchone()['calls_in_window']
    
    conn.close()
    
    return {
        "customer_id": customer_id,
        "rate_limit": rate_limit,
        "calls_in_last_minute": calls_in_window,
        "remaining": max(0, rate_limit - calls_in_window),
        "reset_at": (datetime.now() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    }


def calculate_cost(query_type: str) -> float:
    """计算查询费用"""
    return PRICING.get(query_type, PRICING["basic"])


def get_pricing_info() -> Dict[str, Any]:
    """获取计费定价信息"""
    return {
        "pricing": PRICING,
        "description": {
            "basic": "基础政策查询 - 按企业画像匹配，返回政策列表",
            "advanced": "高级查询 - 包含AI政策解读和分析"
        },
        "unit": "元/次"
    }


def get_usage_summary() -> Dict[str, Any]:
    """获取平台总用量统计"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT customer_id) as total_customers,
               COUNT(*) as total_calls,
               SUM(cost) as total_revenue
        FROM api_usage_logs
    """)
    
    total = dict(cursor.fetchone())
    
    # 按月统计
    cursor.execute("""
        SELECT bill_month, COUNT(*) as customers, SUM(total_calls) as calls, SUM(total_cost) as revenue
        FROM monthly_bills
        GROUP BY bill_month
        ORDER BY bill_month DESC
        LIMIT 12
    """)
    
    monthly = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_customers": total['total_customers'] or 0,
        "total_calls": total['total_calls'] or 0,
        "total_revenue": total['total_revenue'] or 0.0,
        "monthly_stats": monthly
    }

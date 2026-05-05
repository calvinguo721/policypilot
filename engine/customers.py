"""
客户管理系统
管理企业客户的注册、API Key生成和认证
"""
import sqlite3
import hashlib
import secrets
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "policy_pilot.db")


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_token_tables():
    """初始化Token相关表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Token客户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT UNIQUE NOT NULL,
            company_name TEXT NOT NULL,
            contact TEXT,
            email TEXT,
            api_key TEXT UNIQUE NOT NULL,
            api_secret TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP
        )
    """)
    
    # 用量记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            amount REAL NOT NULL,
            cost REAL NOT NULL,
            request_data TEXT,
            response_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES token_customers(customer_id)
        )
    """)
    
    # 限流记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            request_count INTEGER DEFAULT 0,
            FOREIGN KEY (customer_id) REFERENCES token_customers(customer_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Token表初始化完成")


def generate_api_key() -> tuple:
    """生成API Key和Secret"""
    key = f"pp_{secrets.token_hex(16)}"
    secret = secrets.token_hex(32)
    return key, secret


def hash_secret(secret: str) -> str:
    """哈希Secret用于存储"""
    return hashlib.sha256(secret.encode()).hexdigest()


def register_customer(company_name: str, contact: str = None, email: str = None) -> Dict[str, Any]:
    """注册新客户并生成API Key"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 生成客户ID
        customer_id = f"customer_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
        
        # 生成API Key和Secret
        api_key, api_secret = generate_api_key()
        
        # 插入客户记录
        cursor.execute("""
            INSERT INTO token_customers 
            (customer_id, company_name, contact, email, api_key, api_secret, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (customer_id, company_name, contact, email, api_key, hash_secret(api_secret), 100.0))
        
        conn.commit()
        
        return {
            "success": True,
            "customer_id": customer_id,
            "api_key": api_key,
            "api_secret": api_secret,
            "balance": 100.0,
            "message": "注册成功，初始赠送100元余额"
        }
        
    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"注册失败: {str(e)}"
        }
    finally:
        conn.close()


def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """验证API Key并返回客户信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM token_customers 
        WHERE api_key = ? AND status = 'active'
    """, (api_key,))
    
    result = cursor.fetchone()
    
    if result:
        # 更新最后使用时间
        cursor.execute("""
            UPDATE token_customers SET last_used = CURRENT_TIMESTAMP 
            WHERE customer_id = ?
        """, (dict(result)['customer_id'],))
        conn.commit()
        
    conn.close()
    
    if result:
        return dict(result)
    return None


def get_customer_info(customer_id: str) -> Optional[Dict[str, Any]]:
    """获取客户信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM token_customers WHERE customer_id = ?", (customer_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None


def get_balance(customer_id: str) -> Optional[float]:
    """获取客户余额"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM token_customers WHERE customer_id = ?", (customer_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result['balance']
    return None


def deduct_balance(customer_id: str, amount: float) -> bool:
    """扣除余额"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查余额
        cursor.execute("SELECT balance FROM token_customers WHERE customer_id = ?", (customer_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
            
        current_balance = result['balance']
        
        if current_balance < amount:
            conn.close()
            return False
        
        # 扣除余额
        cursor.execute("""
            UPDATE token_customers 
            SET balance = balance - ? 
            WHERE customer_id = ?
        """, (amount, customer_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"扣费失败: {e}")
        return False
    finally:
        conn.close()


def add_balance(customer_id: str, amount: float) -> bool:
    """充值余额"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE token_customers 
            SET balance = balance + ? 
            WHERE customer_id = ?
        """, (amount, customer_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"充值失败: {e}")
        return False
    finally:
        conn.close()


def record_usage(
    customer_id: str, 
    operation_type: str, 
    amount: float, 
    cost: float,
    request_data: str = None,
    response_data: str = None
) -> bool:
    """记录用量"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO token_usage 
            (customer_id, operation_type, amount, cost, request_data, response_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (customer_id, operation_type, amount, cost, request_data, response_data))
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"记录用量失败: {e}")
        return False
    finally:
        conn.close()


def get_usage_summary(customer_id: str, days: int = 30) -> List[Dict[str, Any]]:
    """获取用量汇总"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            operation_type,
            COUNT(*) as count,
            SUM(cost) as total_cost
        FROM token_usage
        WHERE customer_id = ? 
        AND created_at >= datetime('now', '-' || ? || ' days')
        GROUP BY DATE(created_at), operation_type
        ORDER BY date DESC
    """, (customer_id, days))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results


def get_total_usage(customer_id: str, days: int = 30) -> Dict[str, Any]:
    """获取总用量"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_requests,
            SUM(cost) as total_cost,
            operation_type
        FROM token_usage
        WHERE customer_id = ? 
        AND created_at >= datetime('now', '-' || ? || ' days')
        GROUP BY operation_type
    """, (customer_id, days))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # 计算总计
    total_requests = sum(r['total_requests'] for r in results)
    total_cost = sum(r['total_cost'] for r in results)
    
    return {
        "total_requests": total_requests,
        "total_cost": round(total_cost, 2),
        "by_type": results
    }


def check_rate_limit(customer_id: str, max_requests: int = 100, window_seconds: int = 60) -> tuple:
    """
    检查限流
    返回: (是否允许, 剩余请求数, 剩余秒数)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取或创建限流记录
        cursor.execute("""
            SELECT * FROM token_rate_limits 
            WHERE customer_id = ?
            AND window_start >= datetime('now', '-' || ? || ' seconds')
            ORDER BY window_start DESC LIMIT 1
        """, (customer_id, window_seconds))
        
        record = cursor.fetchone()
        
        if record:
            record_dict = dict(record)
            request_count = record_dict['request_count']
            remaining = max_requests - request_count
            
            if remaining <= 0:
                conn.close()
                return False, 0, window_seconds  # 需要等待
            
            # 更新计数
            cursor.execute("""
                UPDATE token_rate_limits 
                SET request_count = request_count + 1 
                WHERE id = ?
            """, (record_dict['id'],))
        else:
            # 创建新记录
            cursor.execute("""
                INSERT INTO token_rate_limits (customer_id, request_count)
                VALUES (?, 1)
            """, (customer_id,))
            remaining = max_requests - 1
        
        conn.commit()
        conn.close()
        return True, remaining, 0
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"限流检查失败: {e}")
        return True, max_requests, 0  # 出错时放行



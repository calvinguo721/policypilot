"""
客户管理模块
管理API客户、API Key生成、预充值
"""
import sqlite3
import secrets
import string
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

# 数据库文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "policy_pilot.db")


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_token_tables():
    """初始化Token相关数据表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # API客户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            company_name TEXT,
            email TEXT,
            phone TEXT,
            api_key TEXT UNIQUE NOT NULL,
            api_secret TEXT,
            status TEXT DEFAULT 'active',
            rate_limit INTEGER DEFAULT 60,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 余额变动记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balance_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES api_customers(id)
        )
    """)
    
    # API调用记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            api_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            query_type TEXT DEFAULT 'basic',
            params TEXT,
            result_count INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0,
            response_time_ms INTEGER DEFAULT 0,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES api_customers(id)
        )
    """)
    
    # 月度账单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            bill_month TEXT NOT NULL,
            total_calls INTEGER DEFAULT 0,
            basic_calls INTEGER DEFAULT 0,
            advanced_calls INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES api_customers(id),
            UNIQUE(customer_id, bill_month)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Token客户表初始化完成")


def generate_api_key() -> str:
    """生成API Key: pp_live_xxxxxxxx（16位随机hex）"""
    random_part = secrets.token_hex(8)
    return f"pp_live_{random_part}"


def generate_api_secret() -> str:
    """生成API Secret（32位随机hex）"""
    return secrets.token_hex(16)


def register_customer(
    customer_name: str,
    company_name: str = None,
    email: str = None,
    phone: str = None,
    initial_balance: float = 0.0
) -> Dict[str, Any]:
    """注册新客户，生成API Key"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查是否已存在同名客户
        cursor.execute(
            "SELECT id FROM api_customers WHERE customer_name = ? OR (email = ? AND email IS NOT NULL)",
            (customer_name, email)
        )
        existing = cursor.fetchone()
        if existing:
            return {
                "success": False,
                "message": "客户已存在",
                "customer_id": existing['id']
            }
        
        # 生成API Key和Secret
        api_key = generate_api_key()
        api_secret = generate_api_secret()
        
        # 插入新客户
        cursor.execute("""
            INSERT INTO api_customers 
            (customer_name, company_name, email, phone, api_key, api_secret, balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (customer_name, company_name, email, phone, api_key, api_secret, initial_balance))
        
        customer_id = cursor.lastrowid
        
        # 如果有初始充值，记录变动
        if initial_balance > 0:
            cursor.execute("""
                INSERT INTO balance_transactions 
                (customer_id, amount, transaction_type, description)
                VALUES (?, ?, 'deposit', '初始充值')
            """, (customer_id, initial_balance))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "客户注册成功",
            "customer_id": customer_id,
            "api_key": api_key,
            "api_secret": api_secret,
            "balance": initial_balance,
            "rate_limit": 60
        }
        
    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"注册失败: {str(e)}"
        }
    finally:
        conn.close()


def get_customer_by_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """根据API Key获取客户信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM api_customers WHERE api_key = ? AND status = 'active'
    """, (api_key,))
    
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None


def get_customer_by_id(customer_id: int) -> Optional[Dict[str, Any]]:
    """根据客户ID获取客户信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM api_customers WHERE id = ?", (customer_id,))
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None


def verify_api_key(api_key: str) -> Dict[str, Any]:
    """验证API Key有效性"""
    customer = get_customer_by_api_key(api_key)
    
    if not customer:
        return {
            "valid": False,
            "message": "无效的API Key"
        }
    
    # 检查余额
    if customer['balance'] < 0.1:  # 最低消费0.1元
        return {
            "valid": False,
            "message": "余额不足，请先充值",
            "balance": customer['balance']
        }
    
    return {
        "valid": True,
        "customer_id": customer['id'],
        "customer_name": customer['customer_name'],
        "balance": customer['balance'],
        "rate_limit": customer['rate_limit']
    }


def recharge_balance(customer_id: int, amount: float, description: str = None) -> Dict[str, Any]:
    """充值余额"""
    if amount <= 0:
        return {
            "success": False,
            "message": "充值金额必须大于0"
        }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 更新余额
        cursor.execute("""
            UPDATE api_customers 
            SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (amount, customer_id))
        
        # 记录变动
        desc = description or f"充值 {amount} 元"
        cursor.execute("""
            INSERT INTO balance_transactions 
            (customer_id, amount, transaction_type, description)
            VALUES (?, ?, 'deposit', ?)
        """, (customer_id, amount, desc))
        
        # 获取新余额
        cursor.execute("SELECT balance FROM api_customers WHERE id = ?", (customer_id,))
        new_balance = cursor.fetchone()['balance']
        
        conn.commit()
        
        return {
            "success": True,
            "message": "充值成功",
            "amount": amount,
            "new_balance": new_balance
        }
        
    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"充值失败: {str(e)}"
        }
    finally:
        conn.close()


def deduct_balance(customer_id: int, amount: float, description: str = None) -> Dict[str, Any]:
    """扣减余额（消费）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查当前余额
        cursor.execute("SELECT balance FROM api_customers WHERE id = ?", (customer_id,))
        result = cursor.fetchone()
        
        if not result:
            return {
                "success": False,
                "message": "客户不存在"
            }
        
        current_balance = result['balance']
        
        if current_balance < amount:
            return {
                "success": False,
                "message": "余额不足",
                "current_balance": current_balance,
                "required": amount
            }
        
        # 扣减余额
        cursor.execute("""
            UPDATE api_customers 
            SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (amount, customer_id))
        
        # 记录变动
        desc = description or f"API调用扣费 {amount} 元"
        cursor.execute("""
            INSERT INTO balance_transactions 
            (customer_id, amount, transaction_type, description)
            VALUES (?, ?, 'consume', ?)
        """, (customer_id, -amount, desc))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "扣费成功",
            "amount": amount,
            "new_balance": current_balance - amount
        }
        
    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"扣费失败: {str(e)}"
        }
    finally:
        conn.close()


def get_balance_transactions(customer_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """获取余额变动记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM balance_transactions 
        WHERE customer_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (customer_id, limit))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results


def get_all_customers() -> List[Dict[str, Any]]:
    """获取所有客户列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, customer_name, company_name, email, api_key, status, 
               balance, rate_limit, created_at
        FROM api_customers
        ORDER BY created_at DESC
    """)
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results


def update_customer_status(customer_id: int, status: str) -> Dict[str, Any]:
    """更新客户状态"""
    if status not in ['active', 'suspended', 'deleted']:
        return {
            "success": False,
            "message": "无效的状态"
        }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE api_customers 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, customer_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"状态已更新为 {status}"
        }
        
    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"更新失败: {str(e)}"
        }
    finally:
        conn.close()


def update_rate_limit(customer_id: int, rate_limit: int) -> Dict[str, Any]:
    """更新客户限流配置"""
    if rate_limit < 1 or rate_limit > 1000:
        return {
            "success": False,
            "message": "限流值必须在1-1000之间"
        }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE api_customers 
            SET rate_limit = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (rate_limit, customer_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "限流配置已更新",
            "rate_limit": rate_limit
        }
        
    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"更新失败: {str(e)}"
        }
    finally:
        conn.close()


# 初始化Token表
init_token_tables()

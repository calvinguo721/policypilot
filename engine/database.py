"""
数据库操作模块
使用SQLite存储用户和诊断结果
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# 数据库文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "policy_pilot.db")


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone VARCHAR(20) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    # 诊断结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnosis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company_name TEXT NOT NULL,
            company_district TEXT,
            company_industry TEXT,
            company_revenue TEXT,
            company_established INTEGER,
            company_employees INTEGER,
            has_ip INTEGER DEFAULT 0,
            is_high_tech INTEGER DEFAULT 0,
            is_specialized INTEGER DEFAULT 0,
            has_vc INTEGER DEFAULT 0,
            matched_policies TEXT,
            total_matches INTEGER DEFAULT 0,
            highly_recommended INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据库初始化完成: {DB_PATH}")


def create_user(phone: str) -> int:
    """创建新用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (phone) VALUES (?)",
            (phone,)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        # 用户已存在，返回现有用户ID
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        result = cursor.fetchone()
        return result['id'] if result else None
    finally:
        conn.close()


def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """根据手机号获取用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """根据ID获取用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return dict(result)
    return None


def update_last_login(user_id: int):
    """更新最后登录时间"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
        (user_id,)
    )
    conn.commit()
    conn.close()


def save_diagnosis_result(
    user_id: int,
    company_data: Dict[str, Any],
    match_result: Dict[str, Any]
) -> int:
    """保存诊断结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 提取企业信息
    company = company_data if isinstance(company_data, dict) else {}
    
    # 提取匹配结果
    matched_policies = match_result.get('matched_policies', [])
    matched_policies_json = json.dumps(matched_policies, ensure_ascii=False)
    
    cursor.execute("""
        INSERT INTO diagnosis_results (
            user_id, company_name, company_district, company_industry,
            company_revenue, company_established, company_employees,
            has_ip, is_high_tech, is_specialized, has_vc,
            matched_policies, total_matches, highly_recommended
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        company.get('name', ''),
        company.get('district', ''),
        company.get('industry', ''),
        company.get('revenue_scale', ''),
        company.get('established_years', 0),
        company.get('employee_count', 0),
        int(company.get('has_ip', False)),
        int(company.get('is_high_tech', False)),
        int(company.get('is_specialized', False)),
        int(company.get('has_vc_investment', False)),
        matched_policies_json,
        match_result.get('total_matches', 0),
        match_result.get('highly_recommended_count', 0)
    ))
    
    conn.commit()
    result_id = cursor.lastrowid
    conn.close()
    
    return result_id


def get_user_results(user_id: int) -> List[Dict[str, Any]]:
    """获取用户的所有诊断结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM diagnosis_results 
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    results = []
    for row in cursor.fetchall():
        result = dict(row)
        # 解析JSON字段
        if result.get('matched_policies'):
            import json
            result['matched_policies'] = json.loads(result['matched_policies'])
        results.append(result)
    
    conn.close()
    return results


def get_result_by_id(result_id: int) -> Optional[Dict[str, Any]]:
    """根据ID获取诊断结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM diagnosis_results WHERE id = ?
    """, (result_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        r = dict(result)
        if r.get('matched_policies'):
            import json
            r['matched_policies'] = json.loads(r['matched_policies'])
        return r
    return None


import json

# 初始化数据库
init_database()

"""
认证模块
处理用户注册、登录和token验证
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from database import create_user, get_user_by_phone, get_user_by_id, update_last_login

# Token有效期（天）
TOKEN_EXPIRY_DAYS = 30

# 简单的token存储（生产环境应使用Redis）
_token_store: Dict[str, Dict[str, Any]] = {}


def generate_token(user_id: int) -> str:
    """生成用户token"""
    # 生成随机token
    raw_token = f"{user_id}:{secrets.token_hex(16)}:{datetime.now().isoformat()}"
    token = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # 存储token
    _token_store[token] = {
        'user_id': user_id,
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(days=TOKEN_EXPIRY_DAYS)
    }
    
    return token


def verify_token(token: str) -> Optional[int]:
    """验证token并返回用户ID"""
    if not token:
        return None
    
    token_data = _token_store.get(token)
    if not token_data:
        return None
    
    # 检查是否过期
    if datetime.now() > token_data['expires_at']:
        del _token_store[token]
        return None
    
    return token_data['user_id']


def register(phone: str, verify_code: str = None) -> Dict[str, Any]:
    """
    用户注册
    
    Args:
        phone: 手机号
        verify_code: 验证码（mock模式：123456）
    
    Returns:
        包含success、message、user_id、token的字典
    """
    # 验证手机号格式
    if not phone or len(phone) != 11 or not phone.isdigit():
        return {
            'success': False,
            'message': '请输入正确的11位手机号'
        }
    
    # Mock验证码验证（输入123456即可通过）
    if verify_code and verify_code != '123456':
        return {
            'success': False,
            'message': '验证码错误，请输入123456'
        }
    
    # 创建或获取用户
    user_id = create_user(phone)
    
    if not user_id:
        return {
            'success': False,
            'message': '注册失败，请稍后重试'
        }
    
    # 生成token
    token = generate_token(user_id)
    update_last_login(user_id)
    
    return {
        'success': True,
        'message': '注册成功',
        'user_id': user_id,
        'token': token
    }


def login(phone: str, verify_code: str = None) -> Dict[str, Any]:
    """
    用户登录
    
    Args:
        phone: 手机号
        verify_code: 验证码（mock模式：123456）
    
    Returns:
        包含success、message、user_id、token的字典
    """
    # 验证手机号格式
    if not phone or len(phone) != 11 or not phone.isdigit():
        return {
            'success': False,
            'message': '请输入正确的11位手机号'
        }
    
    # Mock验证码验证
    if verify_code and verify_code != '123456':
        return {
            'success': False,
            'message': '验证码错误，请输入123456'
        }
    
    # 检查用户是否存在
    user = get_user_by_phone(phone)
    if not user:
        # 不存在则自动注册
        return register(phone, verify_code)
    
    # 生成token
    token = generate_token(user['id'])
    update_last_login(user['id'])
    
    return {
        'success': True,
        'message': '登录成功',
        'user_id': user['id'],
        'token': token
    }


def get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """获取当前登录用户信息"""
    user_id = verify_token(token)
    if not user_id:
        return None
    
    return get_user_by_id(user_id)


def logout(token: str) -> bool:
    """登出"""
    if token in _token_store:
        del _token_store[token]
        return True
    return False


def get_user_info(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户信息（脱敏）"""
    user = get_user_by_id(user_id)
    if user:
        # 脱敏手机号
        user['phone_masked'] = user['phone'][:3] + '****' + user['phone'][7:]
        del user['phone']
    return user

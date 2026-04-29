#!/usr/bin/env python3
"""
飞书文档同步到GitHub脚本
每日定时执行，将飞书内容同步到GitHub仓库
"""

import os
import subprocess
import json
from datetime import datetime

# 配置 - 从环境变量读取敏感信息
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise ValueError('请设置环境变量 GITHUB_TOKEN')

GITHUB_REPO = 'calvinguo721/policypilot'
GITHUB_EMAIL = 'calvinguo721@gmail.com'
GITHUB_NAME = 'calvinguo721'

# 本地仓库路径
REPO_PATH = '/app/data/所有对话/主对话/policypilot'

def run_command(cmd, cwd=None):
    """执行命令"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def git_commit_and_push(message):
    """Git提交并推送"""
    os.chdir(REPO_PATH)
    
    # 配置git
    run_command(f'git config user.email "{GITHUB_EMAIL}"')
    run_command(f'git config user.name "{GITHUB_NAME}"')
    
    # 添加所有更改
    run_command('git add .')
    
    # 检查是否有更改
    success, stdout, stderr = run_command('git status --porcelain')
    if not stdout.strip():
        print('没有需要提交的更改')
        return True
    
    # 提交
    success, stdout, stderr = run_command(f'git commit -m "{message}"')
    if not success:
        print(f'提交失败: {stderr}')
        return False
    
    # 推送
    success, stdout, stderr = run_command(f'git push https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git main')
    if not success:
        print(f'推送失败: {stderr}')
        return False
    
    print(f'成功提交并推送: {message}')
    return True

def sync_feishu_docs():
    """
    同步飞书文档
    这里需要配合飞书CLI使用
    """
    # TODO: 实现飞书文档读取和转换逻辑
    # 1. 读取飞书SOP文档
    # 2. 转换为Markdown
    # 3. 保存到docs/目录
    pass

def sync_feishu_sheets():
    """
    同步飞书表格
    导出为CSV格式
    """
    # TODO: 实现飞书表格读取和导出逻辑
    # 1. 读取内容运营表
    # 2. 读取补贴申报表
    # 3. 导出为CSV到data/目录
    pass

def sync_local_articles():
    """
    同步本地文章
    从内容创作目录复制到docs/articles/
    """
    source_dir = '/app/data/所有对话/主对话/内容创作'
    target_dir = os.path.join(REPO_PATH, 'docs/articles')
    
    if not os.path.exists(source_dir):
        print(f'源目录不存在: {source_dir}')
        return
    
    # 复制所有md文件
    for filename in os.listdir(source_dir):
        if filename.endswith('.md'):
            src = os.path.join(source_dir, filename)
            dst = os.path.join(target_dir, filename)
            
            # 读取源文件
            with open(src, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 写入目标文件
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f'同步文章: {filename}')

def main():
    """主函数"""
    print(f'开始同步: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    # 同步本地文章
    sync_local_articles()
    
    # 同步飞书文档（待实现）
    # sync_feishu_docs()
    
    # 同步飞书表格（待实现）
    # sync_feishu_sheets()
    
    # 提交并推送
    today = datetime.now().strftime('%Y-%m-%d')
    git_commit_and_push(f'自动同步: {today}')
    
    print(f'同步完成: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

if __name__ == '__main__':
    main()

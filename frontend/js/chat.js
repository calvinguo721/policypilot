/**
 * 政策通 PolicyPilot - AI对话核心逻辑
 * 申报导航仪，不是搜索工具
 */

// API配置
const API_BASE = window.location.origin;

// 对话状态
const chatState = {
    sessionId: localStorage.getItem('policy_chat_session') || null,
    messages: [],
    isLoading: false
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initChat();
});

// 初始化对话
function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    
    // 绑定发送事件
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    // 绑定回车发送
    if (chatInput) {
        // 自动聚焦输入框
        chatInput.focus();
        
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // 自动调整输入框高度
        chatInput.addEventListener('input', autoResizeInput);
    }
    
    // 加载历史消息
    loadMessages();
    
    // 监听粘贴事件
    if (chatInput) {
        chatInput.addEventListener('paste', (e) => {
            setTimeout(autoResizeInput, 0);
        });
    }
}

// 自动调整输入框高度
function autoResizeInput() {
    const chatInput = document.getElementById('chatInput');
    if (!chatInput) return;
    
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
}

// 发送消息
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message || chatState.isLoading) return;
    
    // 清空输入框
    input.value = '';
    input.style.height = 'auto';
    
    // 添加用户消息
    addMessage('user', message);
    
    // 显示加载状态
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/agent/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                session_id: chatState.sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error('请求失败');
        }
        
        const data = await response.json();
        
        // 保存session
        if (data.session_id) {
            chatState.sessionId = data.session_id;
            localStorage.setItem('policy_chat_session', data.session_id);
        }
        
        // 添加AI回复
        addMessage('ai', data.reply, data);
        
        // 隐藏加载
        hideLoading();
        
        // 重新聚焦输入框
        input.focus();
        
    } catch (error) {
        console.error('Error:', error);
        hideLoading();
        addMessage('ai', '抱歉，服务暂时不可用，请稍后重试。', null);
    }
}

// 添加消息到界面
function addMessage(role, content, data = null) {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role === 'user' ? 'user-message' : 'ai-message'}`;
    
    if (role === 'ai') {
        messageDiv.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="message-text">${formatMarkdown(content)}</div>
                ${data && data.policies && data.policies.length > 0 ? renderPolicyCards(data.policies) : ''}
                ${data && data.suggestions ? renderSuggestions(data.suggestions) : ''}
                <div class="message-time">${formatTime()}</div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${escapeHtml(content)}</div>
                <div class="message-time">${formatTime()}</div>
            </div>
            <div class="message-avatar user-avatar">👤</div>
        `;
    }
    
    messagesContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
    
    // 保存消息
    chatState.messages.push({ role, content, data });
}

// 滚动到底部
function scrollToBottom() {
    const messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer) {
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
    }
}

// 渲染政策卡片
function renderPolicyCards(policies) {
    if (!policies || policies.length === 0) return '';
    
    let html = '<div class="policy-cards">';
    
    policies.forEach((policy, index) => {
        const score = Math.round(policy.match_score || 0);
        const stars = '⭐'.repeat(Math.min(Math.floor(score / 20), 5));
        const recommended = policy.is_highly_recommended ? '🏆' : '📋';
        
        html += `
            <div class="policy-card" onclick="showPolicyDetail('${policy.id}')">
                <div class="policy-card-header">
                    ${recommended}
                    <span class="policy-name">${escapeHtml(policy.name)}</span>
                    <span class="policy-score">${stars}</span>
                </div>
                <div class="policy-card-body">
                    <div class="policy-info">
                        <span class="policy-tag">${escapeHtml(policy.district)}</span>
                        <span class="policy-tag">${escapeHtml(policy.category)}</span>
                    </div>
                    <div class="policy-amount">
                        <span class="amount-label">💰</span>
                        <span class="amount-text">${escapeHtml(policy.subsidy_amount)}</span>
                    </div>
                    <div class="policy-deadline">
                        <span class="deadline-label">⏰</span>
                        <span class="deadline-text">${escapeHtml(policy.deadline)}</span>
                    </div>
                    ${policy.match_reason_text ? `
                    <div class="policy-reason">
                        <span class="reason-text">✅ ${escapeHtml(policy.match_reason_text)}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="policy-card-footer">
                    <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); showPolicyDetail('${policy.id}')">
                        查看详情
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); generateMaterial('${policy.id}')">
                        申报指南
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

// 渲染建议按钮
function renderSuggestions(suggestions) {
    if (!suggestions || suggestions.length === 0) return '';
    
    let html = '<div class="suggestions">';
    suggestions.forEach(suggestion => {
        html += `
            <button class="suggestion-chip" onclick="askSuggestion('${escapeHtml(suggestion).replace(/'/g, "\\'")}')">
                ${escapeHtml(suggestion)}
            </button>
        `;
    });
    html += '</div>';
    return html;
}

// 推荐问题点击
function askSuggestion(text) {
    document.getElementById('chatInput').value = text;
    sendMessage();
}

// 查看政策详情 - 跳转到详情页
function showPolicyDetail(policyId) {
    window.location.href = `/policy/${policyId}`;
}

// 生成申报材料
function generateMaterial(policyId) {
    showMaterialModal(policyId);
}

// 显示/隐藏加载状态
function showLoading() {
    chatState.isLoading = true;
    const loadingEl = document.getElementById('loadingIndicator');
    if (loadingEl) {
        loadingEl.classList.remove('hidden');
    }
}

function hideLoading() {
    chatState.isLoading = false;
    const loadingEl = document.getElementById('loadingIndicator');
    if (loadingEl) {
        loadingEl.classList.add('hidden');
    }
}

// 格式化Markdown（简化版）
function formatMarkdown(text) {
    if (!text) return '';
    
    // 转义HTML
    let formatted = escapeHtml(text);
    
    // 粗体
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // 换行处理
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

// 转义HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 格式化时间
function formatTime() {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 加载历史消息（简化版，只显示欢迎语）
function loadMessages() {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer || chatState.messages.length > 0) return;
    
    // 显示欢迎语
    const welcomeHTML = `
        <div class="message ai-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <div class="message-text">
                    您好！我是您的<strong>政策申报顾问</strong> 🤖<br><br>
                    告诉我您的情况，我来帮您找政策：<br>
                </div>
                <div class="suggestion-chips">
                    <button class="suggestion-chip" onclick="askSuggestion('我是海珠区的AI创业公司')">
                        💡 我是海珠区的AI创业公司
                    </button>
                    <button class="suggestion-chip" onclick="askSuggestion('天河区软件企业有什么补贴')">
                        💡 天河区软件企业有什么补贴
                    </button>
                    <button class="suggestion-chip" onclick="askSuggestion('专精特新企业怎么申报')">
                        💡 专精特新企业怎么申报
                    </button>
                    <button class="suggestion-chip" onclick="askSuggestion('小微企业租金减免政策')">
                        💡 小微企业租金减免政策
                    </button>
                </div>
                <div class="message-time">${formatTime()}</div>
            </div>
        </div>
    `;
    
    messagesContainer.innerHTML = welcomeHTML;
}

// 政策解读弹窗（申报材料生成）
function showMaterialModal(policyId) {
    // 复用主页面的材料生成逻辑
    if (typeof window.showMaterialModal === 'function') {
        window.showMaterialModal(policyId);
    } else {
        alert('材料生成功能正在开发中，请稍候...');
    }
}

// 移动端适配：触摸滚动
function initMobileScroll() {
    const messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;
    
    // 防止页面整体滚动时影响对话区域
    messagesContainer.addEventListener('touchmove', (e) => {
        if (messagesContainer.scrollHeight - messagesContainer.scrollTop <= messagesContainer.clientHeight + 50) {
            e.stopPropagation();
        }
    }, { passive: true });
}

// 初始化移动端滚动
initMobileScroll();

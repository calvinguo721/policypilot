/**
 * 政策通 PolicyPilot - AI对话核心逻辑
 * 智能补贴计算器，RAG增强版
 */

// API配置
var API_BASE = window.location.origin;

// 对话状态
var chatState = {
    sessionId: localStorage.getItem('policy_chat_session') || null,
    messages: [],
    isLoading: false,
    remainingToday: 999
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initChat();
});

// 初始化对话
function initChat() {
    var chatInput = document.getElementById('chatInput');
    var sendBtn = document.getElementById('sendBtn');
    
    // 绑定发送事件
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    }
    
    // 绑定回车发送
    if (chatInput) {
        // 自动聚焦输入框
        chatInput.focus();
        
        chatInput.addEventListener('keypress', function(e) {
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
        chatInput.addEventListener('paste', function(e) {
            setTimeout(autoResizeInput, 0);
        });
    }

    // 检查URL参数
    checkUrlParams();
}

// 检查URL参数 ?q=xxx
function checkUrlParams() {
    var urlParams = new URLSearchParams(window.location.search);
    var queryParam = urlParams.get('q');
    if (queryParam) {
        // 延迟执行，确保DOM已加载
        setTimeout(function() {
            var input = document.getElementById('chatInput');
            if (input) {
                input.value = queryParam;
                sendMessage();
            }
        }, 300);
    }
}

// 自动调整输入框高度
function autoResizeInput() {
    var chatInput = document.getElementById('chatInput');
    if (!chatInput) return;
    
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
}

// 发送消息
async function sendMessage() {
    var input = document.getElementById('chatInput');
    var message = input.value.trim();
    
    if (!message || chatState.isLoading) return;
    
    // 清空输入框
    input.value = '';
    input.style.height = 'auto';
    
    // 添加用户消息
    addMessage('user', message);
    
    // 显示加载状态
    showLoading();
    
    try {
        var response = await fetch(API_BASE + '/api/partner/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: message,
                company_info: { partner_id: 'web_guest' }
            })
        });
        
        if (!response.ok) {
            throw new Error('请求失败');
        }
        
        var data = await response.json();
        
        // 更新剩余次数
        if (data.metadata && data.metadata.remaining_today) {
            chatState.remainingToday = data.metadata.remaining_today;
            updateRemainingDisplay();
        }
        
        // 添加AI回复
        addMessage('ai', data.response, data.metadata);
        
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
function addMessage(role, content, data) {
    var messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;
    
    var messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + (role === 'user' ? 'user' : 'ai');
    
    if (role === 'ai') {
        var evidenceBadge = '';
        if (data && data.metadata && data.metadata.policies_found > 0) {
            evidenceBadge = '<div class="policy-evidence">✅ 基于' + data.metadata.policies_found + '条真实政策数据回答</div>';
        }
        
        messageDiv.innerHTML = '<div class="message-avatar">🤖</div>' +
            '<div class="message-content">' +
                '<div class="message-text">' + formatContent(content) + '</div>' +
                evidenceBadge +
                '<div class="message-time">' + formatTime() + '</div>' +
            '</div>';
    } else {
        messageDiv.innerHTML = '<div class="message-content">' +
                '<div class="message-text">' + escapeHtml(content) + '</div>' +
                '<div class="message-time">' + formatTime() + '</div>' +
            '</div>' +
            '<div class="message-avatar">👤</div>';
    }
    
    messagesContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
    
    // 保存消息
    chatState.messages.push({ role: role, content: content, data: data });
}

// 更新剩余次数显示
function updateRemainingDisplay() {
    var remainingEl = document.getElementById('remainingCount');
    if (remainingEl) {
        remainingEl.textContent = '今日剩余 ' + chatState.remainingToday + ' 次查询';
    }
}

// 滚动到底部
function scrollToBottom() {
    var messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer) {
        setTimeout(function() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
    }
}

// 格式化内容（Markdown + 金额高亮）
function formatContent(text) {
    if (!text) return '';
    
    var formatted = escapeHtml(text);
    
    // 粗体
    formatted = formatted.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // 金额高亮（金色）
    formatted = formatted.replace(/(¥?\d+(?:\.\d+)?(?:万|亿|元|千))/g, '<span class="amount-highlight">$1</span>');
    
    // 换行处理
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

// 转义HTML
function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 格式化时间
function formatTime() {
    var now = new Date();
    return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

// 显示/隐藏加载状态
function showLoading() {
    chatState.isLoading = true;
    var loadingEl = document.getElementById('loadingIndicator');
    var sendBtn = document.getElementById('sendBtn');
    if (loadingEl) {
        loadingEl.classList.remove('hidden');
    }
    if (sendBtn) {
        sendBtn.disabled = true;
    }
}

function hideLoading() {
    chatState.isLoading = false;
    var loadingEl = document.getElementById('loadingIndicator');
    var sendBtn = document.getElementById('sendBtn');
    if (loadingEl) {
        loadingEl.classList.add('hidden');
    }
    if (sendBtn) {
        sendBtn.disabled = false;
    }
}

// 加载历史消息（简化版，只显示欢迎语）
function loadMessages() {
    var messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer || chatState.messages.length > 0) return;
    
    // 显示欢迎语
    var welcomeHTML = '<div class="message ai">' +
        '<div class="message-avatar">🤖</div>' +
        '<div class="message-content">' +
            '<div class="message-text">' +
                '👋 你好！我是政策通AI助手，帮你算算企业能拿多少补贴。<br><br>' +
                '告诉我你的企业情况，我马上给你匹配：<br><br>' +
                '💡 点击下方快速开始，或直接输入你的情况' +
            '</div>' +
            '<div class="suggestion-chips" style="margin-top:16px;">' +
                '<button class="suggestion-chip" onclick="askSuggestion(\'🏢 海珠区AI创业公司\')">🏢 海珠区AI创业公司</button>' +
                '<button class="suggestion-chip" onclick="askSuggestion(\'💻 天河区软件企业\')">💻 天河区软件企业</button>' +
                '<button class="suggestion-chip" onclick="askSuggestion(\'🔬 专精特新企业申报\')">🔬 专精特新企业申报</button>' +
                '<button class="suggestion-chip" onclick="askSuggestion(\'🏭 小微企业租金减免\')">🏭 小微企业租金减免</button>' +
                '<button class="suggestion-chip" onclick="askSuggestion(\'🧠 大模型产业扶持\')">🧠 大模型产业扶持</button>' +
                '<button class="suggestion-chip" onclick="askSuggestion(\'🏗️ 新认定高新技术企业\')">🏗️ 新认定高新技术企业</button>' +
            '</div>' +
            '<div class="message-time">' + formatTime() + '</div>' +
        '</div>' +
    '</div>';
    
    messagesContainer.innerHTML = welcomeHTML;
}

// 推荐问题点击
function askSuggestion(text) {
    var input = document.getElementById('chatInput');
    if (input) {
        input.value = text;
        sendMessage();
    }
}

// 移动端适配：触摸滚动
function initMobileScroll() {
    var messagesContainer = document.getElementById('chatMessages');
    if (!messagesContainer) return;
    
    // 防止页面整体滚动时影响对话区域
    messagesContainer.addEventListener('touchmove', function(e) {
        if (messagesContainer.scrollHeight - messagesContainer.scrollTop <= messagesContainer.clientHeight + 50) {
            e.stopPropagation();
        }
    }, { passive: true });
}

// 初始化移动端滚动
initMobileScroll();

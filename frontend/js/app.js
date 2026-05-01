/**
 * 政策通 PolicyPilot - 前端应用
 * 2024-2026 开源大叔
 */

// API配置
const API_BASE = window.location.origin;

// 应用状态
const state = {
    currentStep: 1,
    totalSteps: 3,
    formData: {
        name: '',
        district: '',
        industry: '',
        establishedYears: 1,
        revenueScale: '',
        employeeCount: 10,
        hasIP: false,
        isHighTech: false,
        isSpecialized: false,
        hasVC: false
    },
    matchedPolicies: [],
    currentPolicy: null,
    user: null,
    token: localStorage.getItem('policy_pilot_token'),
    selectedPolicyForMaterial: null,
    generatedMaterial: null
};

// ========== 用户认证 ==========

function checkAuthStatus() {
    if (state.token) {
        fetchUserInfo();
    }
}

async function fetchUserInfo() {
    try {
        const response = await fetch(`${API_BASE}/user/info`, {
            headers: {
                'Authorization': `Bearer ${state.token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            state.user = data.user;
            updateUserUI();
        } else {
            logout();
        }
    } catch (error) {
        console.error('获取用户信息失败:', error);
        logout();
    }
}

function updateUserUI() {
    const loginBtn = document.getElementById('login-btn');
    const userInfo = document.getElementById('user-info');
    const myResultsLink = document.getElementById('my-results-link');
    const userPhone = document.getElementById('user-phone');
    
    if (state.user) {
        loginBtn.classList.add('hidden');
        userInfo.classList.remove('hidden');
        myResultsLink.classList.remove('hidden');
        if (userPhone) {
            userPhone.textContent = state.user.phone_masked;
        }
    } else {
        loginBtn.classList.remove('hidden');
        userInfo.classList.add('hidden');
        myResultsLink.classList.add('hidden');
    }
}

function logout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem('policy_pilot_token');
    updateUserUI();
}

function showLoginModal() {
    document.getElementById('login-modal').classList.remove('hidden');
    document.getElementById('login-error').classList.add('hidden');
    
    // 绑定手机号输入事件
    const phoneInput = document.getElementById('login-phone');
    phoneInput.oninput = function() {
        const sendBtn = document.getElementById('send-code-btn');
        sendBtn.disabled = this.value.length !== 11;
    };
}

function closeLoginModal() {
    document.getElementById('login-modal').classList.add('hidden');
    document.getElementById('login-phone').value = '';
    document.getElementById('login-code').value = '';
    document.getElementById('login-error').classList.add('hidden');
}

function sendVerifyCode() {
    const phone = document.getElementById('login-phone').value;
    if (phone.length === 11) {
        // Mock: 直接提示验证码已发送
        const sendBtn = document.getElementById('send-code-btn');
        sendBtn.textContent = '已发送';
        sendBtn.disabled = true;
        alert('验证码已发送（测试模式：填123456即可）');
    }
}

async function doLogin() {
    const phone = document.getElementById('login-phone').value;
    const code = document.getElementById('login-code').value;
    const errorEl = document.getElementById('login-error');
    
    if (!phone || phone.length !== 11) {
        errorEl.textContent = '请输入正确的11位手机号';
        errorEl.classList.remove('hidden');
        return;
    }
    
    if (!code) {
        errorEl.textContent = '请输入验证码';
        errorEl.classList.remove('hidden');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ phone, verify_code: code })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            state.token = data.token;
            state.user = { id: data.user_id };
            localStorage.setItem('policy_pilot_token', data.token);
            closeLoginModal();
            updateUserUI();
            
            // 如果有待保存的诊断结果，自动保存
            if (state.matchedPolicies.length > 0) {
                saveDiagnosisResult();
            }
            
            alert('登录成功！');
        } else {
            errorEl.textContent = data.detail || '登录失败';
            errorEl.classList.remove('hidden');
        }
    } catch (error) {
        errorEl.textContent = '网络错误，请稍后重试';
        errorEl.classList.remove('hidden');
    }
}

// ========== API 函数 ==========

async function matchPolicies(companyData) {
    const response = await fetch(`${API_BASE}/match`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            company: {
                name: companyData.name,
                district: companyData.district,
                industry: companyData.industry,
                established_years: companyData.establishedYears,
                revenue_scale: companyData.revenueScale,
                employee_count: companyData.employeeCount,
                has_ip: companyData.hasIP,
                is_high_tech: companyData.isHighTech,
                is_specialized: companyData.isSpecialized,
                has_vc_investment: companyData.hasVC
            }
        })
    });
    
    if (!response.ok) {
        throw new Error('匹配服务出错');
    }
    
    return response.json();
}

async function getPolicy(policyId) {
    const response = await fetch(`${API_BASE}/policy/${policyId}`);
    
    if (!response.ok) {
        throw new Error('获取政策详情失败');
    }
    
    return response.json();
}

async function getAllPolicies() {
    const response = await fetch(`${API_BASE}/policies`);
    
    if (!response.ok) {
        throw new Error('获取政策列表失败');
    }
    
    return response.json();
}

// ========== 诊断结果保存 ==========

async function saveDiagnosisResult() {
    if (!state.token) return;
    
    try {
        await fetch(`${API_BASE}/user/result`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify({
                company: {
                    name: state.formData.name,
                    district: state.formData.district,
                    industry: state.formData.industry,
                    established_years: state.formData.establishedYears,
                    revenue_scale: state.formData.revenueScale,
                    employee_count: state.formData.employeeCount,
                    has_ip: state.formData.hasIP,
                    is_high_tech: state.formData.isHighTech,
                    is_specialized: state.formData.isSpecialized,
                    has_vc_investment: state.formData.hasVC
                },
                match_result: {
                    total_matches: state.matchedPolicies.length,
                    highly_recommended_count: state.matchedPolicies.filter(p => p.is_highly_recommended).length,
                    matched_policies: state.matchedPolicies
                }
            })
        });
    } catch (error) {
        console.error('保存诊断结果失败:', error);
    }
}

async function getUserResults() {
    const response = await fetch(`${API_BASE}/user/results`, {
        headers: {
            'Authorization': `Bearer ${state.token}`
        }
    });
    
    if (!response.ok) {
        throw new Error('获取历史记录失败');
    }
    
    const data = await response.json();
    return data.results;
}

// ========== 材料生成 ==========

async function generateMaterials(policyId) {
    const response = await fetch(`${API_BASE}/generate-materials`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            policy_id: policyId,
            company_name: state.formData.name,
            district: state.formData.district,
            industry: state.formData.industry,
            established_years: state.formData.establishedYears,
            employee_count: state.formData.employeeCount,
            revenue_scale: state.formData.revenueScale,
            has_ip: state.formData.hasIP,
            is_high_tech: state.formData.isHighTech,
            is_specialized: state.formData.isSpecialized,
            has_vc_investment: state.formData.hasVC
        })
    });
    
    if (!response.ok) {
        throw new Error('生成申报材料失败');
    }
    
    return response.json();
}

function showMaterialModal(policyId, policyName) {
    state.selectedPolicyForMaterial = { id: policyId, name: policyName };
    
    const modal = document.getElementById('material-modal');
    const body = document.getElementById('material-modal-body');
    
    body.innerHTML = `
        <div class="material-step">
            <div class="step-title">
                <span class="step-number">1</span>
                <span>确认企业信息</span>
            </div>
            <div class="form-group">
                <p class="form-hint">以下是您诊断时填写的企业信息，将用于生成申报材料：</p>
                <ul style="list-style: none; padding-left: 0;">
                    <li><strong>企业名称：</strong>${state.formData.name}</li>
                    <li><strong>所在区域：</strong>${state.formData.district}</li>
                    <li><strong>所属行业：</strong>${state.formData.industry}</li>
                    <li><strong>营收规模：</strong>${state.formData.revenueScale}</li>
                </ul>
            </div>
        </div>
        
        <div class="material-step">
            <div class="step-title">
                <span class="step-number">2</span>
                <span>选择要申报的政策</span>
            </div>
            <div class="policy-select-card selected">
                <input type="radio" name="policy" checked>
                <strong>${policyName}</strong>
                <p class="form-hint" style="margin-top: 4px;">将以此政策为基础生成申报材料</p>
            </div>
        </div>
        
        <div class="material-step">
            <div class="step-title">
                <span class="step-number">3</span>
                <span>生成并预览材料</span>
            </div>
            <p class="form-hint">点击下方按钮，系统将根据您的企业信息和政策要求，生成完整的申报材料包。</p>
            <button class="generate-btn" onclick="generateMaterialPreview()" id="generate-btn">
                <span>🚀</span>
                <span>生成申报材料</span>
            </button>
        </div>
    `;
    
    modal.classList.remove('hidden');
}

function closeMaterialModal() {
    document.getElementById('material-modal').classList.add('hidden');
    state.selectedPolicyForMaterial = null;
}

async function generateMaterialPreview() {
    const btn = document.getElementById('generate-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:20px;height:20px;border-width:2px;margin-right:8px;"></span> 生成中...';
    
    try {
        const result = await generateMaterials(state.selectedPolicyForMaterial.id);
        state.generatedMaterial = result;
        
        // 显示预览
        showPreviewModal(result.full_content);
        closeMaterialModal();
    } catch (error) {
        alert('生成失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🚀</span><span>生成申报材料</span>';
    }
}

function showPreviewModal(htmlContent) {
    const modal = document.getElementById('preview-modal');
    const frame = document.getElementById('preview-frame');
    
    // 将HTML写入iframe
    frame.srcdoc = htmlContent;
    modal.classList.remove('hidden');
}

function closePreviewModal() {
    document.getElementById('preview-modal').classList.add('hidden');
}

function downloadMaterial() {
    if (!state.generatedMaterial) return;
    
    // 创建下载的HTML文件
    const content = state.generatedMaterial.full_content;
    const blob = new Blob([content], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${state.formData.name}_${state.selectedPolicyForMaterial.name}_申报材料.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ========== 表单处理 ==========

function initForm() {
    // 绑定表单事件
    const form = document.getElementById('diagnosis-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // 区选择
    document.querySelectorAll('.district-option').forEach(btn => {
        btn.addEventListener('click', () => selectDistrict(btn.dataset.value));
    });
    
    // 营收规模选择
    document.querySelectorAll('.revenue-option').forEach(btn => {
        btn.addEventListener('click', () => selectRevenue(btn.dataset.value));
    });
    
    // 行业选择
    const industrySelect = document.getElementById('industry');
    if (industrySelect) {
        populateIndustryOptions(industrySelect);
    }
    
    // 资质复选框
    document.querySelectorAll('.qualification-item').forEach(item => {
        item.addEventListener('click', () => toggleQualification(item));
    });
    
    // 下一步按钮
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', goToNextStep);
    }
    
    // 上一步按钮
    const prevBtn = document.getElementById('prev-btn');
    if (prevBtn) {
        prevBtn.addEventListener('click', goToPrevStep);
    }
    
    // 更新步骤显示
    updateStepIndicator();
    
    // 检查登录状态
    checkAuthStatus();
}

function selectDistrict(value) {
    state.formData.district = value;
    document.querySelectorAll('.district-option').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.value === value);
    });
    updateNextButtonState();
}

function selectRevenue(value) {
    state.formData.revenueScale = value;
    document.querySelectorAll('.revenue-option').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.value === value);
    });
    updateNextButtonState();
}

function populateIndustryOptions(select) {
    const industries = [
        '人工智能/大模型',
        '软件开发/互联网服务',
        '信息技术服务',
        '电子信息',
        '智能制造/工业自动化',
        '电子商务/零售',
        '生物医药/医疗健康',
        '新能源/新材料',
        '金融服务',
        '教育培训',
        '文化创意',
        '其他行业'
    ];
    
    industries.forEach(ind => {
        const option = document.createElement('option');
        option.value = ind;
        option.textContent = ind;
        select.appendChild(option);
    });
}

function toggleQualification(item) {
    const key = item.dataset.key;
    const isSelected = item.classList.toggle('selected');
    state.formData[key] = isSelected;
}

function goToNextStep() {
    if (!validateCurrentStep()) return;
    
    if (state.currentStep < state.totalSteps) {
        // 隐藏当前步骤
        document.querySelectorAll('.form-group').forEach(g => {
            g.classList.remove('active');
        });
        
        // 显示下一步
        state.currentStep++;
        const nextGroup = document.getElementById(`step-${state.currentStep}`);
        if (nextGroup) {
            nextGroup.classList.add('active');
        }
        
        updateStepIndicator();
        updateButtonText();
    } else {
        // 最后一步，提交表单
        handleFormSubmit();
    }
}

function goToPrevStep() {
    if (state.currentStep > 1) {
        document.querySelectorAll('.form-group').forEach(g => {
            g.classList.remove('active');
        });
        
        state.currentStep--;
        const prevGroup = document.getElementById(`step-${state.currentStep}`);
        if (prevGroup) {
            prevGroup.classList.add('active');
        }
        
        updateStepIndicator();
        updateButtonText();
    }
}

function updateStepIndicator() {
    document.querySelectorAll('.step-dot').forEach((dot, index) => {
        dot.classList.remove('active', 'completed');
        if (index + 1 === state.currentStep) {
            dot.classList.add('active');
        } else if (index + 1 < state.currentStep) {
            dot.classList.add('completed');
        }
    });
}

function updateButtonText() {
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        if (state.currentStep === state.totalSteps) {
            nextBtn.innerHTML = '<span>开始诊断</span><span>→</span>';
        } else {
            nextBtn.innerHTML = '<span>下一步</span><span>→</span>';
        }
    }
}

function updateNextButtonState() {
    const nextBtn = document.getElementById('next-btn');
    if (!nextBtn) return;
    
    let canProceed = false;
    
    if (state.currentStep === 1) {
        canProceed = state.formData.district !== '' && state.formData.name.trim() !== '';
    } else if (state.currentStep === 2) {
        canProceed = state.formData.industry !== '' && state.formData.revenueScale !== '';
    } else {
        canProceed = true;
    }
    
    nextBtn.disabled = !canProceed;
}

function validateCurrentStep() {
    if (state.currentStep === 1) {
        if (!state.formData.district) {
            alert('请选择企业所在区域');
            return false;
        }
        if (!state.formData.name.trim()) {
            alert('请输入企业名称');
            return false;
        }
    } else if (state.currentStep === 2) {
        if (!state.formData.industry) {
            alert('请选择所属行业');
            return false;
        }
        if (!state.formData.revenueScale) {
            alert('请选择营收规模');
            return false;
        }
    }
    return true;
}

async function handleFormSubmit(e) {
    if (e) e.preventDefault();
    
    // 收集表单数据
    state.formData.establishedYears = parseInt(document.getElementById('established-years')?.value || 1);
    state.formData.employeeCount = parseInt(document.getElementById('employee-count')?.value || 10);
    state.formData.industry = document.getElementById('industry')?.value || '';
    
    // 显示加载状态
    showLoading();
    
    try {
        const result = await matchPolicies(state.formData);
        state.matchedPolicies = result.matched_policies;
        showResults(result);
        
        // 如果已登录，自动保存结果
        if (state.token) {
            saveDiagnosisResult();
        }
    } catch (error) {
        console.error('匹配失败:', error);
        showError('匹配服务暂时不可用，请稍后重试。');
    }
}

// ========== 结果展示 ==========

function showLoading() {
    document.getElementById('form-section')?.classList.add('hidden');
    document.getElementById('loading-section')?.classList.remove('hidden');
    document.getElementById('result-section')?.classList.add('hidden');
}

function showResults(result) {
    document.getElementById('loading-section')?.classList.add('hidden');
    document.getElementById('result-section')?.classList.remove('hidden');
    
    // 更新结果头部
    const resultTitle = document.getElementById('result-title');
    const resultSubtitle = document.getElementById('result-subtitle');
    const totalMatches = document.getElementById('total-matches');
    const highlyRecommended = document.getElementById('highly-recommended');
    
    if (resultTitle) {
        resultTitle.textContent = `${result.company_name}，为您匹配到 ${result.total_matches} 条政策`;
    }
    if (resultSubtitle) {
        resultSubtitle.textContent = '以下政策可能适合您的企业申报';
    }
    if (totalMatches) {
        totalMatches.textContent = result.total_matches;
    }
    if (highlyRecommended) {
        highlyRecommended.textContent = result.highly_recommended_count;
    }
    
    // 渲染政策列表
    renderPolicyList(result.matched_policies);
}

function renderPolicyList(policies) {
    const listContainer = document.getElementById('policy-list');
    if (!listContainer) return;
    
    if (policies.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <div class="empty-title">暂未匹配到适合的政策</div>
                <div class="empty-desc">请检查输入信息是否准确，或尝试调整筛选条件</div>
            </div>
        `;
        return;
    }
    
    listContainer.innerHTML = policies.map(policy => {
        const amount = policy.policy.max_amount > 0 
            ? `最高 ${policy.policy.max_amount} 万元` 
            : '按条件奖励';
        
        return `
            <div class="policy-card ${policy.is_highly_recommended ? 'recommended' : ''}">
                <div class="policy-card-header" onclick="viewPolicyDetail('${policy.policy.id}')">
                    <div class="policy-name">${policy.policy.name}</div>
                    <div class="policy-badge ${policy.is_highly_recommended ? 'recommend' : 'match'}">
                        匹配度 ${policy.match_score}%
                    </div>
                </div>
                <div class="policy-amount" onclick="viewPolicyDetail('${policy.policy.id}')">${amount}</div>
                <div class="policy-meta" onclick="viewPolicyDetail('${policy.policy.id}')">
                    <div class="policy-meta-item">
                        <span class="icon">📍</span>
                        ${policy.policy.district}
                    </div>
                    <div class="policy-meta-item">
                        <span class="icon">🏛️</span>
                        ${policy.policy.department}
                    </div>
                    <div class="policy-meta-item">
                        <span class="icon">🏷️</span>
                        ${policy.policy.category}
                    </div>
                </div>
                <div class="policy-tags" onclick="viewPolicyDetail('${policy.policy.id}')">
                    ${policy.match_reasons.slice(0, 3).map(r => `<span class="policy-tag">${r}</span>`).join('')}
                </div>
                <div class="policy-card-footer">
                    <button class="btn btn-secondary btn-sm" onclick="viewPolicyDetail('${policy.policy.id}')">
                        查看详情
                    </button>
                    <button class="generate-material-btn" onclick="showMaterialModal('${policy.policy.id}', '${policy.policy.name}')">
                        <span>📄</span>
                        <span>生成申报材料</span>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function showError(message) {
    document.getElementById('loading-section')?.classList.add('hidden');
    document.getElementById('form-section')?.classList.remove('hidden');
    alert(message);
}

// ========== 政策详情 ==========

async function viewPolicyDetail(policyId) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.classList.remove('hidden');
    }
    
    try {
        const policy = await getPolicy(policyId);
        state.currentPolicy = policy;
        showPolicyDetailPage(policy);
    } catch (error) {
        console.error('获取政策详情失败:', error);
        alert('获取政策详情失败，请稍后重试');
    } finally {
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
        }
    }
}

function showPolicyDetailPage(policy) {
    // 跳转到政策详情页
    window.location.href = `/policy.html?id=${policy.id}`;
}

function goBack() {
    window.history.back();
}

// ========== 诊断按钮 ==========

function startDiagnosis() {
    document.getElementById('hero-section')?.classList.add('hidden');
    document.getElementById('form-section')?.classList.remove('hidden');
    document.getElementById('step-1')?.classList.add('active');
    updateButtonText();
}

function goHome() {
    window.location.href = '/';
}

function resetAndStartOver() {
    // 重置状态
    state.currentStep = 1;
    state.formData = {
        name: '',
        district: '',
        industry: '',
        establishedYears: 1,
        revenueScale: '',
        employeeCount: 10,
        hasIP: false,
        isHighTech: false,
        isSpecialized: false,
        hasVC: false
    };
    state.matchedPolicies = [];
    
    // 重置UI
    document.getElementById('result-section')?.classList.add('hidden');
    document.getElementById('form-section')?.classList.remove('hidden');
    document.querySelectorAll('.form-group').forEach(g => g.classList.remove('active'));
    document.getElementById('step-1')?.classList.add('active');
    
    // 重置选择状态
    document.querySelectorAll('.checkbox-item, .district-option, .revenue-option').forEach(el => {
        el.classList.remove('selected');
    });
    
    // 重置表单
    document.getElementById('company-name') && (document.getElementById('company-name').value = '');
    document.getElementById('industry') && (document.getElementById('industry').value = '');
    document.getElementById('established-years') && (document.getElementById('established-years').value = 1);
    document.getElementById('employee-count') && (document.getElementById('employee-count').value = 10);
    
    updateStepIndicator();
    updateButtonText();
}

// ========== 初始化 ==========

document.addEventListener('DOMContentLoaded', () => {
    // 检查是否为结果页面
    const urlParams = new URLSearchParams(window.location.search);
    const policyId = urlParams.get('policy');
    
    if (policyId) {
        viewPolicyDetail(policyId);
    } else {
        initForm();
    }
});

// 导出给全局使用
window.startDiagnosis = startDiagnosis;
window.viewPolicyDetail = viewPolicyDetail;
window.goBack = goBack;
window.resetAndStartOver = resetAndStartOver;
window.goHome = goHome;

// 登录相关
window.showLoginModal = showLoginModal;
window.closeLoginModal = closeLoginModal;
window.doLogin = doLogin;
window.logout = logout;
window.sendVerifyCode = sendVerifyCode;

// 材料生成相关
window.showMaterialModal = showMaterialModal;
window.closeMaterialModal = closeMaterialModal;
window.generateMaterialPreview = generateMaterialPreview;
window.showPreviewModal = showPreviewModal;
window.closePreviewModal = closePreviewModal;
window.downloadMaterial = downloadMaterial;

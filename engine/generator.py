"""
申报材料自动生成模块
根据政策模板和企业信息生成完整的申报材料包
"""
import os
from typing import Dict, Any, List
from datetime import datetime


class MaterialGenerator:
    """申报材料生成器"""
    
    def __init__(self, matcher=None):
        """初始化生成器"""
        self.matcher = matcher
    
    def generate_materials(
        self,
        company_info: Dict[str, Any],
        policy_id: str
    ) -> Dict[str, Any]:
        """
        生成申报材料
        
        Args:
            company_info: 企业信息字典
            policy_id: 政策ID
        
        Returns:
            包含申报材料的字典
        """
        # 获取政策信息
        policy = None
        if self.matcher:
            policy = self.matcher.get_policy_by_id(policy_id)
        
        if not policy:
            return {
                'success': False,
                'error': '未找到指定政策'
            }
        
        # 生成各部分材料
        application_letter = self._generate_application_letter(company_info, policy)
        project_overview = self._generate_project_overview(company_info, policy)
        conditions_statement = self._generate_conditions_statement(company_info, policy)
        expected_results = self._generate_expected_results(company_info, policy)
        attachments_list = self._generate_attachments_list(policy)
        submission_guide = self._generate_submission_guide(policy)
        
        return {
            'success': True,
            'company_name': company_info.get('name', ''),
            'policy_name': policy.name,
            'generated_at': datetime.now().strftime('%Y年%m月%d日 %H:%M'),
            'application_letter': application_letter,
            'project_overview': project_overview,
            'conditions_statement': conditions_statement,
            'expected_results': expected_results,
            'attachments_list': attachments_list,
            'submission_guide': submission_guide,
            'full_content': self._combine_full_content(
                application_letter, project_overview, 
                conditions_statement, expected_results
            )
        }
    
    def _generate_application_letter(
        self,
        company_info: Dict[str, Any],
        policy
    ) -> str:
        """生成申请书封面/申请函"""
        company_name = company_info.get('name', '【企业名称】')
        policy_name = policy.name
        district = company_info.get('district', policy.district)
        current_date = datetime.now().strftime('%Y年%m月%d日')
        
        return f"""
<h2>📄 项目申报书</h2>

<div class="application-header">
<p><strong>项目名称：</strong>{policy_name}</p>
<p><strong>申报单位：</strong>{company_name}</p>
<p><strong>所属区域：</strong>{district}</p>
<p><strong>申报日期：</strong>{current_date}</p>
</div>

<h3>一、申请函</h3>

<p>尊敬的{policy.department}领导：</p>

<p>我单位<b>{company_name}</b>，现就<b>{policy_name}</b>政策补贴项目提出申请。</p>

<p>经自查，我单位符合该政策的申报条件，现提交以下申报材料，请审核。</p>

<p>我单位承诺所提交的所有材料真实、合法、有效，如有弄虚作假，愿承担相应法律责任。</p>

<p style="text-align: right;">
{company_name}<br>
{current_date}
</p>
"""
    
    def _generate_project_overview(
        self,
        company_info: Dict[str, Any],
        policy
    ) -> str:
        """生成企业/项目概况"""
        company_name = company_info.get('name', '【企业名称】')
        industry = company_info.get('industry', '信息技术')
        established_years = company_info.get('established_years', 3)
        employees = company_info.get('employee_count', 50)
        revenue = company_info.get('revenue_scale', '500-2000万')
        
        # 根据资质生成描述
        qualifications = []
        if company_info.get('is_high_tech'):
            qualifications.append("✅ 高新技术企业")
        if company_info.get('is_specialized'):
            qualifications.append("✅ 专精特新企业")
        if company_info.get('has_ip'):
            qualifications.append("✅ 拥有自主知识产权")
        if company_info.get('has_vc_investment'):
            qualifications.append("✅ 获得风险投资机构投资")
        
        qual_desc = "<br>".join(qualifications) if qualifications else "暂无"
        
        return f"""
<h3>二、企业基本情况</h3>

<table class="info-table">
<tr><th>企业名称</th><td>{company_name}</td></tr>
<tr><th>所属行业</th><td>{industry}</td></tr>
<tr><th>成立年限</th><td>{established_years}年</td></tr>
<tr><th>员工数量</th><td>{employees}人</td></tr>
<tr><th>营收规模</th><td>{revenue}</td></tr>
<tr><th>企业资质</th><td>{qual_desc}</td></tr>
</table>

<h3>三、项目概况</h3>

<p><b>项目背景：</b></p>
<p>{company_name}成立于{established_years}年前，是一家专注于{industry}领域的企业。公司拥有专业的研发团队和完善的管理体系，近年来在技术创新和业务发展方面取得了显著成绩。</p>

<p><b>项目内容：</b></p>
<p>本次申报项目为<b>{policy.name}</b>，旨在通过该政策的支持，进一步提升企业创新能力，加快业务发展，为{company_info.get('district', '本地')}经济发展做出更大贡献。</p>

<p><b>项目目标：</b></p>
<ul>
<li>提升企业技术创新能力</li>
<li>扩大市场份额和影响力</li>
<li>带动就业，促进地方经济发展</li>
<li>推动行业技术进步</li>
</ul>
"""
    
    def _generate_conditions_statement(
        self,
        company_info: Dict[str, Any],
        policy
    ) -> str:
        """生成符合条件说明"""
        company_name = company_info.get('name', '【企业名称】')
        
        # 收集匹配原因
        match_reasons = []
        
        # 区域匹配
        if company_info.get('district') in policy.district:
            match_reasons.append(f"✅ 企业位于{company_info.get('district')}，符合政策区域要求")
        
        # 行业匹配
        company_industry = company_info.get('industry', '')
        for ind in policy.conditions.industry:
            if '不限' in ind or ind in company_industry:
                match_reasons.append(f"✅ 企业所属行业({company_industry})符合政策要求")
                break
        
        # 资质匹配
        if company_info.get('is_high_tech') and any('高新技术' in r for r in policy.conditions.other):
            match_reasons.append("✅ 企业具备高新技术企业资质")
        
        if company_info.get('is_specialized') and '专精特新' in policy.category:
            match_reasons.append("✅ 企业具备专精特新资质")
        
        if company_info.get('has_ip') and any('专利' in r for r in policy.conditions.other):
            match_reasons.append("✅ 企业拥有自主知识产权")
        
        # 营收规模匹配
        revenue = company_info.get('revenue_scale', '')
        if revenue:
            match_reasons.append(f"✅ 企业营收规模({revenue})符合政策要求")
        
        # 基本要求匹配
        for req in policy.requirements:
            match_reasons.append(f"✅ {req}")
        
        reasons_html = "<br>".join(match_reasons) if match_reasons else "<p>企业符合政策基本申报条件</p>"
        
        return f"""
<h3>四、符合政策条件说明</h3>

<p>经对照<b>{policy.name}</b>的申报条件，{company_name}符合以下条件：</p>

<div class="conditions-box">
{reasons_html}
</div>

<p><b>政策要求摘要：</b></p>
<ul>
{''.join(f'<li>{m}</li>' for m in policy.materials[:5])}
</ul>
"""
    
    def _generate_expected_results(
        self,
        company_info: Dict[str, Any],
        policy
    ) -> str:
        """生成预期成果"""
        company_name = company_info.get('name', '【企业名称】')
        subsidy_desc = policy.subsidy_amount or policy.subsidy_ratio
        
        return f"""
<h3>五、预期成果</h3>

<p><b>预期经济效益：</b></p>
<ul>
<li>获得政策补贴资金支持，预计金额：{subsidy_desc}</li>
<li>提升企业资金周转效率</li>
<li>降低企业运营成本</li>
</ul>

<p><b>预期社会效益：</b></p>
<ul>
<li>新增就业岗位3-5个</li>
<li>带动上下游产业发展</li>
<li>推动地区技术创新</li>
</ul>

<p><b>预期创新成果：</b></p>
<ul>
<li>申请相关知识产权1-2项</li>
<li>形成可复制推广的技术方案</li>
<li>培养专业技术人才</li>
</ul>

<p><b>项目实施计划：</b></p>
<table class="timeline-table">
<tr><th>阶段</th><th>时间</th><th>主要工作</th></tr>
<tr><td>准备阶段</td><td>第1-2月</td><td>材料准备、申报提交</td></tr>
<tr><td>审核阶段</td><td>第3-4月</td><td>配合审核、补充材料</td></tr>
<tr><td>实施阶段</td><td>第5-12月</td><td>项目执行、进度跟踪</td></tr>
<tr><td>验收阶段</td><td>第13-15月</td><td>项目验收、成果总结</td></tr>
</table>
"""
    
    def _generate_attachments_list(self, policy) -> str:
        """生成附件清单"""
        materials = policy.materials or []
        
        if not materials:
            materials = [
                "企业营业执照复印件",
                "法人身份证复印件",
                "上一年度财务报表",
                "相关资质证书复印件",
                "项目申报书"
            ]
        
        attachments_html = ""
        for i, material in enumerate(materials, 1):
            # 判断是否已有（mock：前两项已有）
            has_it = i <= 2
            status = "✅ 已准备" if has_it else "⏳ 需补充"
            attachments_html += f"""
<tr>
<td>{i}</td>
<td>{material}</td>
<td class="{('status-done' if has_it else 'status-pending')}">{status}</td>
</tr>
"""
        
        return f"""
<h3>六、附件材料清单</h3>

<table class="attachments-table">
<tr>
<th>序号</th>
<th>材料名称</th>
<th>状态</th>
</tr>
{attachments_html}
</table>

<div class="attachments-note">
<p><strong>📝 注意事项：</strong></p>
<ul>
<li>所有复印件需加盖企业公章</li>
<li>财务报表需经审计或加盖财务章</li>
<li>材料按上述顺序整理，制作目录清单</li>
<li>电子版材料需清晰可读</li>
</ul>
</div>
"""
    
    def _generate_submission_guide(self, policy) -> str:
        """生成提交路径说明"""
        deadline = policy.deadline or '请关注官方通知'
        department = policy.department or '主管部门'
        link = policy.link or '请咨询相关部门获取申报网址'
        
        return f"""
<h3>七、申报提交指南</h3>

<div class="submission-box">
<p><strong>📍 申报方式：</strong>线上申报 + 线下材料提交</p>

<p><strong>🏛️ 受理部门：</strong>{department}</p>

<p><strong>⏰ 申报截止时间：</strong>{deadline}</p>

<p><strong>🔗 线上申报入口：</strong></p>
<p><a href="{link}" target="_blank">{link}</a></p>

<p><strong>📍 线下材料提交地址：</strong></p>
<p>请前往{department}政务服务窗口提交纸质材料</p>

<p><strong>👤 联系人：</strong>请联系{department}获取</p>
<p><strong>📞 咨询电话：</strong>请联系{department}获取</p>
</div>

<div class="final-note">
<p><strong>💡 温馨提示：</strong></p>
<ul>
<li>请在截止日期前完成申报，逾期不予受理</li>
<li>提交材料前请仔细核对，确保完整无误</li>
<li>申报过程中如有疑问，请及时与受理部门沟通</li>
<li>保持联系方式畅通，以便接收审核通知</li>
</ul>
</div>
"""
    
    def _combine_full_content(
        self,
        application_letter: str,
        project_overview: str,
        conditions_statement: str,
        expected_results: str
    ) -> str:
        """组合完整申报书内容"""
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>项目申报书</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", sans-serif; line-height: 1.8; color: #374151; max-width: 800px; margin: 0 auto; padding: 20px; }}
h2 {{ color: #1F2937; text-align: center; border-bottom: 2px solid #2563EB; padding-bottom: 10px; }}
h3 {{ color: #2563EB; margin-top: 24px; }}
.application-header {{ background: #F3F4F6; padding: 16px; border-radius: 8px; margin: 16px 0; }}
.application-header p {{ margin: 4px 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th, td {{ border: 1px solid #E5E7EB; padding: 10px; text-align: left; }}
th {{ background: #F9FAFB; font-weight: 600; width: 120px; }}
.info-table th {{ width: 100px; }}
.timeline-table th, .timeline-table td {{ text-align: center; }}
.timeline-table th:last-child, .timeline-table td:last-child {{ text-align: left; }}
.conditions-box {{ background: #ECFDF5; padding: 16px; border-radius: 8px; border-left: 4px solid #10B981; }}
.attachments-table {{ margin: 16px 0; }}
.attachments-table th {{ background: #EFF6FF; }}
.status-done {{ color: #10B981; font-weight: 600; }}
.status-pending {{ color: #F59E0B; font-weight: 600; }}
.attachments-note {{ background: #FEF3C7; padding: 16px; border-radius: 8px; margin-top: 16px; }}
.submission-box {{ background: #EEF2FF; padding: 20px; border-radius: 8px; border-left: 4px solid #6366F1; }}
.submission-box p {{ margin: 8px 0; }}
.final-note {{ background: #F0FDF4; padding: 16px; border-radius: 8px; margin-top: 16px; }}
ul {{ padding-left: 24px; }}
li {{ margin: 4px 0; }}
a {{ color: #2563EB; }}
</style>
</head>
<body>
{application_letter}
{project_overview}
{conditions_statement}
{expected_results}
<div style="text-align: center; margin-top: 40px; color: #6B7280; font-size: 14px;">
<p>—— 本申报书由政策通·PolicyPilot 自动生成 ——</p>
</div>
</body>
</html>
"""

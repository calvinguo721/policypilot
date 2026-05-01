# 政策通 PolicyPilot

**中小企业政策服务开源平台**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-green)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)](https://fastapi.tiangolo.com/)

---

## 项目定位

政策通（PolicyPilot）是一款面向中小企业的政策服务工具，旨在帮助企业快速找到适合自身情况的政府扶持政策，并生成规范的申报材料。

**我们是谁：** 一个开源技术团队，专注于用技术手段降低中小企业获取政策信息的门槛。

**我们的立场：** 坚持数据合规，不爬取任何非公开信息，所有政策数据均来源于官方公开渠道。

---

## 为什么开源？

### 透明 = 可控

政策通选择开源模式，基于以下核心考量：

1. **代码可审计**  
   政府主管部门可随时审查源代码，确认系统运行逻辑符合法规要求，不存在数据滥用风险。

2. **数据可追溯**  
   所有政策数据均标注来源，系统不存储、不分析、不泄露任何企业敏感信息。

3. **部署可自主**  
   各级政府部门、产业园区可自行部署完整系统，实现政策服务的本地化运营，数据不出内网。

4. **技术可信赖**  
   采用成熟开源技术栈（FastAPI、SQLite），无商业锁定，方便集成现有政务系统。

---

## 核心功能

### 1. 企业诊断与政策匹配

企业用户输入基本信息（所在区域、行业、规模等），系统自动匹配适用的政策项目，按匹配度排序推荐。

- 多维度条件匹配：区域、行业、营收规模、企业资质
- 智能评分机制：100分制综合评分
- 重点推荐标识：高匹配度政策优先展示

### 2. 申报材料生成

根据政策要求和用户企业信息，自动生成规范化的申报材料包，包括：

- 申请函
- 项目情况概述
- 申报条件自查声明
- 预期成果说明
- 材料清单与提交指南

### 3. 企业信息管理

- 用户注册与登录
- 诊断结果历史记录
- 诊断报告导出

---

## 技术架构

```
政策通/
├── engine/                 # FastAPI 后端服务
│   ├── main.py            # 服务入口
│   ├── matcher.py         # 政策匹配引擎
│   ├── generator.py       # 申报材料生成器
│   ├── models.py          # 数据模型定义
│   ├── database.py        # 数据库操作
│   └── auth.py            # 用户认证
├── frontend/              # 前端页面（原生 JS）
│   ├── index.html         # 首页/企业诊断
│   ├── policy.html        # 政策详情页
│   ├── my-results.html    # 我的诊断结果
│   ├── css/style.css
│   └── js/app.js
└── data/                  # 数据目录
    ├── policies.json      # 政策数据库（JSON格式）
    └── policy_pilot.db    # SQLite 用户数据库
```

### 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 后端框架 | FastAPI 0.100+ | 高性能 Python Web 框架 |
| 数据库 | SQLite | 轻量级本地数据库，开箱即用 |
| 前端 | HTML5 + CSS3 + Vanilla JS | 无框架依赖，部署简单 |
| API | RESTful JSON | 标准接口，便于集成 |

### 系统要求

- Python 3.9 或更高版本
- 无需 Node.js（前端为原生 JS）
- 建议 2GB 可用内存

---

## 快速部署

### 方式一：一键启动

```bash
# 进入 engine 目录
cd policy-pilot/engine

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

服务启动后，访问 `http://localhost:8000` 即可使用。

### 方式二：使用 uvicorn

```bash
cd policy-pilot/engine
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式三：PM2 生产部署

```bash
# 安装 PM2
npm install -g pm2

# 启动服务
pm2 start "python main.py" --name policy-pilot

# 查看状态
pm2 status

# 查看日志
pm2 logs policy-pilot

# 开机自启
pm2 save
pm2 startup
```

### 方式四：Docker 部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY engine/ /app/engine/
COPY frontend/ /app/frontend/
COPY data/ /app/data/
RUN pip install --no-cache-dir -r engine/requirements.txt
EXPOSE 8000
CMD ["python", "engine/main.py"]
```

---

## 数据合规声明

> **郑重承诺：本项目不爬取任何非公开数据。**

### 数据来源

政策通所使用的数据**全部**来源于以下公开渠道：

1. **各级政府官方网站**  
   - 广州市人民政府（www.gz.gov.cn）
   - 各区级政府网站
   - 政府信息公开平台

2. **政府授权数据接口**（如有）  
   仅在获得明确授权后接入，使用受控 API 获取公开政策信息。

3. **政策原文公开页面**  
   系统仅收录已公开发布的政策原文链接，供用户跳转查阅原文。

### 数据处理原则

| 原则 | 说明 |
|------|------|
| 不采集 | 不使用爬虫技术抓取任何网站数据 |
| 不存储 | 不存储企业提交的敏感信息（仅保留诊断结果） |
| 不分析 | 不对企业数据进行商业分析或画像 |
| 不共享 | 不向任何第三方提供数据访问接口 |

### 企业数据处理

- 企业用户提交的信息仅用于当次政策匹配计算
- 诊断结果由用户自主选择是否保存
- 系统管理员无法查看具体企业的填报内容

---

## 开源协议

本项目基于 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源。

### 您可以

- 自由使用：任何个人或组织均可部署使用本系统
- 自由修改：根据需要修改源代码
- 自由分发：分发本项目的完整代码
- 自由商用：在符合 AGPL 协议的前提下用于商业目的

### 您必须

- 保持开源：如果修改并分发本项目，必须开源修改后的代码
- 注明来源：在分发时保留版权声明和本协议
- 公开修改：如果在服务器上部署并提供服务，必须向用户提供完整源代码

详细协议内容请参阅 [LICENSE](LICENSE) 文件。

---

## 贡献指南

我们欢迎社区贡献！

### 如何贡献

1. **提交 Issue**  
   发现 Bug 或有新功能建议？请先搜索现有 Issue，避免重复提交。

2. **Fork & Pull Request**  
   - Fork 本仓库
   - 创建功能分支 (`git checkout -b feature/AmazingFeature`)
   - 提交更改 (`git commit -m 'Add some AmazingFeature'`)
   - 推送到分支 (`git push origin feature/AmazingFeature`)
   - 创建 Pull Request

3. **代码规范**  
   - Python 代码遵循 PEP 8 规范
   - 提交信息使用中文，清晰描述改动内容
   - 新功能请附带测试用例

### 贡献方向

- 📋 **政策数据**：补充和完善政策数据库
- 🔧 **功能开发**：政策匹配算法优化、申报材料模板扩充
- 🎨 **界面改进**：用户体验优化、前端适配
- 📝 **文档完善**：使用文档、部署指南
- 🐛 **Bug 修复**：问题定位与修复

---

## 免责声明

1. 本系统提供的政策匹配结果仅供参考，不构成申报承诺
2. 政策信息可能存在时效性延迟，请以政策发布部门的最新公告为准
3. 最终申报资格由政策主管机关审核确定
4. 本系统不对因使用本工具导致的申报失败承担任何责任

---

## 联系方式

- **GitHub Issues**: https://github.com/calvinguo721/policypilot/issues
- **邮箱**: policy-pilot@example.com（示例地址）

---

**政策通 —— 让每一个中小企业都能便捷地获取政策支持。**

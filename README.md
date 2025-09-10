# AI Movie Generator 🎬🤖

> 通过AI技术将文字转换为精彩视频的智能平台

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://mysql.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

AI Movie Generator 是一个基于前沿AI技术的智能视频生成平台，能够自动将简单的文字描述转换为完整的视频内容。适合内容创作者、营销人员以及任何需要快速创建吸引人视频内容的用户。

## ✨ 核心功能

### 🎯 智能视频生成
- **文本转视频**: 从文字描述生成完整视频
- **角色图片集成**: 支持自定义角色图片融入视频
- **智能文案生成**: 自动创建吸引人的标题和内容
- **分镜脚本生成**: 将文案智能拆解为多个视频场景
- **AI配音合成**: 为每个场景生成专业配音
- **视频质量检查**: 自动分析并优化视频质量

### 🔧 技术特性
- **多模态AI集成**: 集成 Qwen-Plus、Wanx Video、CosyVoice、Qwen-VL 等模型
- **工作流引擎**: 基于 LangGraph 的模块化处理流程
- **Web应用界面**: 响应式设计，支持桌面端和移动端
- **用户认证系统**: 基于 Flask-Login 的会话管理
- **数据持久化**: MySQL 数据库存储用户数据和视频信息
- **云存储集成**: 支持阿里云 OSS 视频存储和管理
- **CLI工具**: 命令行界面支持批量处理

### 🎨 用户体验
- **直观操作界面**: 简洁易用的Web界面
- **实时进度跟踪**: 视频生成过程可视化
- **个人视频管理**: 用户个人中心和视频历史
- **移动端适配**: 完整的移动设备支持
- **无障碍设计**: 支持屏幕阅读器和键盘导航

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **数据库**: MySQL 8.0+
- **ffmpeg**: 视频处理工具
- **DashScope API**: 阿里云百炼AI服务

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/ai_movie.git
cd ai_movie

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装 ffmpeg
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows
# 下载并安装 https://ffmpeg.org/download.html
```

### 配置设置

```bash
# 1. 复制环境配置模板
cp .env.example .env

# 2. 编辑配置文件
nano .env
```

必需的环境变量：

```bash
# AI 服务配置
DASHSCOPE_API_KEY=your_dashscope_api_key

# 数据库配置
USE_DATABASE=True
SQLALCHEMY_DATABASE_URI=mysql+pymysql://username:password@host:3306/ai_movie

# Flask 配置
SECRET_KEY=your_secret_key_here
FLASK_ENV=production

# OSS 存储配置（可选）
OSS_ENDPOINT=your_oss_endpoint
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
```

### 使用方法

#### Web 应用界面（推荐）

```bash
# 启动 Web 应用
python -m ai_movie.web

# 或者使用命令别名
ai-movie-web

# 打开浏览器访问 http://localhost:5002
```

**Web 界面功能**：
- 👤 用户注册和登录
- 🎥 文本输入生成视频
- 🖼️ 上传角色图片生成个性化视频
- 📋 个人中心查看视频历史
- 📊 实时进度跟踪

#### 命令行界面

```bash
# 基本文本生成视频
ai-movie "一只猫在城市中送外卖"

# 使用自定义角色图片
ai-movie "太空冒险故事" --image character.jpg

# 指定输出目录
ai-movie "喜剧小品" --output ./videos/

# 查看所有可用参数
ai-movie --help
```

#### Python API

```python
import asyncio
from ai_movie.core.video_workflow import VideoWorkflow
from ai_movie.nodes.state import VideoGenerationState

async def generate_video_example():
    # 初始化状态
    state = VideoGenerationState(
        input_text="一只可爱的小狊在花园中玩耶",
        character_image_path="character.jpg"  # 可选
    )
    
    # 创建工作流
    workflow = VideoWorkflow()
    
    # 执行视频生成
    result = await workflow.arun(state)
    
    print(f"视频生成完成: {result['final_video_path']}")
    print(f"OSS 地址: {result.get('oss_url', 'N/A')}")
    
    return result

# 运行示例
asyncio.run(generate_video_example())
```

## 🏢 系统架构

### 技术架构

```mermaid
graph TB
    A[用户输入] --> B[输入解析节点]
    B --> C[文案生成节点]
    C --> D[分镜脚本生成节点]
    D --> E[配音生成节点]
    E --> F[视频生成节点]
    F --> G[视频拼接节点]
    G --> H[背景音乐添加节点]
    H --> I[质量检查节点]
    I --> J[后处理节点]
    J --> K[最终视频]
```

### 核心组件

- **LangGraph 工作流引擎**: 管理复杂的视频生成流程
- **DashScope AI 服务**: 集成多个AI模型
- **Flask Web 框架**: 提供 RESTful API 和 Web 界面
- **MySQL 数据库**: 持久化存储用户数据
- **阿里云 OSS**: 视频文件存储和 CDN 分发
- **FFmpeg**: 视频处理和编码

## 🔧 开发指南

### 开发环境搭建

```bash
# 1. 克隆仓库并进入目录
git clone <repository-url>
cd ai_movie

# 2. 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate

# 3. 安装开发依赖
pip install -r requirements.txt
pip install black ruff mypy pytest pre-commit

# 4. 安装 pre-commit 钩子
pre-commit install

# 5. 配置开发环境变量
cp .env.example .env.development
# 编辑 .env.development 文件
```

### 代码质量工具

```bash
# 代码格式化
black src/ tests/

# 导入排序
isort src/ tests/

# 代码检查
ruff check src/ tests/
ruff check --fix src/ tests/  # 自动修复

# 类型检查
mypy src/

# 全部质量检查
pre-commit run --all-files
```

### 运行测试

```bash
# 运行所有测试
python run_tests.py

# 运行特定类型测试
pytest tests/unit/           # 单元测试
pytest tests/integration/    # 集成测试
pytest tests/web/           # Web API 测试

# 生成测试报告
python generate_test_report.py

# 测试覆盖率
pytest --cov=ai_movie --cov-report=html
```

### 本地开发服务

```bash
# 启动开发服务器
export FLASK_ENV=development
python -m ai_movie.web

# 或者使用开发配置
FLASK_ENV=development python -m ai_movie.web --config development

# 查看日志
tail -f logs/ai_movie_development.log
```

## 📚 文档资源

- [📖 API 文档](docs/api.md) - 详细的 API 接口说明
- [⚙️ 配置指南](docs/configuration.md) - 环境配置和参数设置
- [🛠️ 开发指南](docs/development.md) - 开发环境和流程说明
- [🚀 部署指南](docs/deployment.md) - 生产环境部署指导
- [📊 性能优化](docs/performance.md) - 性能调优和监控
- [🔒 安全指南](docs/security.md) - 安全配置和最佳实践

## 🧑‍💻 参与贡献

我们欢迎各种形式的贡献！请阅读 [贡献指南](CONTRIBUTING.md) 了解详细的行为准则和开发流程。

### 贡献方式

- 🐛 **报告 Bug**: 发现问题请提交 Issue
- ✨ **新功能建议**: 提出功能需求和改进建议
- 📄 **文档改进**: 完善文档和示例
- 📝 **代码贡献**: 提交 Pull Request
- 💬 **问题讨论**: 参与问题讨论和经验分享

### 开发流程

1. Fork 项目仓库
2. 创建功能分支: `git checkout -b feature/amazing-feature`
3. 提交修改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 提交 Pull Request

## 📜 开源协议

该项目采用 MIT 开源协议 - 详情请查看 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢以下开源项目和服务提供商：

- [🤖 DashScope]( https://dashscope.aliyun.com/) - 提供强大的 AI 模型 API 服务
- [🔄 LangGraph](https://github.com/langchain-ai/langgraph) - 工作流编排和管理框架
- [🌶️ Flask](https://flask.palletsprojects.com/) - 轻量级 Web 应用框架
- [📹 FFmpeg](https://ffmpeg.org/) - 强大的多媒体处理工具
- [☁️ 阿里云 OSS](https://www.aliyun.com/product/oss) - 对象存储服务

## 🆘 支持与帮助

遇到问题或需要帮助？我们提供多种支持渠道：

- 🐛 **Bug 报告**: [GitHub Issues](https://github.com/zhangshenzhan7/ai_movie/issues)
- 💬 **问题讨论**: [GitHub Discussions](https://github.com/zhangshenzhan7/ai_movie/discussions)
- 📚 **文档中心**: [Wiki](https://github.com/zhangshenzhan7/ai_movie/wiki)
- 📧 **邮件联系**: support@ai-movie.com

### 常见问题

1. **安装问题**: 请检查 Python 版本和依赖安装
2. **API 密钥问题**: 确保 DashScope API 密钥配置正确
3. **数据库连接**: 检查 MySQL 连接配置和网络访问
4. **视频处理**: 确保 FFmpeg 已正确安装和配置

---

<div align="center">

**✨ 用 AI 技术释放想象力，让视频创作变得简单而高效！✨**

[快速开始](#-快速开始) • [查看文档](#-文档资源) • [提交问题](https://github.com/zhangshenzhan7/ai_movie/)

</div>

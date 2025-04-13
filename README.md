# 🌸 KouriChat - 虚拟与现实交织，温柔永恒的陪伴

[![Python](https://img.shields.io/badge/Python-3.11_➔_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=2B5B84)](https://www.python.org/downloads/)
[![版本](https://img.shields.io/badge/版本-1.3.9-ff69b4?style=for-the-badge)]()

## 📝 项目简介

KouriChat是一个基于人工智能的微信聊天机器人，能够实现角色扮演、智能对话、图像生成与识别、语音消息和持久化记忆等功能。本项目旨在打造一个能够提供温柔陪伴的AI助手，通过微信平台与用户进行无缝交互。

### 🚀 功能特点

- **微信无缝集成**：支持多用户、群聊和私聊场景
- **沉浸式角色扮演**：可配置不同角色和人格
- **智能对话分段**：自然流畅的对话体验
- **情感表情包**：增强交流的情感表达
- **图像生成与识别**：支持图片理解和生成
- **语音消息支持**：实现语音交互
- **持久化记忆**：记住与用户的历史对话
- **自动更新**：保持系统最新
- **热更新功能**：无需重启应用即可更新
- **可视化Web界面**：方便的配置管理

## 🛠️ 快速开始

### 前提条件

1. **辅助设备**：需要一个辅助手机/模拟器/多开应用（微信PC登录需要手机同时在线）
2. **微信小号**：能够PC端登录的微信账号
3. **API密钥**：需要获取DeepSeek等AI服务的API密钥

### 部署方法

#### 半自动设置
```bash
运行 "run.bat"
```

#### 手动设置
```bash
# 安装依赖
pip install -r requirements.txt

# 配置设置
python run_config_web.py

# 启动程序
python run.py
```

## 🧩 项目结构

```
KouriChat/
├── .github/                     # GitHub配置
├── .git/                        # Git仓库
├── data/                        # 运行时数据存储
│   ├── avatars/                 # 角色配置
│   ├── database/                # 数据库文件
│   ├── images/                  # 图像存储
│   └── voices/                  # 语音文件存储
├── logs/                        # 日志文件
├── modules/
│   ├── memory/                  # 记忆管理模块
│   └── reminder/                # 提醒服务模块
├── src/
│   ├── AutoTasker/              # 自动任务系统
│   ├── autoupdate/              # 自动更新功能
│   │   └── updater.py           # 更新管理器
│   ├── config/                  # 配置管理
│   ├── handlers/                # 功能处理器
│   ├── services/                # AI服务接口
│   ├── utils/                   # 实用工具库
│   ├── webui/                   # 可视化配置UI
│   ├── main.py                  # 主程序入口
│   └── avatar_manager.py        # 角色管理
├── requirements.txt             # 项目依赖
├── run.bat                      # Windows运行脚本
├── run.py                       # 主程序启动脚本
├── run_config_web.py            # Web配置启动脚本
├── Thanks.md                    # 鸣谢文档
├── version.json                 # 版本控制
└── LICENSE                      # 许可证文件
```

## 📋 依赖项

项目主要依赖：
- colorama：控制台彩色输出
- Flask：Web服务框架
- openai：OpenAI API接口
- wxauto：微信自动化框架
- SQLAlchemy：数据库ORM
- APScheduler：任务调度
- pandas：数据处理
- jieba：中文分词
- python-dotenv：环境变量管理
- requests：HTTP客户端
- snownlp：中文文本处理
- dateparser：日期解析
- 其他详见requirements.txt

## 🔧 配置说明

项目配置文件位于`src/config/config.json`，包括以下主要配置项：

1. **LLM配置**：API密钥、基础URL、模型选择、最大Token等
2. **用户设置**：监听列表、自动回复设置
3. **行为设置**：角色定义、上下文管理
4. **媒体设置**：图像生成、语音合成、图像识别

可以通过运行`run_config_web.py`进入Web配置界面进行可视化配置。

## 🚀 使用方法

1. 确保满足前提条件并完成配置
2. 运行主程序：`python run.py`或双击`run.bat`
3. 程序将自动初始化系统，连接微信，并开始监听消息
4. 可通过WebUI（http://localhost:8502）进行配置管理

## 💡 开发计划

- 智能任务调度系统
- 记忆优化（8B小型模型）
- 分布式负载均衡
- 数学公式渲染
- 多语言支持

## ⚠️ 免责声明

**法律与道德指南**
- 本项目仅用于技术研究和教育目的
- 禁止用于任何非法或不道德用途
- 生成的内容不代表开发者立场

**使用条款**
- 角色版权归原创者所有
- 用户对自己的行为负全部责任
- 未成年人应在监护人的监督下使用

## 🧑‍💻 技术栈

- Python 3.11+
- wxauto自动化框架
- OpenAI/DeepSeek API
- Flask Web框架
- SQLAlchemy ORM
- APScheduler定时任务

## 📞 联系方式

- QQ群：715616260
- 邮箱：yangchenglin2004@foxmail.com

---

**版本：** 1.3.9  
**最后更新：** 2024-04-09 
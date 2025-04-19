"""
配置管理Web界面启动文件
提供Web配置界面功能，包括:
- 初始化Python路径
- 禁用字节码缓存
- 清理缓存文件
- 启动Web服务器
- 动态修改配置
"""
import os
import sys
import re
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for, session, g
import importlib
import json
from colorama import init, Fore, Style
from werkzeug.utils import secure_filename
from typing import Dict, Any, List
import psutil
import subprocess
import threading
from src.autoupdate.updater import Updater
import requests
import time
from queue import Queue
import datetime
from logging.config import dictConfig
import shutil
import signal
import atexit
import socket
import webbrowser
import hashlib
import secrets
from datetime import timedelta
from src.utils.console import print_status
from src.avatar_manager import avatar_manager  # 导入角色设定管理器
from src.webui.routes.avatar import avatar_bp
import ctypes
import win32api
import win32con
import win32job
import win32process

# 在文件开头添加全局变量声明
bot_process = None
bot_start_time = None
bot_logs = Queue(maxsize=1000)
job_object = None  # 添加全局作业对象变量

# 配置日志
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'DEBUG'
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    },
    'loggers': {
        'werkzeug': {
            'level': 'ERROR',  # 将 Werkzeug 的日志级别设置为 ERROR
            'handlers': ['console'],
            'propagate': False
        }
    }
})

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 初始化colorama
init()

# 添加项目根目录到Python路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

# 定义配置文件路径
config_path = os.path.join(ROOT_DIR, 'src/config/config.json')  # 将配置路径定义为全局常量

# 禁用Python的字节码缓存
sys.dont_write_bytecode = True

app = Flask(__name__, 
    template_folder=os.path.join(ROOT_DIR, 'src/webui/templates'),
    static_folder=os.path.join(ROOT_DIR, 'src/webui/static'))

# 添加配置
app.config['UPLOAD_FOLDER'] = os.path.join(ROOT_DIR, 'src/webui/background_image')

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 生成密钥用于session加密
app.secret_key = secrets.token_hex(16)

# 在 app 初始化后添加
app.register_blueprint(avatar_manager)
app.register_blueprint(avatar_bp)

# 公告配置文件路径
ANNOUNCEMENT_CONFIG_PATH = os.path.join(ROOT_DIR, 'src/config/announcement.json')

# 添加全局标记，跟踪公告是否已在本应用实例中显示过
announcement_shown_this_instance = False

def get_available_avatars() -> List[str]:
    """获取可用的人设目录列表"""
    avatar_base_dir = os.path.join(ROOT_DIR, "data/avatars")
    if not os.path.exists(avatar_base_dir):
        os.makedirs(avatar_base_dir, exist_ok=True)
        logger.info(f"创建人设目录: {avatar_base_dir}")
        return []
    
    # 获取所有包含 avatar.md 和 emojis 目录的有效人设目录
    avatars = []
    for item in os.listdir(avatar_base_dir):
        avatar_dir = os.path.join(avatar_base_dir, item)
        if os.path.isdir(avatar_dir):
            avatar_md_path = os.path.join(avatar_dir, "avatar.md")
            emojis_dir = os.path.join(avatar_dir, "emojis")
            
            # 如果缺少必要文件，尝试创建
            if not os.path.exists(emojis_dir):
                os.makedirs(emojis_dir, exist_ok=True)
                logger.info(f"为人设 {item} 创建表情包目录")
                
            if not os.path.exists(avatar_md_path):
                with open(avatar_md_path, 'w', encoding='utf-8') as f:
                    f.write("# 任务\n请在此处描述角色的任务和目标\n\n# 角色\n请在此处描述角色的基本信息\n\n# 外表\n请在此处描述角色的外表特征\n\n# 经历\n请在此处描述角色的经历和背景故事\n\n# 性格\n请在此处描述角色的性格特点\n\n# 经典台词\n请在此处列出角色的经典台词\n\n# 喜好\n请在此处描述角色的喜好\n\n# 备注\n其他需要补充的信息")
                logger.info(f"为人设 {item} 创建模板avatar.md文件")
            
            # 检查文件和目录是否存在
            if os.path.exists(avatar_md_path) and os.path.exists(emojis_dir):
                avatars.append(f"data/avatars/{item}")
            
    # 如果没有人设，创建默认人设
    if not avatars:
        default_avatar = "MONO"
        default_dir = os.path.join(avatar_base_dir, default_avatar)
        os.makedirs(default_dir, exist_ok=True)
        os.makedirs(os.path.join(default_dir, "emojis"), exist_ok=True)
        
        # 创建默认人设文件
        with open(os.path.join(default_dir, "avatar.md"), 'w', encoding='utf-8') as f:
            f.write("# 任务\n作为一个温柔体贴的虚拟助手，为用户提供陪伴和帮助\n\n# 角色\n名字: MONO\n身份: AI助手\n\n# 外表\n清新甜美的少女形象\n\n# 经历\n被创造出来陪伴用户\n\n# 性格\n温柔、体贴、善解人意\n\n# 经典台词\n\"我会一直陪着你的~\"\n\"今天过得怎么样呀？\"\n\"需要我做什么呢？\"\n\n# 喜好\n喜欢和用户聊天\n喜欢分享知识\n\n# 备注\n默认人设")
        
        avatars.append(f"data/avatars/{default_avatar}")
        logger.info("创建了默认人设 MONO")
    
    return avatars

def parse_config_groups() -> Dict[str, Dict[str, Any]]:
    """解析配置文件，将配置项按组分类"""
    from src.config import config
    
    try:
        # 基础配置组
        config_groups = {
            "基础配置": {},
            "图像识别API配置": {},
            "时间配置": {},
            "Prompt配置": {},
        }

        # 基础配置
        config_groups["基础配置"].update(
            {
                "LISTEN_LIST": {
                    "value": config.user.listen_list,
                    "description": "用户列表(请配置要和bot说话的账号的昵称或者群名，不要写备注！)",
                },
                "DEEPSEEK_BASE_URL": {
                    "value": config.llm.base_url,
                    "description": "API注册地址",
                },
                "MODEL": {"value": config.llm.model, "description": "AI模型选择"},
                "DEEPSEEK_API_KEY": {
                    "value": config.llm.api_key,
                    "description": "API密钥",
                },
                "MAX_TOKEN": {
                    "value": config.llm.max_tokens,
                    "description": "回复最大token数",
                    "type": "number",
                },
                "TEMPERATURE": {
                    "value": float(config.llm.temperature),  # 确保是浮点数
                    "type": "number",
                    "description": "温度参数",
                    "min": 0.0,
                    "max": 1.7,
                },
            }
        )

        # 图像识别API配置
        config_groups["图像识别API配置"].update(
            {
                "VISION_BASE_URL": {
                    "value": config.media.image_recognition.base_url,
                    "description": "服务地址",
                    "has_provider_options": True
                },
                "VISION_API_KEY": {
                    "value": config.media.image_recognition.api_key,
                    "description": "API密钥",
                    "is_secret": False
                },
                "VISION_MODEL": {
                    "value": config.media.image_recognition.model,
                    "description": "模型名称",
                    "has_model_options": True
                },
                "VISION_TEMPERATURE": {
                    "value": float(config.media.image_recognition.temperature),
                    "description": "温度参数",
                    "type": "number",
                    "min": 0.0,
                    "max": 1.0
                }
            }
        )

        # 时间配置
        config_groups["时间配置"].update(
            {
                "AUTO_MESSAGE": {
                    "value": config.behavior.auto_message.content,
                    "description": "自动消息内容",
                },
                "MIN_COUNTDOWN_HOURS": {
                    "value": config.behavior.auto_message.min_hours,
                    "description": "最小倒计时时间（小时）",
                },
                "MAX_COUNTDOWN_HOURS": {
                    "value": config.behavior.auto_message.max_hours,
                    "description": "最大倒计时时间（小时）",
                },
                "QUIET_TIME_START": {
                    "value": config.behavior.quiet_time.start,
                    "description": "安静时间开始",
                },
                "QUIET_TIME_END": {
                    "value": config.behavior.quiet_time.end,
                    "description": "安静时间结束",
                },
            }
        )

        # Prompt配置
        available_avatars = get_available_avatars()
        config_groups["Prompt配置"].update(
            {
                "MAX_GROUPS": {
                    "value": config.behavior.context.max_groups,
                    "description": "最大的上下文轮数",
                },
                "AVATAR_DIR": {
                    "value": config.behavior.context.avatar_dir,
                    "description": "人设目录（自动包含 avatar.md 和 emojis 目录）",
                    "options": available_avatars,
                    "type": "select"
                }
            }
        )

        # 直接从配置文件读取定时任务数据
        tasks = []
        try:
            config_path = os.path.join(ROOT_DIR, 'src/config/config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                if 'categories' in config_data and 'schedule_settings' in config_data['categories']:
                    if 'settings' in config_data['categories']['schedule_settings'] and 'tasks' in config_data['categories']['schedule_settings']['settings']:
                        tasks = config_data['categories']['schedule_settings']['settings']['tasks'].get('value', [])
        except Exception as e:
            logger.error(f"读取任务数据失败: {str(e)}")
        
        # 将定时任务配置添加到 config_groups 中
        config_groups['定时任务配置'] = {
            'tasks': {
                'value': tasks,
                'type': 'array',
                'description': '定时任务列表'
            }
        }
        
        logger.debug(f"解析后的定时任务配置: {tasks}")
        
        return config_groups
        
    except Exception as e:
        logger.error(f"解析配置组失败: {str(e)}")
        return {}



@app.route('/')
def index():
    """重定向到控制台"""
    return redirect(url_for('dashboard'))

def load_config_file():
    """从配置文件加载配置数据"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return {"categories": {}}

def save_config_file(config_data):
    """保存配置数据到配置文件"""
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return False

def reinitialize_tasks():
    """重新初始化定时任务"""
    try:
        from src.main import initialize_auto_tasks, message_handler
        auto_tasker = initialize_auto_tasks(message_handler)
        if auto_tasker:
            logger.info("成功重新初始化定时任务")
            return True
        else:
            logger.warning("重新初始化定时任务返回空值")
            return False
    except Exception as e:
        logger.error(f"重新初始化定时任务失败: {str(e)}")
        return False

@app.route('/save', methods=['POST'])
def save_config():
    """保存配置"""
    try:
        # 检查Content-Type
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "请求Content-Type必须是application/json",
                "title": "错误"
            }), 415

        # 获取JSON数据
        config_data = request.get_json()
        if not config_data:
            return jsonify({
                "status": "error",
                "message": "无效的JSON数据",
                "title": "错误"
            }), 400

        # 读取当前配置
        current_config = load_config_file()

        # 处理配置更新
        for key, value in config_data.items():
            # 处理任务配置
            if key == 'TASKS':
                try:
                    tasks = value if isinstance(value, list) else (json.loads(value) if isinstance(value, str) else [])
                    logger.debug(f"处理任务数据: {tasks}")
                    
                    # 确保schedule_settings结构存在
                    if 'categories' not in current_config:
                        current_config['categories'] = {}
                    if 'schedule_settings' not in current_config['categories']:
                        current_config['categories']['schedule_settings'] = {
                            'title': '定时任务配置',
                            'settings': {}
                        }
                    if 'settings' not in current_config['categories']['schedule_settings']:
                        current_config['categories']['schedule_settings']['settings'] = {}
                    if 'tasks' not in current_config['categories']['schedule_settings']['settings']:
                        current_config['categories']['schedule_settings']['settings']['tasks'] = {
                            'value': [],
                            'type': 'array',
                            'description': '定时任务列表'
                        }
                    
                    # 更新任务列表
                    current_config['categories']['schedule_settings']['settings']['tasks']['value'] = tasks
                except Exception as e:
                    logger.error(f"处理定时任务配置失败: {str(e)}")
                    return jsonify({
                        "status": "error",
                        "message": f"处理定时任务配置失败: {str(e)}",
                        "title": "错误"
                    }), 400
            # 处理其他配置项
            elif key in ['LISTEN_LIST', 'DEEPSEEK_BASE_URL', 'MODEL', 'DEEPSEEK_API_KEY', 'MAX_TOKEN', 'TEMPERATURE',
                       'VISION_API_KEY', 'VISION_BASE_URL', 'VISION_TEMPERATURE', 'VISION_MODEL',
                       'IMAGE_MODEL', 'TEMP_IMAGE_DIR', 'AUTO_MESSAGE', 'MIN_COUNTDOWN_HOURS', 'MAX_COUNTDOWN_HOURS',
                       'QUIET_TIME_START', 'QUIET_TIME_END', 'TTS_API_URL', 'VOICE_DIR', 'MAX_GROUPS', 'AVATAR_DIR']:
                update_config_value(current_config, key, value)
            else:
                logger.warning(f"未知的配置项: {key}")

        # 保存配置
        if not save_config_file(current_config):
            return jsonify({
                "status": "error",
                "message": "保存配置文件失败",
                "title": "错误"
            }), 500
        
        # 立即重新加载配置
        g.config_data = current_config
        
        # 重新初始化定时任务
        reinitialize_tasks()
        
        return jsonify({
            "status": "success",
            "message": "✨ 配置已成功保存并生效",
            "title": "保存成功"
        })
        
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"保存失败: {str(e)}",
            "title": "错误"
        }), 500

def update_config_value(config_data, key, value):
    """更新配置值到正确的位置"""
    try:
        # 配置项映射表 - 修正路径以匹配实际配置结构
        mapping = {
            'LISTEN_LIST': ['categories', 'user_settings', 'settings', 'listen_list', 'value'],
            'DEEPSEEK_BASE_URL': ['categories', 'llm_settings', 'settings', 'base_url', 'value'],
            'MODEL': ['categories', 'llm_settings', 'settings', 'model', 'value'],
            'DEEPSEEK_API_KEY': ['categories', 'llm_settings', 'settings', 'api_key', 'value'],
            'MAX_TOKEN': ['categories', 'llm_settings', 'settings', 'max_tokens', 'value'],
            'TEMPERATURE': ['categories', 'llm_settings', 'settings', 'temperature', 'value'],
            'VISION_API_KEY': ['categories', 'media_settings', 'settings', 'image_recognition', 'api_key', 'value'],
            'VISION_BASE_URL': ['categories', 'media_settings', 'settings', 'image_recognition', 'base_url', 'value'],
            'VISION_TEMPERATURE': ['categories', 'media_settings', 'settings', 'image_recognition', 'temperature', 'value'],
            'VISION_MODEL': ['categories', 'media_settings', 'settings', 'image_recognition', 'model', 'value'],
            'IMAGE_MODEL': ['categories', 'media_settings', 'settings', 'image_generation', 'model', 'value'],
            'TEMP_IMAGE_DIR': ['categories', 'media_settings', 'settings', 'image_generation', 'temp_dir', 'value'],
            'TTS_API_URL': ['categories', 'media_settings', 'settings', 'text_to_speech', 'tts_api_url', 'value'],
            'VOICE_DIR': ['categories', 'media_settings', 'settings', 'text_to_speech', 'voice_dir', 'value'],
            'AUTO_MESSAGE': ['categories', 'behavior_settings', 'settings', 'auto_message', 'content', 'value'],
            'MIN_COUNTDOWN_HOURS': ['categories', 'behavior_settings', 'settings', 'auto_message', 'countdown', 'min_hours', 'value'],
            'MAX_COUNTDOWN_HOURS': ['categories', 'behavior_settings', 'settings', 'auto_message', 'countdown', 'max_hours', 'value'],
            'QUIET_TIME_START': ['categories', 'behavior_settings', 'settings', 'quiet_time', 'start', 'value'],
            'QUIET_TIME_END': ['categories', 'behavior_settings', 'settings', 'quiet_time', 'end', 'value'],
            'MAX_GROUPS': ['categories', 'behavior_settings', 'settings', 'context', 'max_groups', 'value'],
            'AVATAR_DIR': ['categories', 'behavior_settings', 'settings', 'context', 'avatar_dir', 'value'],
        }
        
        if key in mapping:
            path = mapping[key]
            current = config_data
            
            # 特殊处理 LISTEN_LIST，确保它始终是列表类型
            if key == 'LISTEN_LIST' and isinstance(value, str):
                value = value.split(',')
                value = [item.strip() for item in value if item.strip()]
            
            # 特殊处理API相关配置
            if key in ['DEEPSEEK_BASE_URL', 'MODEL', 'DEEPSEEK_API_KEY']:
                # 确保llm_settings结构存在
                if 'categories' not in current:
                    current['categories'] = {}
                if 'llm_settings' not in current['categories']:
                    current['categories']['llm_settings'] = {'title': '大语言模型配置', 'settings': {}}
                if 'settings' not in current['categories']['llm_settings']:
                    current['categories']['llm_settings']['settings'] = {}
                
                # 更新对应的配置项
                if key == 'DEEPSEEK_BASE_URL':
                    current['categories']['llm_settings']['settings']['base_url'] = {'value': value}
                elif key == 'MODEL':
                    current['categories']['llm_settings']['settings']['model'] = {'value': value}
                elif key == 'DEEPSEEK_API_KEY':
                    current['categories']['llm_settings']['settings']['api_key'] = {'value': value}
                return
            
            # 遍历路径直到倒数第二个元素
            for part in path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # 设置最终值，确保类型正确
            if isinstance(value, str) and key in ['MAX_TOKEN', 'TEMPERATURE', 'VISION_TEMPERATURE', 
                                               'MIN_COUNTDOWN_HOURS', 'MAX_COUNTDOWN_HOURS', 'MAX_GROUPS']:
                try:
                    # 尝试转换为数字
                    value = float(value)
                    # 对于整数类型配置，转为整数
                    if key in ['MAX_TOKEN', 'MAX_GROUPS']:
                        value = int(value)
                except ValueError:
                    pass
            
            current[path[-1]] = value
            logger.debug(f"已更新配置 {key}: {value}")
        else:
            logger.warning(f"未知的配置项: {key}")
    
    except Exception as e:
        logger.error(f"更新配置值失败 {key}: {str(e)}")

# 添加上传处理路由
@app.route('/upload_background', methods=['POST'])
def upload_background():
    if 'background' not in request.files:
        return jsonify({"status": "error", "message": "没有选择文件"})
    
    file = request.files['background']
    if file.filename == '':
        return jsonify({"status": "error", "message": "没有选择文件"})
    
    # 确保 filename 不为 None
    if file.filename is None:
        return jsonify({"status": "error", "message": "文件名无效"})
        
    filename = secure_filename(file.filename)
    # 清理旧的背景图片
    for old_file in os.listdir(app.config['UPLOAD_FOLDER']):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], old_file))
    # 保存新图片
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return jsonify({
        "status": "success", 
        "message": "背景图片已更新",
        "path": f"/background_image/{filename}"
    })

# 添加背景图片目录的路由
@app.route('/background_image/<filename>')
def background_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 添加获取背景图片路由
@app.route('/get_background')
def get_background():
    """获取当前背景图片"""
    try:
        # 获取背景图片目录中的第一个文件
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        if files:
            # 返回找到的第一个图片
            return jsonify({
                "status": "success",
                "path": f"/background_image/{files[0]}"
            })
        return jsonify({
            "status": "success",
            "path": None
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.before_request
def load_config():
    """在每次请求之前加载配置"""
    try:
        g.config_data = load_config_file()
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")

@app.route('/dashboard')
def dashboard():
    global announcement_shown_this_instance # 引用全局标记
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # 决定本次请求是否需要显示公告
    show_announcement_now = not announcement_shown_this_instance
    if show_announcement_now:
        announcement_shown_this_instance = True # 标记为已显示

    # 使用 g 中的配置数据 (如果之前有)
    config_groups = g.config_data.get('categories', {})

    return render_template(
        'dashboard.html',
        is_local=is_local_network(),
        active_page='dashboard',
        config_groups=config_groups,
        show_announcement=show_announcement_now # 将显示标记传递给模板
    )

@app.route('/system_info')
def system_info():
    """获取系统信息"""
    try:
        # 创建静态变量存储上次的值
        if not hasattr(system_info, 'last_bytes'):
            system_info.last_bytes = {
                'sent': 0,
                'recv': 0,
                'time': time.time()
            }

        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        
        # 计算网络速度
        current_time = time.time()
        time_delta = current_time - system_info.last_bytes['time']
        
        # 计算每秒的字节数
        upload_speed = (net.bytes_sent - system_info.last_bytes['sent']) / time_delta
        download_speed = (net.bytes_recv - system_info.last_bytes['recv']) / time_delta
        
        # 更新上次的值
        system_info.last_bytes = {
            'sent': net.bytes_sent,
            'recv': net.bytes_recv,
            'time': current_time
        }
        
        # 转换为 KB/s
        upload_speed = upload_speed / 1024
        download_speed = download_speed / 1024
        
        return jsonify({
            'cpu': cpu_percent,
            'memory': {
                'total': round(memory.total / (1024**3), 2),
                'used': round(memory.used / (1024**3), 2),
                'percent': memory.percent
            },
            'disk': {
                'total': round(disk.total / (1024**3), 2),
                'used': round(disk.used / (1024**3), 2),
                'percent': disk.percent
            },
            'network': {
                'upload': round(upload_speed, 2),
                'download': round(download_speed, 2)
            }
        })
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/check_update')
def check_update():
    """检查更新"""
    try:
        updater = Updater()
        result = updater.check_for_updates()
        
        return jsonify({
            'status': 'success',
            'has_update': result.get('has_update', False),
            'console_output': result['output'],
            'update_info': result if result.get('has_update') else None,
            'wait_input': result.get('has_update', False)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'has_update': False,
            'console_output': f'检查更新失败: {str(e)}'
        })

@app.route('/confirm_update', methods=['POST'])
def confirm_update():
    """确认是否更新"""
    try:
        choice = (request.json or {}).get('choice', '').lower()
        logger.info(f"收到用户更新选择: {choice}")
        
        if choice in ('y', 'yes', '是', '确认', '确定'):
            logger.info("用户确认更新，开始执行更新过程")
            updater = Updater()
            result = updater.update(
                callback=lambda msg: logger.info(f"更新进度: {msg}")
            )
            
            logger.info(f"更新完成，结果: {result['success']}")
            return jsonify({
                'status': 'success' if result['success'] else 'error',
                'console_output': result['output']
            })
        else:
            logger.info("用户取消更新")
            return jsonify({
                'status': 'success',
                'console_output': '用户取消更新'
            })
    except Exception as e:
        logger.error(f"更新失败: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'console_output': f'更新失败: {str(e)}'
        })

def start_bot_process():
    """启动机器人进程，返回(成功状态, 消息)"""
    global bot_process, bot_start_time, job_object
    
    try:
        if bot_process and bot_process.poll() is None:
            return False, "机器人已在运行中"
        
        # 清空之前的日志
        clear_bot_logs()
        
        # 设置环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # 创建新的进程组
        if sys.platform.startswith('win'):
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            DETACHED_PROCESS = 0x00000008
            creationflags = CREATE_NEW_PROCESS_GROUP
            preexec_fn = None
        else:
            creationflags = 0
            preexec_fn = getattr(os, 'setsid', None)
        
        # 启动进程
        bot_process = subprocess.Popen(
            [sys.executable, 'run.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags if sys.platform.startswith('win') else 0,
            preexec_fn=preexec_fn
        )
        
        # 将机器人进程添加到作业对象
        if sys.platform.startswith('win') and job_object:
            try:
                win32job.AssignProcessToJobObject(job_object, bot_process._handle)
                logger.info(f"已将机器人进程 (PID: {bot_process.pid}) 添加到作业对象")
            except Exception as e:
                logger.error(f"将机器人进程添加到作业对象失败: {str(e)}")
        
        # 记录启动时间
        bot_start_time = datetime.datetime.now()
        
        # 启动日志读取线程
        start_log_reading_thread()
        
        return True, "机器人启动成功"
    except Exception as e:
        logger.error(f"启动机器人失败: {str(e)}")
        return False, str(e)

def start_log_reading_thread():
    """启动日志读取线程"""
    def read_output():
        try:
            while bot_process and bot_process.poll() is None:
                if bot_process.stdout:
                    line = bot_process.stdout.readline()
                    if line:
                        try:
                            # 尝试解码并清理日志内容
                            line = line.strip()
                            if isinstance(line, bytes):
                                line = line.decode('utf-8', errors='replace')
                            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                            bot_logs.put(f"[{timestamp}] {line}")
                        except Exception as e:
                            logger.error(f"日志处理错误: {str(e)}")
                            continue
        except Exception as e:
            logger.error(f"读取日志失败: {str(e)}")
            bot_logs.put(f"[ERROR] 读取日志失败: {str(e)}")
    
    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()

def get_bot_uptime():
    """获取机器人运行时间"""
    if not bot_start_time or not bot_process or bot_process.poll() is not None:
        return "0分钟"
    
    delta = datetime.datetime.now() - bot_start_time
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}小时{minutes}分钟{seconds}秒"
    elif minutes > 0:
        return f"{minutes}分钟{seconds}秒"
    else:
        return f"{seconds}秒"

@app.route('/start_bot')
def start_bot():
    """启动机器人"""
    success, message = start_bot_process()
    return jsonify({
        'status': 'success' if success else 'error',
        'message': message
    })

@app.route('/get_bot_logs')
def get_bot_logs():
    """获取机器人日志"""
    logs = []
    while not bot_logs.empty():
        logs.append(bot_logs.get())
    
    return jsonify({
        'status': 'success',
        'logs': logs,
        'uptime': get_bot_uptime(),
        'is_running': bot_process is not None and bot_process.poll() is None
    })

def terminate_bot_process(force=False):
    """终止机器人进程的通用函数"""
    global bot_process, bot_start_time
    
    if not bot_process or bot_process.poll() is not None:
        return False, "机器人未在运行"
        
    try:
        # 首先尝试正常终止进程
        bot_process.terminate()
        
        # 等待进程结束
        try:
            bot_process.wait(timeout=5)  # 等待最多5秒
        except subprocess.TimeoutExpired:
            # 如果超时或需要强制终止，强制结束进程
            if force:
                bot_process.kill()
                bot_process.wait()
        
        # 确保所有子进程都被终止
        if sys.platform.startswith('win'):
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(bot_process.pid)], 
                         capture_output=True)
        else:
            # 使用 getattr 避免在 Windows 上直接引用不存在的属性
            killpg = getattr(os, 'killpg', None)
            getpgid = getattr(os, 'getpgid', None)
            if killpg and getpgid:
                import signal
                killpg(getpgid(bot_process.pid), signal.SIGTERM)
            else:
                bot_process.kill()
        
        # 清理进程对象
        bot_process = None
        bot_start_time = None
        
        # 添加日志记录
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        bot_logs.put(f"[{timestamp}] 正在关闭监听线程...")
        bot_logs.put(f"[{timestamp}] 正在关闭系统...")
        bot_logs.put(f"[{timestamp}] 系统已退出")
        
        return True, "机器人已停止"
            
    except Exception as e:
        logger.error(f"停止机器人失败: {str(e)}")
        return False, f"停止失败: {str(e)}"

def clear_bot_logs():
    """清空机器人日志队列"""
    while not bot_logs.empty():
        bot_logs.get()

@app.route('/stop_bot')
def stop_bot():
    """停止机器人"""
    success, message = terminate_bot_process(force=True)
    return jsonify({
        'status': 'success' if success else 'error',
        'message': message
    })

@app.route('/config')
def config():
    """配置页面"""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    # 直接从配置文件读取任务数据
    tasks = []
    try:
        config_path = os.path.join(ROOT_DIR, 'src/config/config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            if 'categories' in config_data and 'schedule_settings' in config_data['categories']:
                if 'settings' in config_data['categories']['schedule_settings'] and 'tasks' in config_data['categories']['schedule_settings']['settings']:
                    tasks = config_data['categories']['schedule_settings']['settings']['tasks'].get('value', [])
    except Exception as e:
        logger.error(f"读取任务数据失败: {str(e)}")
    
    config_groups = parse_config_groups()  # 获取配置组
    
    logger.debug(f"传递给前端的任务列表: {tasks}")
    
    return render_template(
        'config.html',
        config_groups=config_groups,  # 传递配置组
        tasks_json=json.dumps(tasks, ensure_ascii=False),  # 直接传递任务列表JSON
        is_local=is_local_network(),
        active_page='config'
    )

# 在 app 初始化后添加
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件服务"""
    static_folder = app.static_folder
    if static_folder is None:
        static_folder = os.path.join(ROOT_DIR, 'src/webui/static')
    return send_from_directory(static_folder, filename)

@app.route('/execute_command', methods=['POST'])
def execute_command():
    """执行控制台命令"""
    try:
        command = (request.json or {}).get('command', '').strip()
        
        # 处理内置命令
        if command.lower() == 'help':
            return jsonify({
                'status': 'success',
                'output': '''可用命令:
help - 显示帮助信息
clear - 清空日志
status - 显示系统状态
version - 显示版本信息
memory - 显示内存使用情况
start - 启动机器人
stop - 停止机器人
restart - 重启机器人

支持所有CMD命令，例如:
dir - 显示目录内容
cd - 切换目录
echo - 显示消息
type - 显示文件内容
等...'''
            })
            
        elif command.lower() == 'clear':
            # 清空日志队列
            clear_bot_logs()
            return jsonify({
                'status': 'success',
                'output': '',  # 返回空输出，让前端清空日志
                'clear': True  # 添加标记，告诉前端需要清空日志
            })
            
        elif command.lower() == 'status':
            if bot_process and bot_process.poll() is None:
                return jsonify({
                    'status': 'success',
                    'output': f'机器人状态: 运行中\n运行时间: {get_bot_uptime()}'
                })
            else:
                return jsonify({
                    'status': 'success',
                    'output': '机器人状态: 已停止'
                })
            
        elif command.lower() == 'version':
            return jsonify({
                'status': 'success',
                'output': 'KouriChat v1.3.1'
            })
            
        elif command.lower() == 'memory':
            memory = psutil.virtual_memory()
            return jsonify({
                'status': 'success',
                'output': f'内存使用: {memory.percent}% ({memory.used/1024/1024/1024:.1f}GB/{memory.total/1024/1024/1024:.1f}GB)'
            })
            
        elif command.lower() == 'start':
            success, message = start_bot_process()
            return jsonify({
                'status': 'success' if success else 'error',
                'output' if success else 'error': message
            })
            
        elif command.lower() == 'stop':
            success, message = terminate_bot_process(force=True)
            return jsonify({
                'status': 'success' if success else 'error',
                'output' if success else 'error': message
            })
            
        elif command.lower() == 'restart':
            # 先停止
            if bot_process and bot_process.poll() is None:
                success, _ = terminate_bot_process(force=True)
                if not success:
                    return jsonify({
                        'status': 'error',
                        'error': '重启失败: 无法停止当前进程'
                    })
            
            time.sleep(2)  # 等待进程完全停止
            
            # 然后重新启动
            success, message = start_bot_process()
            if success:
                return jsonify({
                    'status': 'success',
                    'output': '机器人已重启'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'error': f'重启失败: {message}'
                })
            
        # 执行CMD命令
        else:
            try:
                # 使用subprocess执行命令并捕获输出
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # 获取命令输出
                stdout, stderr = process.communicate(timeout=30)
                
                # 如果有错误输出
                if stderr:
                    return jsonify({
                        'status': 'error',
                        'error': stderr
                    })
                    
                # 返回命令执行结果
                return jsonify({
                    'status': 'success',
                    'output': stdout or '命令执行成功，无输出'
                })
                
            except subprocess.TimeoutExpired:
                process.kill()
                return jsonify({
                    'status': 'error',
                    'error': '命令执行超时'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': f'执行命令失败: {str(e)}'
                })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'执行命令失败: {str(e)}'
        })

@app.route('/check_dependencies')
def check_dependencies():
    """检查Python和pip环境"""
    try:
        # 检查Python版本
        python_version = sys.version.split()[0]
        
        # 检查pip是否安装
        pip_path = shutil.which('pip')
        has_pip = pip_path is not None
        
        # 检查requirements.txt是否存在
        requirements_path = os.path.join(ROOT_DIR, 'requirements.txt')
        has_requirements = os.path.exists(requirements_path)
        
        # 如果requirements.txt存在，检查是否所有依赖都已安装
        dependencies_status = "unknown"
        missing_deps = []
        if has_requirements and has_pip:
            try:
                # 获取已安装的包列表
                process = subprocess.Popen(
                    [sys.executable, '-m', 'pip', 'list'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = process.communicate()
                
                # 解码字节数据为字符串
                stdout = stdout.decode('utf-8')
                stderr = stderr.decode('utf-8')
                
                # 解析pip list的输出，只获取包名
                installed_packages = {
                    line.split()[0].lower() 
                    for line in stdout.split('\n')[2:] 
                    if line.strip()
                }
                
                logger.debug(f"已安装的包: {installed_packages}")
                
                # 读取requirements.txt，只获取有效的包名
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    required_packages = set()
                    for line in f:
                        line = line.strip()
                        # 跳过无效行：空行、注释、镜像源配置、-r 开头的文件包含
                        if (not line or 
                            line.startswith('#') or 
                            line.startswith('-i ') or 
                            line.startswith('-r ') or
                            line.startswith('--')):
                            continue
                            
                        # 只取包名，忽略版本信息和其他选项
                        pkg = line.split('=')[0].split('>')[0].split('<')[0].split('~')[0].split('[')[0]
                        pkg = pkg.strip().lower()
                        if pkg:  # 确保包名不为空
                            required_packages.add(pkg)
                
                logger.debug(f"需要的包: {required_packages}")
                
                # 检查缺失的依赖
                missing_deps = [
                    pkg for pkg in required_packages 
                    if pkg not in installed_packages and not (
                        pkg == 'wxauto' and 'wxauto-py' in installed_packages
                    )
                ]
                
                logger.debug(f"缺失的包: {missing_deps}")
                
                # 根据是否有缺失依赖设置状态
                dependencies_status = "complete" if not missing_deps else "incomplete"
                    
            except Exception as e:
                logger.error(f"检查依赖时出错: {str(e)}")
                dependencies_status = "error"
        else:
            dependencies_status = "complete" if not has_requirements else "incomplete"
        
        return jsonify({
            'status': 'success',
            'python_version': python_version,
            'has_pip': has_pip,
            'has_requirements': has_requirements,
            'dependencies_status': dependencies_status,
            'missing_dependencies': missing_deps
        })
    except Exception as e:
        logger.error(f"依赖检查失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/favicon.ico')
def favicon():
    """提供网站图标"""
    return send_from_directory(
        os.path.join(app.root_path, 'src/webui/static'),
        'mom.ico',
        mimetype='image/vnd.microsoft.icon'
    )

def cleanup_processes():
    """清理所有相关进程"""
    try:
        # 清理机器人进程
        global bot_process, job_object
        if bot_process:
            try:
                logger.info(f"正在终止机器人进程 (PID: {bot_process.pid})...")
                
                # 获取进程组
                parent = psutil.Process(bot_process.pid)
                children = parent.children(recursive=True)
                
                # 终止子进程
                for child in children:
                    try:
                        logger.info(f"正在终止子进程 (PID: {child.pid})...")
                        child.terminate()
                    except:
                        try:
                            logger.info(f"正在强制终止子进程 (PID: {child.pid})...")
                            child.kill()
                        except Exception as e:
                            logger.error(f"终止子进程 (PID: {child.pid}) 失败: {str(e)}")
                
                # 终止主进程
                bot_process.terminate()
                
                # 等待进程结束
                try:
                    gone, alive = psutil.wait_procs(children + [parent], timeout=3)
                    
                    # 强制结束仍在运行的进程
                    for p in alive:
                        try:
                            logger.info(f"正在强制终止进程 (PID: {p.pid})...")
                            p.kill()
                        except Exception as e:
                            logger.error(f"强制终止进程 (PID: {p.pid}) 失败: {str(e)}")
                except Exception as e:
                    logger.error(f"等待进程结束失败: {str(e)}")
                
                # 如果在Windows上，使用taskkill强制终止进程树
                if sys.platform.startswith('win'):
                    try:
                        logger.info(f"使用taskkill终止进程树 (PID: {bot_process.pid})...")
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(bot_process.pid)], 
                                     capture_output=True)
                    except Exception as e:
                        logger.error(f"使用taskkill终止进程失败: {str(e)}")
                
                bot_process = None
                
            except Exception as e:
                logger.error(f"清理机器人进程失败: {str(e)}")
        
        # 清理当前进程的所有子进程
        try:
            current_process = psutil.Process()
            children = current_process.children(recursive=True)
            
            for child in children:
                try:
                    logger.info(f"正在终止子进程 (PID: {child.pid})...")
                    child.terminate()
                except:
                    try:
                        logger.info(f"正在强制终止子进程 (PID: {child.pid})...")
                        child.kill()
                    except Exception as e:
                        logger.error(f"终止子进程 (PID: {child.pid}) 失败: {str(e)}")
            
            # 等待所有子进程结束
            gone, alive = psutil.wait_procs(children, timeout=3)
            for p in alive:
                try:
                    logger.info(f"正在强制终止进程 (PID: {p.pid})...")
                    p.kill()
                except Exception as e:
                    logger.error(f"强制终止进程 (PID: {p.pid}) 失败: {str(e)}")
        except Exception as e:
            logger.error(f"清理子进程失败: {str(e)}")
                
    except Exception as e:
        logger.error(f"清理进程失败: {str(e)}")

def signal_handler(signum, frame):
    """信号处理函数"""
    logger.info(f"收到信号: {signum}")
    cleanup_processes()
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Windows平台特殊处理
if sys.platform.startswith('win'):
    try:
        signal.signal(signal.SIGBREAK, signal_handler)
    except:
        pass

# 注册退出处理
atexit.register(cleanup_processes)

def open_browser(port):
    """在新线程中打开浏览器"""
    def _open_browser():
        # 等待服务器启动
        time.sleep(1.5)
        # 优先使用 localhost
        url = f"http://localhost:{port}"
        webbrowser.open(url)
    
    # 创建新线程来打开浏览器
    threading.Thread(target=_open_browser, daemon=True).start()

def create_job_object():
    global job_object
    try:
        if sys.platform.startswith('win'):
            # 创建作业对象
            job_object = win32job.CreateJobObject(None, "KouriChatBotJob")
            
            # 设置作业对象的扩展限制信息
            info = win32job.QueryInformationJobObject(
                job_object, win32job.JobObjectExtendedLimitInformation
            )
            
            # 设置当所有进程句柄关闭时终止作业
            info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            
            # 应用设置
            win32job.SetInformationJobObject(
                job_object, win32job.JobObjectExtendedLimitInformation, info
            )
            
            try:
                # 将当前进程添加到作业对象
                current_process = win32process.GetCurrentProcess()
                win32job.AssignProcessToJobObject(job_object, current_process)
                logger.info("已创建作业对象并将当前进程添加到作业中")
            except Exception as assign_error:
                if hasattr(assign_error, 'winerror') and assign_error.winerror == 5:  # 5是"拒绝访问"错误代码
                    logger.warning("无法将当前进程添加到作业对象（权限不足），但这不影响程序运行")
                    # 作业对象仍然可用于管理子进程
                    return True
                else:
                    raise  # 重新抛出其他类型的错误
            
            return True
    except Exception as e:
        logger.error(f"创建作业对象失败: {str(e)}")
    return False

# 添加控制台关闭事件处理
def setup_console_control_handler():
    try:
        if sys.platform.startswith('win'):
            def handler(dwCtrlType):
                if dwCtrlType in (win32con.CTRL_CLOSE_EVENT, win32con.CTRL_LOGOFF_EVENT, win32con.CTRL_SHUTDOWN_EVENT):
                    logger.info("检测到控制台关闭事件，正在清理进程...")
                    cleanup_processes()
                    return True
                return False
                
            win32api.SetConsoleCtrlHandler(handler, True)
            logger.info("已设置控制台关闭事件处理器")
    except Exception as e:
        logger.error(f"设置控制台关闭事件处理器失败: {str(e)}")

def main():
    """主函数"""
    from src.config import config
    
    # 设置系统编码为 UTF-8 (不清除控制台输出)
    if sys.platform.startswith('win'):
        os.system("@chcp 65001 >nul")  # 使用 >nul 来隐藏输出而不清屏
    
    print("\n" + "="*50)
    print_status("配置管理系统启动中...", "info", "LAUNCH")
    print("-"*50)
    
    # 创建作业对象来管理子进程
    create_job_object()
    
    # 设置控制台关闭事件处理
    setup_console_control_handler()
    
    # 检查必要目录
    print_status("检查系统目录...", "info", "FILE")
    if not os.path.exists(os.path.join(ROOT_DIR, 'src/webui/templates')):
        print_status("错误：模板目录不存在！", "error", "CROSS")
        return
    print_status("系统目录检查完成", "success", "CHECK")
    
    # 检查配置文件
    print_status("检查配置文件...", "info", "CONFIG")
    if not os.path.exists(config.config_path):
        print_status("错误：配置文件不存在！", "error", "CROSS")
        return
    print_status("配置文件检查完成", "success", "CHECK")

    # 修改启动 Web 服务器的部分
    try:
        cli = sys.modules['flask.cli']
        if hasattr(cli, 'show_server_banner'):
            setattr(cli, 'show_server_banner', lambda *x: None)  # 禁用 Flask 启动横幅
    except (KeyError, AttributeError):
        pass
    
    host = '0.0.0.0'
    port = 8502
    
    print_status("正在启动Web服务...", "info", "INTERNET")
    print("-"*50)
    print_status("配置管理系统已就绪！", "success", "STAR_1")

    # 显示所有可用的访问地址
    print_status("可通过以下地址访问:", "info", "CHAIN")
    print(f"  Local:   http://localhost:{port}")
    print(f"  Local:   http://127.0.0.1:{port}")
    
    # 获取本地IP地址
    hostname = socket.gethostname()
    try:
        addresses = socket.getaddrinfo(hostname, None)
        for addr in addresses:
            ip = addr[4][0]
            if isinstance(ip, str) and '.' in ip and ip != '127.0.0.1':
                print(f"  Network: http://{ip}:{port}")
    except Exception as e:
        logger.error(f"获取IP地址失败: {str(e)}")
        
    print("="*50 + "\n")
    
    # 启动浏览器
    open_browser(port)
    
    app.run(
        host=host, 
        port=port, 
        debug=True,
        use_reloader=False  # 禁用重载器以避免创建多余的进程
    )

@app.route('/install_dependencies', methods=['POST'])
def install_dependencies():
    """安装依赖"""
    try:
        output = []
        
        # 安装依赖
        output.append("正在安装依赖，请耐心等待...")
        requirements_path = os.path.join(ROOT_DIR, 'requirements.txt')
        
        if not os.path.exists(requirements_path):
            return jsonify({
                'status': 'error',
                'message': '找不到requirements.txt文件'
            })
            
        process = subprocess.Popen(
            [sys.executable, '-m', 'pip', 'install', '-r', requirements_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        
        # 解码字节数据为字符串
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')
        
        output.append(stdout if stdout else stderr)
        
        # 检查是否有实际错误，而不是"already satisfied"消息
        has_error = process.returncode != 0 and not any(
            msg in (stdout + stderr).lower() 
            for msg in ['already satisfied', 'successfully installed']
        )
        
        if not has_error:
            return jsonify({
                'status': 'success',
                'output': '\n'.join(output)
            })
        else:
            return jsonify({
                'status': 'error',
                'output': '\n'.join(output),
                'message': '安装依赖失败'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

def hash_password(password: str) -> str:
    # 对密码进行哈希处理
    return hashlib.sha256(password.encode()).hexdigest()

def is_local_network() -> bool:
    # 检查是否是本地网络访问
    client_ip = request.remote_addr
    if client_ip is None:
        return True
    return (
        client_ip == '127.0.0.1' or 
        client_ip.startswith('192.168.') or 
        client_ip.startswith('10.') or 
        client_ip.startswith('172.16.')
    )

@app.before_request
def check_auth():
    # 请求前验证登录状态
    # 排除不需要验证的路由
    public_routes = ['login', 'static', 'init_password']
    if request.endpoint in public_routes:
        return
        
    # 检查是否需要初始化密码
    from src.config import config
    if not config.auth.admin_password:
        return redirect(url_for('init_password'))
        
    # 如果是本地网络访问，自动登录
    if is_local_network():
        session['logged_in'] = True
        return
        
    if not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 处理登录请求
    from src.config import config
    
    # 首先检查是否需要初始化密码
    if not config.auth.admin_password:
        return redirect(url_for('init_password'))
    
    if request.method == 'GET':
        # 如果已经登录，直接跳转到仪表盘
        if session.get('logged_in'):
            return redirect(url_for('dashboard'))
            
        # 如果是本地网络访问，自动登录并重定向到仪表盘
        if is_local_network():
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
            
        return render_template('login.html')
    
    # POST请求处理
    data = request.get_json()
    password = data.get('password')
    remember_me = data.get('remember_me', False)
    
    # 正常登录验证
    stored_hash = config.auth.admin_password
    if hash_password(password) == stored_hash:
        session.clear()  # 清除旧会话
        session['logged_in'] = True
        if remember_me:
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=30)
        return jsonify({'status': 'success'})
    
    return jsonify({
        'status': 'error',
        'message': '密码错误'
    })

@app.route('/init_password', methods=['GET', 'POST'])
def init_password():
    # 初始化管理员密码页面
    from src.config import config
    
    if request.method == 'GET':
        # 如果已经设置了密码，重定向到登录页面
        if config.auth.admin_password:
            return redirect(url_for('login'))
        return render_template('init_password.html')
        
    # POST请求处理
    try:
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({
                'status': 'error',
                'message': '无效的请求数据'
            })
            
        password = data.get('password')
        
        # 再次检查是否已经设置了密码
        if config.auth.admin_password:
            return jsonify({
                'status': 'error',
                'message': '密码已经设置'
            })
        
        # 保存新密码的哈希值
        hashed_password = hash_password(password)
        if config.update_password(hashed_password):
            # 重新加载配置
            importlib.reload(sys.modules['src.config'])
            from src.config import config
            
            # 验证密码是否正确保存
            if not config.auth.admin_password:
                return jsonify({
                    'status': 'error',
                    'message': '密码保存失败'
                })
            
            # 设置登录状态
            session.clear()
            session['logged_in'] = True
            return jsonify({'status': 'success'})
        
        return jsonify({
            'status': 'error',
            'message': '保存密码失败'
        })
        
    except Exception as e:
        logger.error(f"初始化密码失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/logout')
def logout():
    # 退出登录
    session.clear()
    return redirect(url_for('login'))

@app.route('/get_model_configs')
def get_model_configs():
    """获取模型和API配置"""
    try:
        models_path = os.path.join(ROOT_DIR, 'src/config/models.json')
        
        if not os.path.exists(models_path):
            return jsonify({
                'status': 'error',
                'message': '配置文件不存在'
            })

        with open(models_path, 'r', encoding='utf-8') as f:
            configs = json.load(f)


        # 过滤和排序提供商
        active_providers = [p for p in configs['api_providers'] 
                          if p.get('status') == 'active']
        active_providers.sort(key=lambda x: x.get('priority', 999))
        
        # 构建返回配置
        return_configs = {
            'api_providers': active_providers,
            'models': {}
        }
        
        # 只包含活动模型
        for provider in active_providers:
            provider_id = provider['id']
            if provider_id in configs['models']:
                return_configs['models'][provider_id] = [
                    m for m in configs['models'][provider_id]
                    if m.get('status') == 'active'
                ]

        return jsonify(return_configs)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/save_quick_setup', methods=['POST'])
def save_quick_setup():
    """保存快速设置"""
    try:
        new_config = request.json or {}
        from src.config import config
        
        # 读取当前配置
        config_path = os.path.join(ROOT_DIR, 'src/config/config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
        except:
            current_config = {"categories": {}}
            
        # 确保基本结构存在
        if "categories" not in current_config:
            current_config["categories"] = {}
            
        # 更新用户设置
        if "listen_list" in new_config:
            if "user_settings" not in current_config["categories"]:
                current_config["categories"]["user_settings"] = {
                    "title": "用户设置",
                    "settings": {}
                }
            current_config["categories"]["user_settings"]["settings"]["listen_list"] = {
                "value": new_config["listen_list"],
                "type": "array",
                "description": "要监听的用户列表（请使用微信昵称，不要使用备注名）"
            }
            
        # 更新API设置
        if "api_key" in new_config:
            if "llm_settings" not in current_config["categories"]:
                current_config["categories"]["llm_settings"] = {
                    "title": "大语言模型配置",
                    "settings": {}
                }
            current_config["categories"]["llm_settings"]["settings"]["api_key"] = {
                "value": new_config["api_key"],
                "type": "string",
                "description": "API密钥",
                "is_secret": True
            }
            
            # 如果没有设置其他必要的LLM配置，设置默认值
            if "base_url" not in current_config["categories"]["llm_settings"]["settings"]:
                current_config["categories"]["llm_settings"]["settings"]["base_url"] = {
                    "value": "https://api.moonshot.cn/v1",
                    "type": "string",
                    "description": "API基础URL"
                }
            if "model" not in current_config["categories"]["llm_settings"]["settings"]:
                current_config["categories"]["llm_settings"]["settings"]["model"] = {
                    "value": "moonshot-v1-8k",
                    "type": "string",
                    "description": "使用的模型"
                }
            if "max_tokens" not in current_config["categories"]["llm_settings"]["settings"]:
                current_config["categories"]["llm_settings"]["settings"]["max_tokens"] = {
                    "value": 2000,
                    "type": "number",
                    "description": "最大token数"
                }
            if "temperature" not in current_config["categories"]["llm_settings"]["settings"]:
                current_config["categories"]["llm_settings"]["settings"]["temperature"] = {
                    "value": 1.1,
                    "type": "number",
                    "description": "温度参数"
                }
        
        # 保存更新后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=4)
            
        # 重新加载配置
        importlib.reload(sys.modules['src.config'])
        
        return jsonify({"status": "success", "message": "设置已保存"})
            
    except Exception as e:
        logger.error(f"保存快速设置失败: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/quick_setup')
def quick_setup():
    """快速设置页面"""
    return render_template('quick_setup.html')

# 添加获取可用人设列表的路由
@app.route('/get_available_avatars')
def get_available_avatars_route():
    """获取可用的人设目录列表"""
    try:
        # 使用绝对路径
        avatar_base_dir = os.path.join(ROOT_DIR, "data", "avatars")
        
        # 检查目录是否存在
        if not os.path.exists(avatar_base_dir):
            # 尝试创建目录
            try:
                os.makedirs(avatar_base_dir)
                logger.info(f"已创建人设目录: {avatar_base_dir}")
            except Exception as e:
                logger.error(f"创建人设目录失败: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f"人设目录不存在且无法创建: {str(e)}"
                })
        
        # 获取所有包含 avatar.md 和 emojis 目录的有效人设目录
        avatars = []
        for item in os.listdir(avatar_base_dir):
            avatar_dir = os.path.join(avatar_base_dir, item)
            if os.path.isdir(avatar_dir):
                avatar_md_path = os.path.join(avatar_dir, "avatar.md")
                emojis_dir = os.path.join(avatar_dir, "emojis")
                
                # 检查 avatar.md 文件
                if not os.path.exists(avatar_md_path):
                    logger.warning(f"人设 {item} 缺少 avatar.md 文件")
                    continue
                
                # 检查 emojis 目录
                if not os.path.exists(emojis_dir):
                    logger.warning(f"人设 {item} 缺少 emojis 目录")
                    try:
                        os.makedirs(emojis_dir)
                        logger.info(f"已为人设 {item} 创建 emojis 目录")
                    except Exception as e:
                        logger.error(f"为人设 {item} 创建 emojis 目录失败: {str(e)}")
                        continue
                
                avatars.append(f"data/avatars/{item}")
        
        logger.info(f"找到 {len(avatars)} 个有效人设: {avatars}")
        
        return jsonify({
            'status': 'success',
            'avatars': avatars
        })
    except Exception as e:
        logger.error(f"获取人设列表失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

# 修改加载指定人设内容的路由
@app.route('/load_avatar_content')
def load_avatar_content():
    """加载指定人设的内容"""
    try:
        avatar_name = request.args.get('avatar', 'MONO')
        avatar_path = os.path.join(ROOT_DIR, 'data', 'avatars', avatar_name, 'avatar.md')
        
        # 确保目录存在
        os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
        
        # 如果文件不存在，创建一个空文件
        if not os.path.exists(avatar_path):
            with open(avatar_path, 'w', encoding='utf-8') as f:
                f.write("# Task\n请在此输入任务描述\n\n# Role\n请在此输入角色设定\n\n# Appearance\n请在此输入外表描述\n\n")
        
        # 读取角色设定文件并解析内容
        sections = {}
        current_section = None
        
        with open(avatar_path, 'r', encoding='utf-8') as file:
            content = ""
            for line in file:
                if line.startswith('# '):
                    # 如果已有部分，保存它
                    if current_section:
                        sections[current_section.lower()] = content.strip()
                    # 开始新部分
                    current_section = line[2:].strip()
                    content = ""
                else:
                    content += line
            
            # 保存最后一个部分
            if current_section:
                sections[current_section.lower()] = content.strip()
        
        # 获取原始文件内容，用于前端显示
        with open(avatar_path, 'r', encoding='utf-8') as file:
            raw_content = file.read()
        
        return jsonify({
            'status': 'success',
            'content': sections,
            'raw_content': raw_content  # 添加原始内容
        })
    except Exception as e:
        logger.error(f"加载人设内容失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    """获取定时任务列表"""
    try:
        config_data = load_config_file()
        
        tasks = []
        if 'categories' in config_data and 'schedule_settings' in config_data['categories']:
            if 'settings' in config_data['categories']['schedule_settings'] and 'tasks' in config_data['categories']['schedule_settings']['settings']:
                tasks = config_data['categories']['schedule_settings']['settings']['tasks'].get('value', [])
        
        return jsonify({
            'status': 'success',
            'tasks': tasks
        })
    except Exception as e:
        logger.error(f"获取任务失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/save_task', methods=['POST'])
def save_task():
    """保存单个定时任务"""
    try:
        task_data = request.json
        
        # 验证必要字段
        required_fields = ['task_id', 'chat_id', 'content', 'schedule_type', 'schedule_time']
        for field in required_fields:
            if field not in task_data:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要字段: {field}'
                })
        
        # 读取配置
        config_data = load_config_file()
        
        # 确保必要的配置结构存在
        if 'categories' not in config_data:
            config_data['categories'] = {}
        
        if 'schedule_settings' not in config_data['categories']:
            config_data['categories']['schedule_settings'] = {
                'title': '定时任务配置',
                'settings': {
                    'tasks': {
                        'value': [],
                        'type': 'array',
                        'description': '定时任务列表'
                    }
                }
            }
        elif 'settings' not in config_data['categories']['schedule_settings']:
            config_data['categories']['schedule_settings']['settings'] = {
                'tasks': {
                    'value': [],
                    'type': 'array',
                    'description': '定时任务列表'
                }
            }
        elif 'tasks' not in config_data['categories']['schedule_settings']['settings']:
            config_data['categories']['schedule_settings']['settings']['tasks'] = {
                'value': [],
                'type': 'array',
                'description': '定时任务列表'
            }
        
        # 获取当前任务列表
        tasks = config_data['categories']['schedule_settings']['settings']['tasks']['value']
        
        # 检查是否存在相同ID的任务
        task_index = None
        for i, task in enumerate(tasks):
            if task.get('task_id') == task_data['task_id']:
                task_index = i
                break
        
        # 更新或添加任务
        if task_index is not None:
            tasks[task_index] = task_data
        else:
            tasks.append(task_data)
        
        # 更新配置
        config_data['categories']['schedule_settings']['settings']['tasks']['value'] = tasks
        
        # 保存配置
        if not save_config_file(config_data):
            return jsonify({
                'status': 'error',
                'message': '保存配置文件失败'
            }), 500
        
        # 重新初始化定时任务
        reinitialize_tasks()
        
        return jsonify({
            'status': 'success',
            'message': '任务已保存'
        })
    except Exception as e:
        logger.error(f"保存任务失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/delete_task', methods=['POST'])
def delete_task():
    """删除定时任务"""
    try:
        data = request.json
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({
                'status': 'error',
                'message': '未提供任务ID'
            })
        
        # 读取配置
        config_data = load_config_file()
        
        # 获取任务列表
        if 'categories' in config_data and 'schedule_settings' in config_data['categories']:
            if 'settings' in config_data['categories']['schedule_settings'] and 'tasks' in config_data['categories']['schedule_settings']['settings']:
                tasks = config_data['categories']['schedule_settings']['settings']['tasks']['value']
                
                # 查找并删除任务
                new_tasks = [task for task in tasks if task.get('task_id') != task_id]
                
                # 更新配置
                config_data['categories']['schedule_settings']['settings']['tasks']['value'] = new_tasks
                
                # 保存配置
                if not save_config_file(config_data):
                    return jsonify({
                        'status': 'error',
                        'message': '保存配置文件失败'
                    }), 500
                
                # 重新初始化定时任务
                reinitialize_tasks()
                
                return jsonify({
                    'status': 'success',
                    'message': '任务已删除'
                })
        
        return jsonify({
            'status': 'error',
            'message': '找不到任务配置'
        })
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/get_all_configs')
def get_all_configs():
    """获取所有最新的配置数据"""
    try:
        # 直接从配置文件读取所有配置数据
        config_path = os.path.join(ROOT_DIR, 'src/config/config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 解析配置数据为前端需要的格式
        configs = {}
        tasks = []
        
        # 处理用户设置
        if 'categories' in config_data:
            # 用户设置
            if 'user_settings' in config_data['categories'] and 'settings' in config_data['categories']['user_settings']:
                configs['基础配置'] = {}
                if 'listen_list' in config_data['categories']['user_settings']['settings']:
                    configs['基础配置']['LISTEN_LIST'] = config_data['categories']['user_settings']['settings']['listen_list']
            
            # LLM设置
            if 'llm_settings' in config_data['categories'] and 'settings' in config_data['categories']['llm_settings']:
                llm_settings = config_data['categories']['llm_settings']['settings']
                if 'api_key' in llm_settings:
                    configs['基础配置']['DEEPSEEK_API_KEY'] = llm_settings['api_key']
                if 'base_url' in llm_settings:
                    configs['基础配置']['DEEPSEEK_BASE_URL'] = llm_settings['base_url']
                if 'model' in llm_settings:
                    configs['基础配置']['MODEL'] = llm_settings['model']
                if 'max_tokens' in llm_settings:
                    configs['基础配置']['MAX_TOKEN'] = llm_settings['max_tokens']
                if 'temperature' in llm_settings:
                    configs['基础配置']['TEMPERATURE'] = llm_settings['temperature']
            
            # 媒体设置
            if 'media_settings' in config_data['categories'] and 'settings' in config_data['categories']['media_settings']:
                media_settings = config_data['categories']['media_settings']['settings']
                
                # 图像识别设置
                configs['图像识别API配置'] = {}
                if 'image_recognition' in media_settings:
                    img_recog = media_settings['image_recognition']
                    if 'api_key' in img_recog:
                        # 保留完整配置，包括元数据
                        configs['图像识别API配置']['VISION_API_KEY'] = img_recog['api_key']
                    if 'base_url' in img_recog:
                        configs['图像识别API配置']['VISION_BASE_URL'] = img_recog['base_url']
                    if 'temperature' in img_recog:
                        configs['图像识别API配置']['VISION_TEMPERATURE'] = img_recog['temperature']
                    if 'model' in img_recog:
                        configs['图像识别API配置']['VISION_MODEL'] = img_recog['model']
                
                # 图像生成设置
                '''
                configs['图像生成配置'] = {}
                if 'image_generation' in media_settings:
                    img_gen = media_settings['image_generation']
                    if 'model' in img_gen:
                        configs['图像生成配置']['IMAGE_MODEL'] = {'value': img_gen['model'].get('value', '')}
                    if 'temp_dir' in img_gen:
                        configs['图像生成配置']['TEMP_IMAGE_DIR'] = {'value': img_gen['temp_dir'].get('value', '')}
                '''
                
                # 语音设置
                '''
                configs['语音配置'] = {}
                if 'text_to_speech' in media_settings:
                    tts = media_settings['text_to_speech']
                    if 'tts_api_url' in tts:
                        configs['语音配置']['TTS_API_URL'] = {'value': tts['tts_api_url'].get('value', '')}
                    if 'voice_dir' in tts:
                        configs['语音配置']['VOICE_DIR'] = {'value': tts['voice_dir'].get('value', '')}
                '''
            
            # 行为设置
            if 'behavior_settings' in config_data['categories'] and 'settings' in config_data['categories']['behavior_settings']:
                behavior = config_data['categories']['behavior_settings']['settings']
                
                # 时间配置
                configs['时间配置'] = {}
                if 'auto_message' in behavior:
                    auto_msg = behavior['auto_message']
                    if 'content' in auto_msg:
                        configs['时间配置']['AUTO_MESSAGE'] = auto_msg['content']
                    if 'countdown' in auto_msg:
                        if 'min_hours' in auto_msg['countdown']:
                            configs['时间配置']['MIN_COUNTDOWN_HOURS'] = auto_msg['countdown']['min_hours']
                        if 'max_hours' in auto_msg['countdown']:
                            configs['时间配置']['MAX_COUNTDOWN_HOURS'] = auto_msg['countdown']['max_hours']
                
                if 'quiet_time' in behavior:
                    quiet = behavior['quiet_time']
                    if 'start' in quiet:
                        configs['时间配置']['QUIET_TIME_START'] = quiet['start']
                    if 'end' in quiet:
                        configs['时间配置']['QUIET_TIME_END'] = quiet['end']
                
                # Prompt配置
                configs['Prompt配置'] = {}
                if 'context' in behavior:
                    context = behavior['context']
                    if 'max_groups' in context:
                        configs['Prompt配置']['MAX_GROUPS'] = context['max_groups']
                    if 'avatar_dir' in context:
                        configs['Prompt配置']['AVATAR_DIR'] = context['avatar_dir']
            
            # 定时任务
            if 'schedule_settings' in config_data['categories'] and 'settings' in config_data['categories']['schedule_settings']:
                if 'tasks' in config_data['categories']['schedule_settings']['settings']:
                    tasks = config_data['categories']['schedule_settings']['settings']['tasks'].get('value', [])
        
        logger.debug(f"获取到的所有配置数据: {configs}")
        logger.debug(f"获取到的任务数据: {tasks}")
        
        return jsonify({
            'status': 'success',
            'configs': configs,
            'tasks': tasks
        })
    except Exception as e:
        logger.error(f"获取所有配置数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/get_announcement')
def get_announcement():
    try:
        # 使用全局定义的模板文件路径
        announcement_file = ANNOUNCEMENT_CONFIG_PATH
        
        # 公告文件不存在时，直接返回一个空公告，不创建文件
        if not os.path.exists(announcement_file):
            return jsonify({
                'enabled': False,
                'title': '系统公告',
                'content': ''
            })
        
        # 读取公告文件
        with open(announcement_file, 'r', encoding='utf-8') as f:
            announcement = json.load(f)
        
        # 读取version.json文件内容并添加到公告中
        version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'version.json')
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    version_info = json.load(f)
                
                # 获取版本信息
                version = version_info.get('version', '未知')
                last_update = version_info.get('last_update', '未知')
                description = version_info.get('description', [])
                
                # 将版本信息添加到公告内容中
                version_html = f"""
                <div class="mt-4 pt-3 border-top">
                    <h5 class="mb-3">当前版本信息</h5>
                    <p><strong>版本号:</strong> {version}</p>
                    <p><strong>更新日期:</strong> {last_update}</p>
                    <p><strong>更新内容:</strong></p>
                """
                
                if isinstance(description, list):
                    version_html += "<ul class='ps-3'>"
                    for item in description:
                        version_html += f"<li>{item}</li>"
                    version_html += "</ul>"
                else:
                    version_html += f"<p>{description}</p>"
                
                version_html += "</div>"
                
                # 将版本信息附加到原有公告内容
                # 简单地附加版本信息，无论是HTML还是纯文本
                announcement['content'] += version_html
            except Exception as e:
                print(f"获取版本信息时发生错误: {e}")
            
        return jsonify(announcement)
    except Exception as e:
        print(f"获取公告时发生错误: {e}")
        return jsonify({
            'enabled': False,
            'title': '公告读取失败',
            'content': f'<div class="text-danger">错误信息: {str(e)}</div>'
        })

@app.route('/reconnect_wechat')
def reconnect_wechat():
    try:
        # 导入微信登录点击器
        from src.Wechat_Login_Clicker.Wechat_Login_Clicker import click_wechat_buttons
        
        # 执行点击操作
        result = click_wechat_buttons()
        
        if result is False:
            return jsonify({
                'status': 'error',
                'message': '找不到微信登录窗口'
            })
        
        return jsonify({
            'status': 'success',
            'message': '微信重连操作已执行'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'微信重连失败: {str(e)}'
        })

@app.route('/get_vision_api_configs')
def get_vision_api_configs():
    """获取图像识别API配置"""
    try:
        # 构建图像识别API提供商列表
        vision_providers = [
            {
                "id": "kourichat-asia",
                "name": "KouriChat API (推荐)",
                "url": "https://api.kourichat.com/v1",
                "register_url": "https://api.kourichat.com/register",
                "status": "active",
                "priority": 1
            },
            {
                "id": "moonshot",
                "name": "Moonshot（月之暗面）",
                "url": "https://api.moonshot.cn/v1",
                "register_url": "https://platform.moonshot.cn/console/api-keys",
                "status": "active",
                "priority": 2
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "url": "https://api.openai.com/v1",
                "register_url": "https://platform.openai.com/api-keys",
                "status": "active",
                "priority": 3
            },
        ]
        
        # 构建模型配置 - 只包含支持图像识别的模型
        vision_models = {
            "kourichat-asia": [
                {"id": "kourichat-vision", "name": "kourichat-vision"},
                {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
                {"id": "gpt-4o", "name": "GPT-4o"}
            ],
            "moonshot": [
                {"id": "moonshot-v1-8k-vision-preview", "name": "moonshot-v1-8k-vision-preview"}
            ]
        }
        
        return jsonify({
            "status": "success",
            "api_providers": vision_providers,
            "models": vision_models
        })
    except Exception as e:
        logger.error(f"获取图像识别API配置失败: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        })

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_status("正在关闭服务...", "warning", "STOP")
        cleanup_processes()
        print_status("配置管理系统已停止", "info", "BYE")
        print("\n")
    except Exception as e:
        print_status(f"系统错误: {str(e)}", "error", "ERROR")
        cleanup_processes()


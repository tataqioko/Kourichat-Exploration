import os
import shutil
import json
from flask import Blueprint, jsonify, request
from pathlib import Path
from datetime import datetime

avatar_bp = Blueprint('avatar', __name__)

AVATARS_DIR = Path('data/avatars')

def parse_md_content(content):
    """解析markdown内容为字典格式"""
    sections = {
        '任务': 'task',
        '角色': 'role',
        '外表': 'appearance',
        '经历': 'experience',
        '性格': 'personality',
        '经典台词': 'classic_lines',
        '喜好': 'preferences',
        '备注': 'notes'
    }
    
    result = {v: '' for v in sections.values()}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('# '):
            if current_section and current_content:
                result[sections.get(current_section, 'notes')] = '\n'.join(current_content)
                current_content = []
            
            current_section = line[2:].strip()
            continue
            
        if current_section:
            current_content.append(line)
    
    # 处理最后一个部分
    if current_section and current_content:
        result[sections.get(current_section, 'notes')] = '\n'.join(current_content)
    
    return result

@avatar_bp.route('/get_available_avatars')
def get_available_avatars():
    """获取所有可用的人设列表"""
    try:
        if not AVATARS_DIR.exists():
            return jsonify({'status': 'success', 'avatars': []})
            
        avatars = [d.name for d in AVATARS_DIR.iterdir() if d.is_dir()]
        return jsonify({'status': 'success', 'avatars': avatars})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/load_avatar_content')
def load_avatar_content():
    """加载指定人设的内容"""
    avatar = request.args.get('avatar')
    if not avatar:
        return jsonify({'status': 'error', 'message': '未指定人设名称'})
        
    try:
        avatar_dir = AVATARS_DIR / avatar
        avatar_file = avatar_dir / 'avatar.md'
        
        if not avatar_file.exists():
            return jsonify({'status': 'error', 'message': '人设文件不存在'})
            
        with open(avatar_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        parsed_content = parse_md_content(content)
        return jsonify({
            'status': 'success',
            'content': parsed_content,
            'raw_content': content
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/create_avatar', methods=['POST'])
def create_avatar():
    """创建新的人设"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar_name')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供人设名称'})
            
        # 创建人设目录
        avatar_dir = AVATARS_DIR / avatar_name
        if avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '该人设已存在'})
            
        # 创建目录结构
        avatar_dir.mkdir(parents=True)
        (avatar_dir / 'emojis').mkdir()
        
        # 创建avatar.md文件
        avatar_file = avatar_dir / 'avatar.md'
        template = """# 任务
请在此处描述角色的任务和目标

# 角色
请在此处描述角色的基本信息

# 外表
请在此处描述角色的外表特征

# 经历
请在此处描述角色的经历和背景故事

# 性格
请在此处描述角色的性格特点

# 经典台词
请在此处列出角色的经典台词

# 喜好
请在此处描述角色的喜好

# 备注
其他需要补充的信息
"""
        with open(avatar_file, 'w', encoding='utf-8') as f:
            f.write(template)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/delete_avatar', methods=['POST'])
def delete_avatar():
    """删除人设"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar_name')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供人设名称'})
            
        avatar_dir = AVATARS_DIR / avatar_name
        if not avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '人设不存在'})
            
        # 删除整个人设目录
        shutil.rmtree(avatar_dir)
        return jsonify({'status': 'success', 'message': '人设已删除'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/save_avatar', methods=['POST'])
def save_avatar():
    """保存人设设定"""
    data = request.get_json()
    avatar_name = data.get('avatar')
    
    if not avatar_name:
        return jsonify({'status': 'error', 'message': '未提供人设名称'})
        
    try:
        avatar_dir = AVATARS_DIR / avatar_name
        avatar_file = avatar_dir / 'avatar.md'
        
        if not avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '人设目录不存在'})
            
        # 构建markdown内容
        content = f"""# 任务
{data.get('task', '')}

# 角色
{data.get('role', '')}

# 外表
{data.get('appearance', '')}

# 经历
{data.get('experience', '')}

# 性格
{data.get('personality', '')}

# 经典台词
{data.get('classic_lines', '')}

# 喜好
{data.get('preferences', '')}

# 备注
{data.get('notes', '')}
"""
        # 保存文件
        with open(avatar_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/save_avatar_raw', methods=['POST'])
def save_avatar_raw():
    """保存原始Markdown内容"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar')
        content = data.get('content')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供人设名称'})
            
        if content is None:
            return jsonify({'status': 'error', 'message': '未提供内容'})
            
        avatar_dir = AVATARS_DIR / avatar_name
        avatar_file = avatar_dir / 'avatar.md'
        
        if not avatar_dir.exists():
            return jsonify({'status': 'error', 'message': '人设目录不存在'})
            
        # 保存原始内容
        with open(avatar_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/load_core_memory')
def load_core_memory():
    """加载角色的核心记忆内容"""
    try:
        avatar_name = request.args.get('avatar')
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供角色名称'})
            
        memory_path = AVATARS_DIR / avatar_name / 'memory' / 'core_memory.json'
        
        # 如果记忆文件不存在，则返回空内容
        if not memory_path.exists():
            # 创建记忆目录
            memory_dir = AVATARS_DIR / avatar_name / 'memory'
            memory_dir.mkdir(exist_ok=True)
            
            # 创建空的核心记忆文件
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "content": ""}, f, ensure_ascii=False, indent=2)
            
            return jsonify({'status': 'success', 'content': ''})
            
        # 读取核心记忆文件
        with open(memory_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            content = data.get('content', '')
            
        return jsonify({'status': 'success', 'content': content})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/save_core_memory', methods=['POST'])
def save_core_memory():
    """保存角色的核心记忆内容"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar')
        content = data.get('content', '')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供角色名称'})
            
        # 确保记忆目录存在
        memory_dir = AVATARS_DIR / avatar_name / 'memory'
        memory_dir.mkdir(exist_ok=True)
        
        memory_path = memory_dir / 'core_memory.json'
        
        # 保存核心记忆
        memory_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": content
        }
        
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/load_short_memory')
def load_short_memory():
    """加载角色的短期记忆内容"""
    try:
        avatar_name = request.args.get('avatar')
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供角色名称'})
            
        memory_path = AVATARS_DIR / avatar_name / 'memory' / 'short_memory.json'
        
        # 如果记忆文件不存在，则返回空内容
        if not memory_path.exists():
            # 创建记忆目录
            memory_dir = AVATARS_DIR / avatar_name / 'memory'
            memory_dir.mkdir(exist_ok=True)
            
            # 创建空的短期记忆文件
            with open(memory_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            
            return jsonify({'status': 'success', 'conversations': []})
            
        # 读取短期记忆文件
        with open(memory_path, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
            
        return jsonify({'status': 'success', 'conversations': conversations})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/save_short_memory', methods=['POST'])
def save_short_memory():
    """保存角色的短期记忆内容"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar')
        conversations = data.get('conversations', [])
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供角色名称'})
            
        # 确保记忆目录存在
        memory_dir = AVATARS_DIR / avatar_name / 'memory'
        memory_dir.mkdir(exist_ok=True)
        
        memory_path = memory_dir / 'short_memory.json'
        
        # 保存短期记忆
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@avatar_bp.route('/clear_short_memory', methods=['POST'])
def clear_short_memory():
    """清空角色的短期记忆内容"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供角色名称'})
            
        # 确保记忆目录存在
        memory_dir = AVATARS_DIR / avatar_name / 'memory'
        memory_dir.mkdir(exist_ok=True)
        
        memory_path = memory_dir / 'short_memory.json'
        
        # 清空短期记忆
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# 添加清空核心记忆的路由
@avatar_bp.route('/clear_core_memory', methods=['POST'])
def clear_core_memory():
    """清空角色的核心记忆内容"""
    try:
        data = request.get_json()
        avatar_name = data.get('avatar')
        
        if not avatar_name:
            return jsonify({'status': 'error', 'message': '未提供角色名称'})
            
        # 确保记忆目录存在
        memory_dir = AVATARS_DIR / avatar_name / 'memory'
        memory_dir.mkdir(exist_ok=True)
        
        memory_path = memory_dir / 'core_memory.json'
        
        # 清空核心记忆，但保留文件结构
        memory_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": ""
        }
        
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}) 
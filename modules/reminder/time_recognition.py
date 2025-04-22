"""
时间识别服务
负责识别消息中的时间信息和提醒意图
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Tuple

# 使用main日志器
logger = logging.getLogger('main')

class TimeRecognitionService:
    def __init__(self, llm_service):
        """
        初始化时间识别服务
        Args:
            llm_service: LLM服务实例，用于时间识别
        """
        self.llm_service = llm_service
        
        # 从文件读取提示词
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        prompt_path = os.path.join(root_dir, "data", "base", "reminder.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read().strip()

    def recognize_time(self, message: str) -> Optional[List[Tuple[datetime, str]]]:
        """
        识别消息中的时间信息，支持多个提醒
        Args:
            message: 用户消息
        Returns:
            Optional[list]: [(目标时间, 提醒内容), ...] 或 None
        """
        current_time = datetime.now()
        user_prompt = f"""当前时间是：{current_time.strftime('%Y-%m-%d %H:%M:%S')}
请严格按照JSON格式分析这条消息中的提醒请求：{message}"""
        
        response = self.llm_service.get_response(
            message=user_prompt,
            system_prompt=self.system_prompt,
            user_id="time_recognition_system"
        )

        # 如果没有有效响应或明确不是时间相关
        if not response or response == "NOT_TIME_RELATED":
            return None

        # 提取和解析JSON
        try:
            # 清理响应
            response = ' '.join(response.split())
            start = response.find('{')
            end = response.rfind('}')
            
            # 检查是否找到了有效的JSON边界
            if start == -1 or end == -1 or start >= end:
                logger.debug(f"响应中未找到有效的JSON: {response[:100]}...")
                return None
                
            json_str = response[start:end + 1]
            
            # 解析JSON
            result = json.loads(json_str)
            
            # 提取提醒信息
            if "reminders" not in result or not isinstance(result["reminders"], list):
                return None
                
            reminders = []
            for reminder in result["reminders"]:
                if not isinstance(reminder, dict):
                    continue
                    
                if "target_time" not in reminder or "reminder_content" not in reminder:
                    continue
                    
                target_time = datetime.strptime(
                    reminder["target_time"], 
                    "%Y-%m-%d %H:%M:%S"
                )
                reminders.append((target_time, reminder["reminder_content"]))
                
            return reminders if reminders else None
            
        except Exception as e:
            logger.error(f"处理时间识别响应失败: {str(e)}")
            logger.debug(f"错误的响应内容: {response[:200]}...")
            return None

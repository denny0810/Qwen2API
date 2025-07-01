import os
import random

# 从当前目录下的 qwen2api.env 文件加载环境变量
from dotenv import load_dotenv
load_dotenv(dotenv_path='qwen2api.env')

# API配置
TARGET_API_URL = 'https://chat.qwen.ai/api/chat/completions'
MODELS_API_URL = 'https://chat.qwen.ai/api/models'
DEFAULT_COOKIE_VALUE = 'ssxmod_itna=YqjxyiDQDtKQu4iqYQiQGCDce=SqAjeDXDUMqiQGgDYq7=GFKDCOtkajRYSB3odE4hYd02D5D/fmreDZDG9dDqx0orXKt3Axsa0mCiv3BCeou2PHQClrpctWvB7l3m=w9GY5+DCPGnDBIqqGqx+DiiTx0rD0eDPxDYDG+hDneDexDdNFEpN4GWTjR5Dl9sr4DaW4i3NIYDR=xD0gWsDQF3bIDDBpiXDrDej8OsU/r6DivqF9cwD7H3DlaKiv0w2KZnoAEp3ypf5pBAw40OD095N4ibVaLQbREf+Qie5=XYwQDrqCmqX=0KrYxZYNtiGAEQaDsOYqdYqeA4AEi+odyTeDDf+YIUY4+ehGY+0rUuEt9oqt+qBY5at4VED59GdY+YGR1nxUCxoQuQChdYeqlXxpDxD;'
COOKIE_VALUE = os.environ.get('COOKIE_VALUE',DEFAULT_COOKIE_VALUE)

# 默认不向服务器强制要求非流式响应
FORCE_NO_STREAM = os.environ.get('FORCE_NO_STREAM', '').upper() == 'TRUE'

# 默认不开启伪流式输出
PSEUDO_STREAM = os.environ.get('PSEUDO_STREAM', '').upper() == 'TRUE'

# 日志配置
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'error').upper()
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'logging_config.yaml')

# 服务器配置
HOST = '0.0.0.0'
PORT = 6060

# 全局变量，记录上一次选择的 Token
last_token = None  

# 获取认证令牌
def get_auth_token(auth_header):
    """从请求头或环境变量中获取认证令牌    
    Args:
        auth_header (str): The Authorization header from the request        
    Returns:
        tuple: A 3-element tuple containing:
            - str|None: The selected auth token if successful, None otherwise
            - str|None: Error message if authentication failed, None if successful
            - int|None: HTTP status code (401) if authentication failed, None if successful
            
        Possible return combinations:
            - (token, None, None): Authentication successful
            - (None, error_msg, 401): Invalid Authorization header format
            - (None, error_msg, 401): No valid tokens found
    """
    CHAT_AUTHORIZATION = os.environ.get('CHAT_AUTHORIZATION')
    token_list=[]
    # 优先尝试从请求头获取 token
    if auth_header and isinstance(auth_header, str) and auth_header.startswith('Bearer '):
        tokens = auth_header[7:].strip()  # 去掉 'Bearer ' 前缀并去除空格
    else:
         return None, '未找到有效的Authorization 请求头', 401
    if len(tokens) > 30:             # 简单校验 token 长度是否合理
            token_list = tokens.split(',')
    elif CHAT_AUTHORIZATION and isinstance(CHAT_AUTHORIZATION, str):
            token_list = CHAT_AUTHORIZATION.split(',')
    token_list = [t for t in token_list if t.strip()] #过滤无效空格
    if token_list:
        token = get_token_cached_random(token_list)
        return token, None, None        
    else:
        return None, '未找到有效token，请检查请求头的token或 CHAT_AUTHORIZATION 环境变量', 401



# 缓存随机生成
def get_token_cached_random(token_list):
    global last_token
    # 排除上一次使用的 Token（除非只剩它一个）
    available_tokens = [t for t in token_list if t != last_token] or token_list
    # 从剩余 Token 中随机选择一个
    tokenGet = random.choice(available_tokens)
    last_token = tokenGet  # 更新缓存
    return tokenGet

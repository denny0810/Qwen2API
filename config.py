import os
import random

# API配置
TARGET_API_URL = 'https://chat.qwen.ai/api/chat/completions'
MODELS_API_URL = 'https://chat.qwen.ai/api/models'
COOKIE_VALUE = 'ssxmod_itna=YqjxyiDQDtKQu4iqYQiQGCDce=SqAjeDXDUMqiQGgDYq7=GFKDCOtkajRYSB3odE4hYd02D5D/fmreDZDG9dDqx0orXKt3Axsa0mCiv3BCeou2PHQClrpctWvB7l3m=w9GY5+DCPGnDBIqqGqx+DiiTx0rD0eDPxDYDG+hDneDexDdNFEpN4GWTjR5Dl9sr4DaW4i3NIYDR=xD0gWsDQF3bIDDBpiXDrDej8OsU/r6DivqF9cwD7H3DlaKiv0w2KZnoAEp3ypf5pBAw40OD095N4ibVaLQbREf+Qie5=XYwQDrqCmqX=0KrYxZYNtiGAEQaDsOYqdYqeA4AEi+odyTeDDf+YIUY4+ehGY+0rUuEt9oqt+qBY5at4VED59GdY+YGR1nxUCxoQuQChdYeqlXxpDxD;'

# 日志配置
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'logging_config.yaml')

# 服务器配置
HOST = '0.0.0.0'
PORT = 6060

# 获取认证令牌
def get_auth_token(auth_header):
    """从请求头或环境变量中获取认证令牌"""
    CHAT_AUTHORIZATION = os.environ.get('CHAT_AUTHORIZATION')
    
    # 验证API key格式
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, '缺少或无效的API密钥格式', 401
    
    # 获取API key
    tokens = auth_header[7:]  # 去掉'Bearer '前缀
    if len(tokens) < 30:
        tokens = CHAT_AUTHORIZATION
    
    # 如果 tokens 仍然无效，返回错误
    if not tokens:
        return None, 'API密钥无效或环境变量未设置', 401
    
    try:
        # 分割密钥字符串并随机选择一个元素
        token_list = tokens.split(',')
        token = random.choice(token_list)
        return token, None, None
    except ValueError:
        # 处理无法分割或列表为空的情况
        return None, 'API密钥格式错误,无法分割', 401
from flask import Flask
import logging

from config import HOST, PORT, get_auth_token
from api.routes import chat_completions_route, models_route, index_route
from logger import setup_logging, start_log_cleaner

# 初始化日志
logger = setup_logging()

# 初始化Flask应用
app = Flask(__name__)

# 注册路由
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    return chat_completions_route(get_auth_token)

@app.route('/v1/models', methods=['GET'])
def list_models():
    return models_route()

@app.route('/', methods=['GET'])
def index():
    return index_route()

if __name__ == '__main__':
    # 启动日志清理线程
    log_cleaner = start_log_cleaner()
    logger.info("已启动日志清理线程")
    
    logger.info(f"正在 {PORT} 端口启动服务...")
    app.run(host=HOST, port=PORT)

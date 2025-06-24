import os
import logging
import logging.config
import datetime
import threading
import time
import glob
import yaml

from config import LOGS_DIR, CONFIG_PATH, LOG_LEVEL

# 确保logs文件夹存在
os.makedirs(LOGS_DIR, exist_ok=True)

# 获取当前日期作为日志文件名
def get_log_file():
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    return os.path.join(LOGS_DIR, f'{current_date}.log')

# 初始化日志配置
def setup_logging():
    # 获取当前日期作为日志文件名
    log_file = get_log_file()
    
    # 加载日志配置
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        # 更新日志文件路径
        for handler in config.get('handlers', {}).values():
            if 'filename' in handler:
                handler['filename'] = log_file
        
        # 根据环境变量设置日志级别
        if LOG_LEVEL == 'NONE':
            logging.disable(logging.CRITICAL + 1)  # 关闭日志记录
        else:
            config['loggers']['']['level'] = LOG_LEVEL
            for handler in config.get('handlers', {}).values():
                handler['level'] = LOG_LEVEL
        
        logging.config.dictConfig(config)
    
    # 获取日志记录器
    return logging.getLogger('qwen2api')

# 日志清理函数
def clean_old_logs():
    """
    定期清理旧日志文件，根据配置文件中的设置
    """
    logger = logging.getLogger('qwen2api')
    
    # 从配置文件中读取保留策略
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 获取日志保留策略配置
    retention_config = config.get('log_retention', {})
    days_to_keep = retention_config.get('days_to_keep', 30)
    check_interval_hours = retention_config.get('check_interval_hours', 24)
    
    logger.info(f"启动日志清理线程，保留最近{days_to_keep}天的日志，每{check_interval_hours}小时检查一次")
    
    while True:
        try:
            # 计算截止日期
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            # 获取所有日志文件
            log_files = glob.glob(os.path.join(LOGS_DIR, '*.log'))
            
            # 检查并删除旧文件
            deleted_count = 0
            for log_file in log_files:
                file_name = os.path.basename(log_file)
                # 尝试从文件名中提取日期
                try:
                    file_date_str = file_name.split('.')[0]  # 假设文件名格式为 YYYY-MM-DD.log
                    if file_date_str < cutoff_str:
                        os.remove(log_file)
                        deleted_count += 1
                        logger.info(f"已删除旧日志文件: {file_name}")
                except (IndexError, ValueError) as e:
                    logger.warning(f"无法解析日志文件名: {file_name}, 错误: {str(e)}")
            
            if deleted_count > 0:
                logger.info(f"日志清理完成，共删除了{deleted_count}个旧日志文件")
            else:
                logger.info(f"没有找到需要删除的旧日志文件")
                
            # 等待下一次检查
            time.sleep(check_interval_hours * 3600)
        except Exception as e:
            logger.error(f"日志清理过程中发生错误: {str(e)}")
            # 出错后等待一段时间再重试
            time.sleep(3600)

# 启动日志清理线程
def start_log_cleaner():
    log_cleaner = threading.Thread(target=clean_old_logs, daemon=True)
    log_cleaner.start()
    return log_cleaner
def format_cookie(converted_cookie):
    """将API密钥格式转换为cookie格式"""
    # 将冒号替换为分号
    original_format = converted_cookie.replace(':', ';')
    
    # 在每个分号后添加空格
    parts = original_format.split(';')
    result = '; '.join(parts)
    
    return result
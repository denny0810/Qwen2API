def format_cookie(converted_cookie):
    """
    将转换后的cookie格式（分号变成冒号且删除了空格）转换回原始格式
    （冒号转分号且在每个分号后添加空格）
    
    Args:
        converted_cookie (str): 转换后的cookie字符串
        
    Returns:
        str: 原始格式的cookie字符串
    """
    # 将冒号替换为分号
    original_format = converted_cookie.replace(':', ';')
    
    # 在每个分号后添加空格（除了最后一个）
    parts = original_format.split(';')
    result = '; '.join(parts)
    
    return result

def testmain():
    print("Cookie格式转换工具")
    print("将转换后的cookie（冒号分隔）转回原始格式（分号+空格分隔）")
    print("-" * 50)
    
    # 获取用户输入
    converted_cookie = input("请输入转换后的cookie（冒号分隔）：\n")
    
    # 转换格式
    original_cookie = format_cookie(converted_cookie)
    
    # 输出结果
    print("\n转换结果：")
    print("-" * 50)
    print(original_cookie)
    print("-" * 50)

if __name__ == "__main__":
    testmain()
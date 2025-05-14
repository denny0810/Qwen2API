import base64
import requests
from requests_toolbelt import MultipartEncoder

def base64_to_bytes(base64_image):
    # 提取 Base64 编码部分（去掉 data URL 的前缀）
    if ',' in base64_image:
        base64_data = base64_image.split(',', 1)[1]
    else:
        # 如果没有逗号分隔符，假设整个字符串都是 base64 数据
        base64_data = base64_image
    
    # 将 Base64 编码解码为二进制数据
    image_data = base64.b64decode(base64_data)
    return image_data

def upload_to_qwenlm(blob, token):
    url = "https://chat.qwenlm.ai/api/v1/files/"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    # 创建 MultipartEncoder 对象
    m = MultipartEncoder(
        fields={
            'file': ('image.png', blob, 'image/png')
        }
    )

    # 更新 headers 中的 Content-Type
    headers.update({'Content-Type': m.content_type})

    # 发送 POST 请求
    response = requests.post(url, headers=headers, data=m)

    # 检查响应
    if response.status_code == 200:
        upload_data = response.json()
        if 'id' not in upload_data:
            raise ValueError('File upload failed')
        return upload_data
    else:
        raise requests.exceptions.HTTPError(f'HTTP Error: {response.status_code}')

def upload_base64_image_to_qwenlm(base64_image, token):
    """
    将 Base64 格式的图片直接上传到 qwenlm
    
    参数:
        base64_image (str): Base64 格式的图片数据，包含前缀如 "data:image/png;base64,"
        token (str): 认证 token
        
    返回:
        dict: 上传成功后的响应数据，包含文件 ID
        
    异常:
        ValueError: 如果上传失败
        HTTPError: 如果 HTTP 请求失败
    """
    try:
        # 将 Base64 转换为二进制数据
        blob = base64_to_bytes(base64_image)
        # 上传二进制数据
        return upload_to_qwenlm(blob, token)
    except Exception as e:
        raise Exception(f"上传图片失败: {str(e)}")

def get_image_id_from_upload(upload_result):
    """
    从上传图片返回的JSON数据中提取图片ID
    
    参数:
        upload_result (dict): upload_base64_image_to_qwenlm函数返回的JSON数据
        
    返回:
        str: 上传图片的ID
        
    异常:
        ValueError: 如果JSON中不包含id字段
    """
    if not upload_result or 'id' not in upload_result:
        raise ValueError("上传结果中未找到图片ID")
    return upload_result['id']

# 示例用法
if __name__ == "__main__":
    # 示例 Base64 图像数据
    base64_image = ""

    try:
        # 使用新的入口函数
        upload_data = upload_base64_image_to_qwenlm(base64_image, "your_token_here")
        data_id = get_image_id_from_upload(upload_data)
        print("Upload successful!")
        print("Image ID:", data_id)
    except Exception as e:
        print("Error:", str(e))
        
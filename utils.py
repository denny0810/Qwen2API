import base64
import logging
import requests
from requests_toolbelt import MultipartEncoder
from typing import Dict, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)

class ImageProcessingError(Exception):
    """图像处理过程中的异常基类"""
    pass

class Base64ConversionError(ImageProcessingError):
    """Base64转换过程中的异常"""
    pass

class UploadError(ImageProcessingError):
    """上传过程中的异常"""
    pass

class ImageUtils:
    """处理图像相关操作的工具类"""
    
    @staticmethod
    def base64_to_bytes(base64_image: str) -> bytes:
        """
        将Base64编码的图像转换为二进制数据
        
        参数:
            base64_image (str): Base64格式的图片数据，可能包含前缀如 "data:image/png;base64,"
            
        返回:
            bytes: 解码后的二进制图像数据
            
        异常:
            Base64ConversionError: 如果解码过程中出现错误
        """
        try:
            # 提取Base64编码部分（去掉data URL的前缀）
            if ',' in base64_image:
                base64_data = base64_image.split(',', 1)[1]
            else:
                # 如果没有逗号分隔符，假设整个字符串都是base64数据
                base64_data = base64_image
            
            # 将Base64编码解码为二进制数据
            return base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"Base64转换失败: {str(e)}")
            raise Base64ConversionError(f"Base64转换失败: {str(e)}")

class QwenLMUploader:
    """处理与QwenLM API的图像上传相关操作"""
    
    def __init__(self, base_url: str = "https://chat.qwenlm.ai/api/v1/files/"):
        """
        初始化上传器
        
        参数:
            base_url (str): QwenLM API的基础URL
        """
        self.base_url = base_url
    
    def _prepare_headers(self, token: str) -> Dict[str, str]:
        """
        准备请求头
        
        参数:
            token (str): 认证token
            
        返回:
            Dict[str, str]: 包含认证信息的请求头
        """
        return {
            'accept': 'application/json',
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def upload_blob(self, blob: bytes, token: str, filename: str = "image.png", content_type: str = "image/png") -> Dict[str, Any]:
        """
        上传二进制数据到QwenLM
        
        参数:
            blob (bytes): 要上传的二进制数据
            token (str): 认证token
            filename (str): 上传文件的文件名
            content_type (str): 文件的内容类型
            
        返回:
            Dict[str, Any]: 上传成功后的响应数据，包含文件ID
            
        异常:
            UploadError: 如果上传过程中出现错误
        """
        try:
            headers = self._prepare_headers(token)
            
            # 创建MultipartEncoder对象
            m = MultipartEncoder(
                fields={
                    'file': (filename, blob, content_type)
                }
            )
            
            # 更新headers中的Content-Type
            headers.update({'Content-Type': m.content_type})
            
            # 发送POST请求
            response = requests.post(self.base_url, headers=headers, data=m)
            
            # 检查响应
            if response.status_code == 200:
                upload_data = response.json()
                if 'id' not in upload_data:
                    logger.error("上传成功但未返回ID")
                    raise UploadError('文件上传成功但未返回ID')
                logger.info(f"文件上传成功，ID: {upload_data['id']}")
                return upload_data
            else:
                logger.error(f"HTTP错误: {response.status_code}, 响应: {response.text}")
                raise UploadError(f'HTTP错误: {response.status_code}')
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {str(e)}")
            raise UploadError(f"请求异常: {str(e)}")
        except Exception as e:
            logger.error(f"上传过程中发生未知错误: {str(e)}")
            raise UploadError(f"上传过程中发生未知错误: {str(e)}")
    
    def upload_base64_image(self, base64_image: str, token: str) -> Dict[str, Any]:
        """
        将Base64格式的图片上传到QwenLM
        
        参数:
            base64_image (str): Base64格式的图片数据，包含前缀如 "data:image/png;base64,"
            token (str): 认证token
            
        返回:
            Dict[str, Any]: 上传成功后的响应数据，包含文件ID
            
        异常:
            ImageProcessingError: 如果处理或上传过程中出现错误
        """
        try:
            # 将Base64转换为二进制数据
            blob = ImageUtils.base64_to_bytes(base64_image)
            # 上传二进制数据
            return self.upload_blob(blob, token)
        except Base64ConversionError as e:
            # 已经记录了日志，直接抛出
            raise
        except Exception as e:
            logger.error(f"上传图片失败: {str(e)}")
            raise ImageProcessingError(f"上传图片失败: {str(e)}")
    
    @staticmethod
    def get_image_id_from_upload(upload_result: Dict[str, Any]) -> str:
        """
        从上传图片返回的JSON数据中提取图片ID
        
        参数:
            upload_result (Dict[str, Any]): upload_base64_image函数返回的JSON数据
            
        返回:
            str: 上传图片的ID
            
        异常:
            ValueError: 如果JSON中不包含id字段
        """
        if not upload_result or 'id' not in upload_result:
            logger.error("上传结果中未找到图片ID")
            raise ValueError("上传结果中未找到图片ID")
        return upload_result['id']

# 为了保持向后兼容性，提供与原始API相同的函数
def base64_to_bytes(base64_image: str) -> bytes:
    """向后兼容的函数，调用ImageUtils.base64_to_bytes"""
    return ImageUtils.base64_to_bytes(base64_image)

def upload_to_qwenlm(blob: bytes, token: str) -> Dict[str, Any]:
    """向后兼容的函数，调用QwenLMUploader.upload_blob"""
    uploader = QwenLMUploader()
    return uploader.upload_blob(blob, token)

def upload_base64_image_to_qwenlm(base64_image: str, token: str) -> Dict[str, Any]:
    """向后兼容的函数，调用QwenLMUploader.upload_base64_image"""
    uploader = QwenLMUploader()
    return uploader.upload_base64_image(base64_image, token)

def get_image_id_from_upload(upload_result: Dict[str, Any]) -> str:
    """向后兼容的函数，调用QwenLMUploader.get_image_id_from_upload"""
    return QwenLMUploader.get_image_id_from_upload(upload_result)

# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 示例Base64图像数据
    base64_image = ""

    try:
        # 使用新的类
        uploader = QwenLMUploader()
        upload_data = uploader.upload_base64_image(base64_image, "your_token_here")
        data_id = uploader.get_image_id_from_upload(upload_data)
        print("Upload successful!")
        print("Image ID:", data_id)
        
        # 或者使用向后兼容的函数
        # upload_data = upload_base64_image_to_qwenlm(base64_image, "your_token_here")
        # data_id = get_image_id_from_upload(upload_data)
    except Exception as e:
        print("Error:", str(e))
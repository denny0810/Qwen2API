import os
import json
import logging
from flask import Flask, request, jsonify, Response, stream_with_context
import requests
from dotenv import load_dotenv

from cookie_formatter import format_cookie

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化Flask应用并加载环境变量
app = Flask(__name__)
load_dotenv()

# API端点配置
TARGET_API_URL = os.getenv('TARGET_API_URL', 'https://chat.qwen.ai/api/chat/completions')
MODELS_API_URL = os.getenv('MODELS_API_URL', 'https://chat.qwen.ai/api/models')
COOKIE_VALUE = os.getenv('COOKIE_VALUE', '') # 默认值

def handle_error(e, error_type=None):
    """统一错误处理函数
    
    Args:
        e (Exception): 异常对象
        error_type (str, optional): 错误类型，默认为None
    
    Returns:
        tuple: (错误响应字典, 状态码)
    """
    if error_type is None:
        error_type = 'API request' if isinstance(e, requests.exceptions.RequestException) else 'Internal server'
    
    error_message = f'{error_type} error: {str(e)}'
    logger.error(error_message)
    return {'error': error_message}, 500

def validate_request(request):
    """验证请求数据
    
    Args:
        request: Flask请求对象
    
    Returns:
        tuple: (请求数据, 错误响应, 状态码, cookie值)
    """
    # 验证API key格式
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, {'error': 'Missing or invalid API key format'}, 401, None
    
    # 获取API key并格式化cookie
    api_key = auth_header[7:]  # 去掉'Bearer '前缀
    cookie_value = format_cookie(api_key)
    
    # 验证请求数据格式
    try:
        request_data = request.get_json()
        if not isinstance(request_data, dict):
            return None, {'error': 'Invalid JSON format: must be an object'}, 400, None
        return request_data, None, None, cookie_value
    except Exception as e:
        return None, {'error': f'Invalid JSON format: {str(e)}'}, 400, None

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """处理聊天完成请求的端点"""
    # 验证请求
    request_data, error_response, status_code, cookie_value = validate_request(request)
    if error_response:
        return jsonify(error_response), status_code

    try:
        # 检查是否为流式请求
        stream_mode = request_data.get('stream', False)
        
        if stream_mode:
            # 流式请求处理
            response, status, headers = make_api_request(
                TARGET_API_URL, 
                method='POST', 
                data=request_data, 
                stream=True,
                cookie_value=cookie_value
            )
            if status != 200:
                return jsonify(response), status
            
            # 使用Flask的stream_with_context处理流式响应
            return Response(
                stream_with_context(process_stream_response(response)),
                status=200,
                headers=headers
            )
        else:
            # 非流式请求处理
            response, status = make_api_request(
                TARGET_API_URL, 
                method='POST', 
                data=request_data,
                cookie_value=cookie_value
            )
            return jsonify(response), status
    except Exception as e:
        error_response, status_code = handle_error(e)
        return jsonify(error_response), status_code

def make_api_request(url, method='GET', data=None, stream=False, cookie_value=None):
    """统一的API请求处理函数
    
    Args:
        url (str): 目标API的URL
        method (str): HTTP请求方法，默认为'GET'
        data (dict): POST请求的数据，默认为None
        stream (bool): 是否使用流式响应，默认为False
        cookie_value (str): 用于请求的cookie值，默认为None
    
    Returns:
        tuple: (响应数据, 状态码) 或 (响应数据, 状态码, 头部信息)
    """
    try:
        # 设置请求头
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 使用传入的cookie值或默认值
        actual_cookie = cookie_value if cookie_value is not None else COOKIE_VALUE
        
        # 准备请求参数
        kwargs = {
            'headers': headers,
            'cookies': {'_auth_token': actual_cookie},
            'stream': stream
        }
        if data:
            kwargs['json'] = data

        # 记录请求信息和实际使用的cookie值
        logger.info(f"{method} request to {url}")
        logger.info(f"Using cookie value: {actual_cookie}")
        if data:
            logger.debug(f"Request data: {json.dumps(data, ensure_ascii=False)}")

        # 发送请求
        response = requests.request(method, url, **kwargs)

        # 处理流式响应
        if stream and response.status_code == 200:
            return response, 200, {'Content-Type': 'text/event-stream'}

        # 记录响应信息
        logger.info(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        if not stream:
            logger.debug(f"Response content: {response.text}")

        # 处理非200状态码
        if response.status_code != 200:
            return {'error': f'API request failed with status code: {response.status_code}'}, response.status_code

        # 处理非流式响应的内容类型
        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' in content_type and not stream:
            return response.text, response.status_code, {'Content-Type': 'text/event-stream'}

        # 处理空响应
        response_text = response.text.strip()
        if not response_text:
            return {'error': 'Empty response from server'}, 500

        # 返回JSON响应
        return json.loads(response_text), response.status_code

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return handle_error(e)
    except Exception as e:
        return handle_error(e, 'Internal server')

def process_stream_response(response):
    """处理流式响应，删除重复内容
    
    Args:
        response: 原始响应对象
    
    Yields:
        str: 处理后的事件流数据
    """
    previous_content = ""
    chunk_count = 0
    full_response = ""
    logger.info("Stream response processing started")
    
    for chunk in response.iter_lines():
        if chunk:
            chunk_count += 1
            chunk_str = chunk.decode('utf-8')
            
            # 只处理data字段的行
            if chunk_str.startswith('data:'):
                try:
                    # 提取JSON数据
                    data_json = json.loads(chunk_str[5:].strip())
                    if 'choices' in data_json and len(data_json['choices']) > 0:
                        # 获取当前内容
                        current_content = data_json['choices'][0].get('delta', {}).get('content', '')
                        if current_content:
                            # 累积完整响应
                            if previous_content and current_content.startswith(previous_content):
                                new_content = current_content[len(previous_content):]
                                full_response += new_content
                                data_json['choices'][0]['delta']['content'] = new_content
                            else:
                                full_response += current_content
                            previous_content = current_content
                            
                            # 检查是否为最后一个消息
                            if data_json.get('choices', [{}])[0].get('finish_reason') is not None:
                                logger.info(f"Final response: {full_response}")
                    
                    # 重新构建事件流数据
                    processed_chunk = f"data: {json.dumps(data_json)}\n\n"
                    yield processed_chunk
                except json.JSONDecodeError as e:
                    # 如果解析失败，直接传递原始数据
                    logger.warning(f"Failed to parse JSON: {e}")
                    yield f"{chunk_str}\n\n"
            else:
                # 非data行直接传递
                yield f"{chunk_str}\n\n"
    
    # 如果没有在流中检测到结束标志，在这里记录完整响应
    if full_response:
        logger.info(f"Complete response: {full_response}")
    
    logger.info(f"Total chunks processed: {chunk_count}")
    logger.info("Stream processing completed")

@app.route('/v1/models', methods=['GET'])
def list_models():
    """获取可用模型列表的端点"""
    try:
        return make_api_request(MODELS_API_URL)
    except Exception as e:
        error_response, status_code = handle_error(e)
        return jsonify(error_response), status_code

if __name__ == '__main__':
    logger.info("Starting Qwen2 API server on port 5000")
    app.run(host='0.0.0.0', port=5000)
from flask import request, jsonify, Response, stream_with_context
import json
import logging
import requests

from utils import upload_base64_image_to_qwenlm, get_image_id_from_upload
from config import TARGET_API_URL, MODELS_API_URL, COOKIE_VALUE

# 获取日志记录器
logger = logging.getLogger(__name__)


def handle_error(e, error_type=None):
    """统一错误处理函数"""
    if error_type is None:
        error_type = 'API请求' if isinstance(e, requests.exceptions.RequestException) else '服务器内部'
    
    error_message = f'{error_type}错误: {str(e)}'
    logger.error(error_message)
    return {'error': error_message}, 500


def validate_request(request, get_auth_token):
    """验证请求数据"""
    # 验证API key
    auth_header = request.headers.get('Authorization')
    token, error_message, status_code = get_auth_token(auth_header)
    
    if error_message:
        return None, {'error': error_message}, status_code, None
    
    # 验证请求数据格式
    try:
        request_data = request.get_json()
        # 添加请求内容的调试输出
        logger.info(f"收到请求: {json.dumps(request_data, ensure_ascii=False)}")
        if not isinstance(request_data, dict):
            return None, {'error': '无效的JSON格式:必须是一个对象'}, 400, None
        return request_data, None, None, token
    except Exception as e:
        return None, {'error': f'无效的JSON格式: {str(e)}'}, 400, None


def make_api_request(url, method='GET', data=None, stream=False, token_value=None):
    """统一的API请求处理函数"""
    try:
        # 使用传入的token值或默认值
        token = token_value
        
        # 设置请求头
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Authorization': f'Bearer {token}',
            'Cookie': f'{COOKIE_VALUE}'
        }
        
        # 准备请求参数
        kwargs = {
            'headers': headers,
            'stream': stream
        }
        if data:
            # 添加请求数据的调试输出
            logger.info(f"发送到目标API的数据: {json.dumps(data, ensure_ascii=False)}")
            kwargs['json'] = data

        # 发送请求
        logger.info(f"{method} 请求到 {url}")
        response = requests.request(method, url, **kwargs)
        logger.info(f"响应状态码: {response.status_code}")

        # 处理流式响应
        if stream and response.status_code == 200:
            return response, 200, {'Content-Type': 'text/event-stream'}

        # 处理非200状态码
        if response.status_code != 200:
            return {'error': f'API请求失败，状态码: {response.status_code}'}, response.status_code

        # 处理非流式响应的内容类型
        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' in content_type and not stream:
            return response.text, response.status_code, {'Content-Type': 'text/event-stream'}

        # 处理响应内容
        response_text = response.text.strip()
        if not response_text:
            return {'error': '服务器返回空响应'}, 500

        # 添加非流式响应内容的调试输出
        if not stream:
            try:
                response_json = json.loads(response_text)
                logger.info(f"收到响应: {json.dumps(response_json, ensure_ascii=False)[:1000]}...")
            except:
                logger.info(f"收到非JSON响应: {response_text[:1000]}...")

        return json.loads(response_text), response.status_code

    except Exception as e:
        return handle_error(e)


def process_stream_response(response):
    """处理流式响应，删除重复内容"""
    previous_content = ""
    full_response = ""
    chunk_count = 0  # 添加这个变量来计数处理的数据块
    
    for chunk in response.iter_lines():
        if chunk:
            chunk_count += 1  # 增加计数器
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
                            # 累积完整响应并处理重复内容
                            if previous_content and current_content.startswith(previous_content):
                                new_content = current_content[len(previous_content):]
                                full_response += new_content
                                data_json['choices'][0]['delta']['content'] = new_content
                            else:
                                full_response += current_content
                            previous_content = current_content
                    
                    # 重新构建事件流数据
                    processed_chunk = f"data: {json.dumps(data_json)}\n\n"
                    yield processed_chunk
                except json.JSONDecodeError:
                    # 如果解析失败，直接传递原始数据
                    yield f"{chunk_str}\n\n"
            else:
                # 非data行直接传递
                yield f"{chunk_str}\n\n"
    
    # 如果没有在流中检测到结束标志，在这里记录完整响应
    if full_response:
        logger.info(f"Complete response: {full_response}")
    
    logger.info(f"Total chunks processed: {chunk_count}")
    logger.info("Stream processing completed")


def chat_completions_route(get_auth_token):
    """处理聊天完成请求的端点"""
    # 验证请求
    request_data, error_response, status_code, token_value = validate_request(request, get_auth_token)
    if error_response:
        return jsonify(error_response), status_code

    try:
        # 检查是否为流式请求
        stream_mode = request_data.get('stream', False)
        
        # 处理多模态消息格式
        if 'messages' in request_data:
            for message in request_data['messages']:
                if 'content' in message:
                    # 如果content是字符串，转换为列表格式
                    if isinstance(message['content'], str):
                        message['content'] = [{"type": "text", "text": message['content']}]
                    # 确保列表格式符合通义千问API要求
                    elif isinstance(message['content'], list):
                        formatted_content = []
                        for item in message['content']:
                            if item.get('type') == 'text':
                                formatted_content.append({
                                    'text': item.get('text', ''),
                                    'type': 'text'
                                })
                            elif item.get('type') == 'image_url':
                                # 提取图片
                                image_data = item.get('image_url', '')
                                # 如果image是对象且包含url字段，提取url值
                                if isinstance(image_data, dict) and 'url' in image_data:
                                    image_id=get_image_id_from_upload(upload_base64_image_to_qwenlm(image_data['url'],token_value))
                                    formatted_content.append({
                                        'image': image_id,  # 提取url字段的值
                                        'type': 'image'
                                    })
                            elif item.get('type') == 'image':
                                formatted_content.append({
                                    'image': item.get('image', ''),
                                    'type': 'image'
                                })
                        message['content'] = formatted_content
        
        if stream_mode:
            # 流式请求处理
            response, status, headers = make_api_request(
                TARGET_API_URL, 
                method='POST', 
                data=request_data, 
                stream=True,
                token_value=token_value
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
                token_value=token_value
            )
            return jsonify(response), status
    except Exception as e:
        error_response, status_code = handle_error(e)
        return jsonify(error_response), status_code


def models_route():
    """获取可用模型列表的端点"""
    try:
        response, status = make_api_request(MODELS_API_URL)
        return jsonify(response), status
    except Exception as e:
        error_response, status_code = handle_error(e)
        return jsonify(error_response), status_code


def index_route():
    """显示帮助和介绍信息的根目录端点"""
    help_text = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Qwen2Api 帮助</title>
        <style>
            body { 
                font-family: sans-serif; 
                line-height: 1.6; 
                padding: 20px; 
                background-color: #1e1e1e; /* 暗色背景 */
                color: #d4d4d4; /* 浅色文字 */
            }
            h1, h2 { 
                color: #cccccc; /* 标题颜色 */
                border-bottom: 1px solid #444; /* 标题下划线 */
                padding-bottom: 5px;
            }
            code { 
                background-color: #333333; /* 代码块背景 */
                color: #d4d4d4; /* 代码块文字颜色 */
                padding: 2px 6px; 
                border-radius: 4px; 
                font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
            }
            pre { 
                background-color: #2a2a2a; /* 预格式化文本背景 */
                padding: 15px; 
                border-radius: 4px; 
                overflow-x: auto; 
                border: 1px solid #444;
            }
            .endpoint { 
                margin-bottom: 15px; 
                padding: 10px;
                background-color: #2a2a2a;
                border-radius: 4px;
                border: 1px solid #444;
            }
            .endpoint span { 
                font-weight: bold; 
                margin-right: 10px; 
                color: #9cdcfe; /* 标签颜色 */
            }
            a {
                color: #569cd6; /* 链接颜色 */
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            h3 {
                color: #cccccc;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <h1>Qwen2Api</h1>
        
        <h2>API Endpoints</h2>
        <div class="endpoint">
            <span>Models:</span> <code>/v1/models</code> <br>
            <span>Chat:</span> <code>/v1/chat/completions</code>
        </div>

        <h3>GitHub: <a href="https://github.com/jyz2012/qwen2api" target="_blank">jyz2012/qwen2api</a></h3>
    </body>
    </html>
    """
    return Response(help_text, mimetype='text/html')
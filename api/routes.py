from flask import request, jsonify, Response, stream_with_context
import json
import logging
import requests

from utils import upload_base64_image_to_qwenlm, get_image_id_from_upload
from config import TARGET_API_URL, MODELS_API_URL, COOKIE_VALUE, FORCE_NO_STREAM
# 获取日志记录器
logger = logging.getLogger(__name__)


def handle_error(e, error_type=None):
    """统一错误处理函数"""
    if error_type is None:
        error_type = 'API请求' if isinstance(e, requests.exceptions.RequestException) else '服务器内部'
    
    error_message = f'{error_type}错误: {str(e)}'
    logger.error(error_message)
    return {'error': error_message}, 500

def make_api_request(url, method='GET', data=None, stream=False, token_value=None):
    """Handles interaction with the target API including streaming and non-streaming request/response patterns.
    Supports forced non-streaming configuration override, automatically handles authentication and request parameters.
    
    Args:
        url (str): Complete URL of the target API endpoint
        method (str, optional): HTTP method ('GET', 'POST', etc.). Defaults to 'GET'
        data (dict, optional): Request body data. Defaults to None
        stream (bool, optional): Whether this is a streaming request. Defaults to False
        token_value (str, optional): Bearer authentication token. Defaults to None

    Returns:
        tuple: Contains three elements:
            - response_data: Parsed JSON dict (non-streaming) or raw response object (streaming)
            - status_code: HTTP status code
            - is_stream: Boolean indicating if response is streaming
    """

    try:
        logger.info("检测到客户端发送的 [%s] 请求", '流式' if stream else '非流式')
        # Set API streaming request flag
        if FORCE_NO_STREAM:  # If non-streaming is forced, ignore the original request's streaming flag
            stream = False
        logger.debug("API将向服务器发送 [%s] 请求", '流式' if stream else '非流式')
        
        # Set request headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Authorization': f'Bearer {token_value}',
            'Cookie': f'{COOKIE_VALUE}'
        }
        
        # Prepare request parameters
        kwargs = {'headers': headers, 'stream': stream}
        if data:
            data['stream'] = stream  # Ensure the server receives the same streaming flag as the API
            kwargs['json'] = data
        
        # send request to the target API
        logger.info("%s 请求到 %s", method, url)
        logger.debug("JSON格式的完整发送请求: %s", json.dumps(kwargs, ensure_ascii=False, indent=2))
        response = requests.request(method, url, **kwargs)
        logger.info("响应状态码: %d", response.status_code)

        # Procede response handling based on status code
        if response.status_code == 200:            
            logger.debug("返回的完整响应: %s", response.text)            
            
            # Streaming response handling
            if stream:
                return response, 200, True          
            # Non-streaming response handling
            try:
                response_text = response.text.strip()
                none_stream_json = json.loads(response_text)
                return none_stream_json, 200, False
            except json.JSONDecodeError:
                logger.error("返回的响应数据未包含有效的JSON格式")
                return {'error': '返回的响应数据未包含有效的JSON格式'}, 500, False
        
        # Procede responde处理非200状态码
        logger.error("API请求失败，状态码: %d", response.status_code)
        return {'error': f'API请求失败，状态码: {response.status_code}'}, response.status_code, False
    
    except Exception as e:
        return handle_error(e)

def generate_stream_response(response):
    """Generator function to convert non-streaming response to streaming format
    
    Features:
        - Converts complete response to streaming chunks
        - Maintains OpenAI API compatibility
        - Provides incremental content delivery
        - Handles text content only
        
    Process:
        1. Extracts complete content from response object
        2. Builds content incrementally character by character
        3. Calculates delta between current and previous content
        4. Constructs OpenAI-compliant streaming format
        5. Yields formatted response chunks
    
    Returns:
        str: Streaming response chunk in format "data: {JSON}\n\n"
    """
    # Extract complete content from response object
    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    # Store previous content fragment for delta calculation
    previous = ""
    
    # Incrementally build content character by character
    for i in range(1, len(content) + 1):
        # Get current length content fragment
        current = content[:i]
        
        # Calculate new content portion
        new_content = current[len(previous):]
        
        # Skip empty content
        if not new_content:
            continue
            
        # Construct OpenAI streaming format
        chunk = {
            "choices": [{
                "delta": {
                    "role": "assistant",
                    "content": new_content
                }
            }]
        }
        
        # Yield formatted response chunk and update previous content
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        previous = current

    # Add a stop signal to indicate the end of streaming
    yield "data: [DONE]\n\n"
    

def process_stream_response(response):
    """Processes a streaming HTTP response to remove duplicate content and reconstruct clean event stream data.
    
    Handles Server-Sent Events (SSE) format by:
    - Detecting and removing duplicate content prefixes in consecutive chunks
    - Skipping completely duplicate chunks
    - Maintaining full response reconstruction for logging
    - Preserving non-data lines in the stream
    - Counting processed chunks for monitoring
    
    Args:
        response (iterable): The HTTP response object that supports iter_lines(),
                            typically from requests library or similar.
                            
    Yields:
        str: Processed event stream chunks in format "data: {json}\n\n" or
             passes through non-data lines unchanged.
             
    Behavior:
        1. Processes only lines starting with 'data:'
        2. For valid JSON data:
           - Extracts and processes content from choices[0].delta.content
           - Removes duplicate content from previous chunks
           - Skips completely duplicate chunks
           - Reconstructs clean event stream data
        3. For invalid JSON: passes through original data
        4. Logs:
           - Complete reconstructed response at end
           - Total chunks processed
           - Stream completion
    
    Example:
        >>> for chunk in process_stream_response(response):
        ...     print(chunk)
        data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n
        data: {"choices": [{"delta": {"content": " world"}}]}\n\n
    """
    previous_content = ""
    previous_chunk = None
    full_response = ""
    chunk_count = 0  # 添加这个变量来计数处理的数据块
    
    for chunk in response.iter_lines():
        if chunk:
            chunk_count += 1  # 增加计数器
            chunk_str = chunk.decode('utf-8')
            
            # Skip if this is an exact duplicate of the previous chunk
            if chunk_str == previous_chunk:
                continue
                
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
                    previous_chunk = chunk_str  # Store for duplicate checking
                    yield processed_chunk
                except json.JSONDecodeError:
                    # 如果解析失败，直接传递原始数据
                    yield f"{chunk_str}\n\n"
            else:
                # 非data行直接传递
                yield f"{chunk_str}\n\n"
    
    # 如果没有在流中检测到结束标志，在这里记录完整响应
    if full_response:
        logger.debug("Stream processing completed")        
        logger.debug("Total chunks processed: %d", chunk_count)
        logger.debug("Complete response: %s", full_response)        
    
    # Add a stop signal to indicate the end of streaming
    yield "data: [DONE]\n\n"

def process_multimodal_content(content, token_value):
    """处理多模态内容
    
    Args:
        content: 要处理的内容，可以是字符串或列表格式
        token_value: 认证令牌值
    
    Returns:
        list: 格式化后的多模态内容列表
    """
    # 如果content是字符串，转换为列表格式
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    
    # 如果不是列表或字典类型，返回空列表
    if not isinstance(content, list):
        return []
    
    formatted_content = []
    for item in content:
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
                image_id = get_image_id_from_upload(upload_base64_image_to_qwenlm(image_data['url'], token_value))
                formatted_content.append({
                    'image': image_id,  # 提取url字段的值
                    'type': 'image'
                })
        elif item.get('type') == 'image':
            formatted_content.append({
                'image': item.get('image', ''),
                'type': 'image'
            })
    
    return formatted_content

def chat_completions_route(get_auth_token):
    """处理聊天完成请求的端点"""
    # 跳过 OPTIONS 请求的处理
    if request.method == 'OPTIONS':
        return '', 200
   
    # 验证请求数据格式
    try:
        request_data = request.get_json()
        logger.debug("完整请求数据: %s", json.dumps(request_data, ensure_ascii=False, indent=2))
        if not isinstance(request_data, dict):
            return jsonify({'error': '请求JSON格式不正确，应为一个JSON对象'}), 400
        
        # 检查并格式化stream参数，只有严格为True或字符串'true'时才为True，其余及没有stream一律为False
        # val = request_data.get('stream')
        # if val is True or (isinstance(val, str) and val.lower() == 'true'):
        #     request_data['stream'] = True
        # else:
        #     request_data['stream'] = False
        #     logger.info("stream参数未显式为True，已设置为False")
    
    except Exception as e:
        return jsonify({'error': f'无效的JSON格式: {str(e)}'}), 400
    
    # 验证API key
    authorization_header = request.headers.get('Authorization')
    token_value, error_message, status_code = get_auth_token(authorization_header)
    if error_message:
        logger.error("认证失败: %s", error_message)
        return jsonify(error_message), status_code

    try:
        # 处理多模态消息格式
        if 'messages' in request_data:
            for message in request_data['messages']:
                if 'content' in message:
                    message['content'] = process_multimodal_content(message['content'], token_value)
        
        # 检查客户端请求格式，默认非流式请求
        is_stream_request = request_data.get('stream', False)
        
        # 发送请求到目标API 
        response, status_code, is_stream_response = make_api_request(
            TARGET_API_URL, 
            method='POST', 
            data=request_data,
            stream=is_stream_request, 
            token_value=token_value
        )
        
        if status_code != 200:
            return jsonify(response), status_code
            
        # 客户端流式请求，使用Flask的stream_with_context处理流式响应
        # 接收到非流式JSON格式响应
        if is_stream_request:            
            if not is_stream_response:
                logger.warning("检测到对客户端流式请求的非流式响应 ❕")
                logger.warning("生成伪流式响应 ❕")
                logger.debug("生成的伪流式响应: %s", json.dumps(list(generate_stream_response(response)), ensure_ascii=False, indent=2))
                return Response(
                    stream_with_context(generate_stream_response(response)),
                    status=200,
                    mimetype='text/event-stream'
                )
            # 接收到流式响应
            logger.info("检测到对客户端流式请求的流式响应 ✅")
            return Response(
                stream_with_context(process_stream_response(response)),
                status=200,
                mimetype='text/event-stream'
            )
        
        # 客户端非流式请求
        # 接收到非流式格式响应
        if not is_stream_response:
            logger.info("检测到对客户端非流式请求的非流式响应 ✅")
            return jsonify(response), 200        
        # 接收到流式响应 
        # =====从程序逻辑上不应该发生，但如果发生了，转换为非流式响应====== 
        logger.warning("检测到对客户端非流式请求的流式响应 ❕")
        logger.warning("转换生成非流式响应 ❕")
        last_line = response.strip().splitlines()[-1] # 截取最后一行转换为非流式响应
        try:
            data_json=json.loads(last_line[5:].strip()) # 去掉 'data:' 前缀并去除空格
            content = data_json["choices"][0]["delta"].get("content", "")
            response_json = {"choices": [{"message": {"role": "assistant", "content": content}}]}
            logger.debug("转换流式响应为非流式响应: %s", json.dumps(response_json, ensure_ascii=False, indent=2))
            return jsonify(response_json), 200
        except json.JSONDecodeError:
            logger.error("返回的响应数据不是有效的JSON格式")
            return {'error': '返回的响应数据不是有效的JSON格式'},500

    except Exception as e:
        error_response, status_code = handle_error(e)
        return jsonify(error_response), status_code


def models_route():
    """获取可用模型列表的端点"""
    try:
        response, status, is_stream_response = make_api_request(MODELS_API_URL)
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

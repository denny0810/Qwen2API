# Qwen2Api

将 [Qwen Chat](https://chat.qwen.ai/) 转换为 Openai 格式的 api 服务，现已支持图片上传等功能。

## 项目结构

采用模块化设计，结构如下：

```
qwen2api/
├── api/                  # API路由模块
│   ├── __init__.py
│   └── routes.py         # 路由处理逻辑
├── logger/               # 日志处理模块
│   └── __init__.py       # 日志配置和清理功能
├── logs/                 # 日志文件目录
├── app.py               # 主应用入口
├── config.py            # 配置管理
├── utils.py             # 工具函数
├── logging_config.yaml  # 日志配置文件
├── requirements.txt     # 依赖项
├── Dockerfile           # Docker配置
└── README.md            # 项目文档
```

## 快速搭建

1. 克隆此项目

```bash
git clone https://github.com/jyz2012/qwen2api.git
```

2. 安装所需的库

```bash
pip install -r requirements.txt
```

3. 运行主程序

```bash
python app.py
```

**注意**：**这是一个开发服务器。请勿在生产部署中使用它。如果需要，请使用 WSGI 服务器。**

## 环境变量

- `CHAT_AUTHORIZATION`: 通义千问API的授权令牌，可以设置多个令牌，用逗号分隔

## API端点

### 1. 聊天完成

```
POST /v1/chat/completions
```

请求示例：

```json
{
  "model": "qwen-max",
  "messages": [
    {"role": "user", "content": "你好"}
  ]
}
```

### 2. 获取模型列表

```
GET /v1/models
```

## 多模态支持

支持发送图片和文本的多模态请求，示例：

```json
{
  "model": "qwen-max",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "这张图片是什么?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."}}
      ]
    }
  ]
}
```

## Docker 部署

### Docker Compose 示例

```yaml
services:
  qwen2api:
    container_name: qwen2api
    image: <your hub repository>/qwen2api:latest
    restart: always
    network_mode: bridge
    ports:
      - 6060:6060
    environment:
      - TZ=Asia/Shanghai
      - CHAT_AUTHORIZATION=<your token>
    volumes:
      - <your log file location>:/app/logs
```

## 项目特点

- 模块化设计，代码结构清晰
- 支持流式输出
- 支持多模态输入（文本和图像）
- 完善的日志记录和错误处理
- 自动清理旧日志文件
- Docker支持，便于部署

## 许可证

本项目使用 GPL v3 许可证。详情请参阅 [LICENSE](./License) 文件。

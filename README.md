# OpenAI API 中转服务

这是一个API中转服务，用于将QwenChat转换为标准的基于API key认证的OpenAI格式API。

## 功能特点

- 将cookie认证转换为API key认证
- 完全兼容OpenAI API格式
- 简单的配置和部署

## 安装步骤

1. 克隆项目到本地
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 配置环境变量：
   - 复制 `.env.example`文件为 `.env`
   - 在 `.env`文件中设置目标API的URL和cookie值

## 使用方法

1. 启动服务器：

   ```bash
   python app.py
   ```
2. 服务器将在 `http://localhost:5000`上运行
3. 调用API：

   - 端点：`/v1/chat/completions`
   - 使用标准的OpenAI API格式
   - 在Authorization header中使用token

示例请求：

```bash
curl http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer xxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-max-latest",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

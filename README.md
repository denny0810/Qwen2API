# Qwen2Api

## 介绍

将 [Qwen Chat](https://chat.qwen.ai) 转换为 Openai 格式的 api 服务，现已支持图片上传等功能。

## 快速搭建

1.克隆此项目

`git clone https://github.com/jyz2012/qwen2api.git`

2.安装所需的库

`pip install -r requirements.txt`

3.运行主程序

`python app.py`

**注意**：**这是一个开发服务器。请勿在生产部署中使用它。如果需要，请使用 WSGI 服务器。**

## 环境要求

**python** >= **3.11**

**pip** >= **25.0**

## 相关接口

模型:   `/v1/models`

聊天:   `/v1/chat/completions`

## API Key获取

在 [Qwen Chat](https://chat.qwen.ai) 中打开开发者模式与大模型聊天，会出现一个 completion 请求，在请求头里找到 Authorization 复制下来去掉 Bearer 前缀就可以使用了

## API使用示例

### 文本聊天

```bash
curl -X POST "http://your_site/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "model": "qwen-max-latest",
    "messages": [
      {
        "role": "user",
        "content": "hi"
      }
    ],
    "stream": false
  }'
```

### 图片请求

```bash
curl -X POST "http://your_site/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "model": "qwen-max-latest",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "What's that?"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,/9j/4DWwf31..."
            }
          }
        ]
      }
    ],
    "stream": false
  }'
```

## 免责申明

+ 本项目仅用作学习技术，请勿滥用，不要通过此工具做任何违法乱纪或有损国家利益之事
+ 禁止使用该项目进行任何盈利活动，对一切非法使用所产生的后果，本人概不负责

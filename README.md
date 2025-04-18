# Qwen2Api

## 介绍

将 [Qwen Chat](https://chat.qwen.ai) 转换为 Openai 格式的 api 服务，现已支持图片上传等功能

## 搭建方法

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

模型:   `localhost:5000/v1/models`

聊天:   `localhost:5000/v1/chat/completions`

Base Url :  `localhost:5000` (for Cherry Studio etc...)

## API Key获取

在 [Qwen Chat](https://chat.qwen.ai) 中打开开发者模式与大模型聊天，会出现一个 completion 请求，在里面的请求头里面找到 cookie 复制下来输入到 [处理工具](https://jyz2012.github.io/kukitky/) 中，复制结果就可以使用了

## 日志

本项目所有日志信息将会打印到  `qwen2api.log` 文件中，日志记录了发送到网站的请求、网站处理后发送到目标Api地址的请求内容、目标模型的响应等。日志仅用于调试代码。

## 免责申明

+ 本项目仅用作学习技术，请勿滥用，不要通过此工具做任何违法乱纪或有损国家利益之事
+ 禁止使用该项目进行任何盈利活动，对一切非法使用所产生的后果，本人概不负责

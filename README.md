# Qwen2Api

## 介绍

将 [Qwen Chat](https://chat.qwen.ai) 转换为 Openai 格式的 api 服务

## 使用方法

1.克隆此项目

`git clone repo-url`

2.安装所需的库

`pip install -r requirements.txt`

3.运行主程序

`python app.py`

## 相关接口

模型:   `localhost:5000/v1/models`

聊天:   `localhost:5000/v1/chat/completions`

Base Url :  `localhost:5000` (Cherry Studio etc...)

## API Key

在 [Qwen Chat](https://chat.qwen.ai) 中打开开发者模式与大模型聊天，会出现一个 completion 请求，在里面的请求头里面找到 cookie 复制下来输入到 [处理工具](https://jyz2012.github.io/kukitky/) 中，复制结果就可以使用了

## 免责申明

+ 本项目仅用作学习技术，请勿滥用，不要通过此工具做任何违法乱纪或有损国家利益之事
+ 禁止使用该项目进行任何盈利活动，对一切非法使用所产生的后果，本人概不负责

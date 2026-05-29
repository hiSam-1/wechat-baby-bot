import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

# 从环境变量中读取微信接头暗号
TOKEN = os.environ.get("WECHAT_TOKEN", "mybabylove")
# 核心：大飞的 API 密钥（在 Dify 后台生成的 app-xxx）
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
# 核心：大飞的 API 地址（默认是官方云端地址）
DIFY_API_URL = os.environ.get("DIFY_API_URL", "https://api.dify.ai/v1/chat-messages")

@app.route("/", methods=["GET", "POST"])
def wechat_auth():
    # 1. 微信接入验证
    if request.method == "GET":
        signature = request.args.get("signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")
        
        data = [TOKEN, timestamp, nonce]
        data.sort()
        sha1 = hashlib.sha1("".join(data).encode("utf-8")).hexdigest()
        
        if sha1 == signature:
            return make_response(echostr)
        return "验证失败"

    # 2. 处理微信消息
    if request.method == "POST":
        xml_data = request.data
        xml_rec = ET.fromstring(xml_data)
        
        to_user = xml_rec.find("ToUserName").text
        from_user = xml_rec.find("FromUserName").text
        msg_type = xml_rec.find("MsgType").text
        
        if msg_type == "text":
            content = xml_rec.find("Content").text.strip()
            
            # 🚀 直接呼叫你的大飞（Dify）API
            headers = {
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": {},
                "query": content,
                "response_mode": "blocking", # 阻塞模式，直接获取最终文本
                "user": from_user            # 用微信加密ID作为大飞的用户标识，大飞能自动记住上下文！
            }
            
            try:
                # 呼叫大飞，设置4.5秒超时防止微信断连
                response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=4.5)
                ai_reply = response.json()["answer"]
            except Exception as e:
                # 极端情况下的保底，大飞基本不会触发这里
                ai_reply = "唔……网络好像调皮了一下，你再重新对我说一次嘛~"

            # 3. 组装微信 XML 回传
            reply_xml = f"""
            <xml>
            <ToUserName><![CDATA[{from_user}]]></ToUserName>
            <FromUserName><![CDATA[{to_user}]]></FromUserName>
            <CreateTime>{int(time.time())}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{ai_reply}]]></Content>
            </xml>
            """
            response = make_response(reply_xml)
            response.content_type = "application/xml"
            return response
        
        return "success"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)

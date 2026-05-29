import os
import hashlib
import xml.etTree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

# 从环境变量中读取你配置的“暗号”
TOKEN = os.environ.get("WECHAT_TOKEN", "my_baby_token_123")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", "你叫宝宝，是一个性感的成人树洞。")

@app.route("/", methods=["GET", "POST"])
def wechat_auth():
    # 1. 微信公众号接入验证 (GET请求)
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
        return "认证失败"

    # 2. 处理用户发送的消息 (POST请求)
    if request.method == "POST":
        xml_data = request.data
        xml_rec = ET.fromstring(xml_data)
        
        to_user = xml_rec.find("ToUserName").text
        from_user = xml_rec.find("FromUserName").text
        msg_type = xml_rec.find("MsgType").text
        
        # 只处理文本消息
        if msg_type == "text":
            content = xml_rec.find("Content").text
            
            # 请求 OpenRouter 获大尺度 AI 回复
            headers = {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openrouter/auto",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ]
            }
            
            try:
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=15)
                ai_reply = response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                ai_reply = "嗯哈~ 宝宝刚才有点开小差，你再说一遍嘛..."

            # 组装微信专用的 XML 格式返回给用户
            reply_xml = f"""
            <xml>
            <ToUserName><![CDATA[{from_user}]]></ToUserName>
            <FromUserName><![CDATA[{to_user}]]></FromUserName>
            <CreateTime>{int(request.date.timestamp())}</CreateTime>
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

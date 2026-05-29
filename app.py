import os
import hashlib
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

# 从环境变量中读取你配置的密码和钥匙
TOKEN = os.environ.get("WECHAT_TOKEN", "mybabylove")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", "你叫宝宝，是一个性感的成人树洞。")

@app.route("/", methods=["GET", "POST"])
def wechat_auth():
    # 微信接入验证 (GET)
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

    # 处理用户发送的消息 (POST)
    if request.method == "POST":
        xml_data = request.data
        xml_rec = ET.fromstring(xml_data)
        
        to_user = xml_rec.find("ToUserName").text
        from_user = xml_rec.find("FromUserName").text
        msg_type = xml_rec.find("MsgType").text
        
        if msg_type == "text":
            content = xml_rec.find("Content").text
            
            # 请求 OpenRouter 大尺度 AI 模型
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
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=12)
                ai_reply = response.json()["choices"][0]["message"]["content"]
            except Exception:
                ai_reply = "呜……宝宝刚才走神了，你再疼疼我、重新说一遍嘛~"

            # 组装返回给微信用户的 XML
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
    # Hugging Face 默认只暴露 7860 端口，必须用这个端口运行
    app.run(host="0.0.0.0", port=7860)

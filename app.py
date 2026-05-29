import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

TOKEN = os.environ.get("WECHAT_TOKEN", "mybabylove")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
# 默认大尺度提示词
DEFAULT_PROMPT = "你叫宝宝，是一个性感的成人树洞。说话妖娆，多用括号描写动作。"
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", DEFAULT_PROMPT)

@app.route("/", methods=["GET", "POST"])
def wechat_auth():
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

    if request.method == "POST":
        xml_data = request.data
        xml_rec = ET.fromstring(xml_data)
        
        to_user = xml_rec.find("ToUserName").text
        from_user = xml_rec.find("FromUserName").text
        msg_type = xml_rec.find("MsgType").text
        
        if msg_type == "text":
            content = xml_rec.find("Content").text
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            }
            # 放弃自动路由，直接锁死速度最快、对成人话题完美的免费模型
            payload = {
                "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content}
                ]
            }
            
            try:
                # 严格限制 4.5 秒超时，防止微信断连
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=4.5)
                ai_reply = response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                # 超时或报错时的性感安抚语，确保微信一定能收到回复
                ai_reply = "呜……宝贝刚才让人家等太久了，小Q稍微有点开小差。你再重新摸摸我、和我说一次嘛~"

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

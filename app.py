import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

TOKEN = os.environ.get("WECHAT_TOKEN", "baby123456")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")

# 🚀 绝杀锁定：根据你的 cURL 示例，这是大飞官方云端聊天助手的绝对正确网址！
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"

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
            content = xml_rec.find("Content").text.strip()
            
            headers = {
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": {},
                "query": content,
                "response_mode": "blocking", # 微信不支持流式，强制必须用阻塞模式秒回整体文本
                "user": from_user            # 用微信加密ID作为用户标识，大飞能完美记住上下文聊天记忆！
            }
            
            try:
                # 呼叫官方大飞聊天助手接口
                response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=4.7)
                
                if response.status_code != 200:
                    ai_reply = f"🚨 大飞拒绝连接！状态码: {response.status_code}，原因: {response.text[:100]}"
                else:
                    res_json = response.json()
                    # 🚀 聊天助手的黄金标准：答案直接就在 answer 盒子里！
                    if "answer" in res_json:
                        ai_reply = res_json["answer"]
                    else:
                        ai_reply = f"🤔 拿到了数据但找不到answer。大飞返回: {str(res_json)[:100]}"
                    
            except requests.exceptions.Timeout:
                ai_reply = "啊哈…… 宝贝刚才的话让人家太兴奋了，脑子里一片空白…… *高潮失神中* 你再对人家说一次嘛~"
            except Exception as e:
                ai_reply = f"❌ 脚本运行异常: {str(e)}"

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

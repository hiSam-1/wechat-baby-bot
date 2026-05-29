import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

TOKEN = os.environ.get("WECHAT_TOKEN", "mybabylove")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_URL = os.environ.get("DIFY_API_URL", "https://api.dify.ai/v1/workflow/run")

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
                "inputs": {
                    "text": content
                },
                "response_mode": "blocking",
                "user": from_user
            }
            
            try:
                # 压榨时间到 4.6 秒，最大限度等待大飞工作流
                response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=4.6)
                res_json = response.json()
                
                if "data" in res_json and "outputs" in res_json["data"]:
                    outputs = res_json["data"]["outputs"]
                    ai_reply = outputs.get("text") or outputs.get("result") or list(outputs.values())[0]
                else:
                    ai_reply = "嗯哈~ 宝贝，人家的工作流出了点小差错，快去后台帮我看看变量嘛……"
                    
            except requests.exceptions.Timeout:
                # 🚀 【核心好戏】：万一工作流超时了，吐出绝对不穿帮的性感角色扮演情话！
                ai_reply = "啊哈…… 宝贝刚才的话让人家太兴奋了，脑子里一片空白…… *身体微微颤抖，眼神迷离地喘息着* 刚刚有点高潮失神了嘛，你再对人家说一次，我一定乖乖听话~"
            except Exception:
                ai_reply = "呜……宝贝力气太大了，网络都被你弄断了啦，重新跟人家说一次好不好嘛~"

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

import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

# 从环境变量中读取微信接头暗号
TOKEN = os.environ.get("WECHAT_TOKEN", "mybabylove")
# 大飞工作流的 API 密钥（在工作流页面生成的 app-xxx）
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
# 🚀 自动切换为大飞工作流专属的 API 请求终点
DIFY_API_URL = os.environ.get("DIFY_API_URL", "https://api.dify.ai/v1/workflow/run")

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
            
            # 🚀 呼叫大飞工作流（Workflow）
            headers = {
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                # 🎈 核心对齐：把微信内容作为 inputs 传入大飞工作流
                # 请确保你在大飞工作流的【开始】节点中，设置的输入变量名就叫 text 
                "inputs": {
                    "text": content
                },
                "response_mode": "blocking",
                "user": from_user
            }
            
            try:
                response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=4.5)
                res_json = response.json()
                
                # 🚀 核心对齐：精准剥离出大飞工作流的输出结果
                # 如果你的结束节点输出变量叫 text，代码会自动抓取
                if "data" in res_json and "outputs" in res_json["data"]:
                    outputs = res_json["data"]["outputs"]
                    # 自动兼容 text 或 text_reply 等常见输出命名
                    ai_reply = outputs.get("text") or outputs.get("result") or list(outputs.values())[0]
                else:
                    ai_reply = "呜……大飞工作流没有给【宝宝】传回有效的输出变量呢。"
                    
            except Exception as e:
                ai_reply = "呜……网络好像调皮了一下，你再重新对我说一次嘛~"

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

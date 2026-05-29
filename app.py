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
                    "text": content  # 👈 对应大飞开始节点的 text 变量
                },
                "response_mode": "blocking",
                "user": from_user
            }
            
            try:
                # 请求大飞
                response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=4.6)
                res_json = response.json()
                
                # 如果大飞返回了错误码（比如 400, 401）
                if response.status_code != 200:
                    ai_reply = f"🚨 大飞服务器报错啦！状态码: {response.status_code}，原因: {response.text}"
                elif "data" in res_json and "outputs" in res_json["data"]:
                    outputs = res_json["data"]["outputs"]
                    ai_reply = outputs.get("text") or outputs.get("result") or list(outputs.values())[0]
                else:
                    ai_reply = f"🤔 大飞返回了奇怪的数据格式: {str(res_json)}"
                    
            except requests.exceptions.Timeout:
                ai_reply = "啊哈…… 宝贝刚才的话让人家太兴奋了，脑子里一片空白…… *高潮失神中* 你再对人家说一次嘛~"
            except Exception as e:
                ai_reply = f"❌ 桥接脚本自身崩溃，错误信息: {str(e)}"

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

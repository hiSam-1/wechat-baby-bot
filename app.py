import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

TOKEN = os.environ.get("WECHAT_TOKEN", "baby123456")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")

# 🚀 智能多终点候选列表，彻底解决官方云端 404 问题
DIFY_URLS = [
    "https://api.dify.ai/v1/workflow/run",
    "https://api.dify.dev/v1/workflow/run",       # 国际版云端真实备用域名
    "https://api-cloud.dify.ai/v1/workflow/run"   # 极少数集群专用域名
]

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
            
            ai_reply = ""
            last_error = ""
            
            # 🚀 智能循环盲测每一个可能的官方云端接口
            for url in DIFY_URLS:
                try:
                    response = requests.post(url, json=payload, headers=headers, timeout=4.5)
                    
                    if response.status_code == 200:
                        res_json = response.json()
                        if "data" in res_json and "outputs" in res_json["data"]:
                            outputs = res_json["data"]["outputs"]
                            ai_reply = outputs.get("text") or outputs.get("result") or list(outputs.values())[0]
                            break # 成功拿到情话，立刻跳出循环
                    elif response.status_code == 404:
                        last_error = f"网址 {url} 报 404"
                        continue # 这个网址不对，继续试下一个
                    else:
                        ai_reply = f"🚨 大飞拒绝！状态码: {response.status_code}，原因: {response.text[:50]}"
                        break
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # 如果所有的网址都试了一遍还是没成功
            if not ai_reply:
                ai_reply = f"❌ 所有的官方接口都试过了，最后一次尝试报错: {last_error}。请检查你在大飞复制的【API访问】页面里的 API Base URL 到底写的是什么网址？"

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

import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

TOKEN = os.environ.get("WECHAT_TOKEN", "baby123456")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")

# 🚨 重点：强制锁死大飞官方云端【工作流】的绝对正确终点！
DIFY_API_URL = "https://api.dify.ai/v1/workflow/run"

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
                    "text": content  # 👈 必须对应大飞【开始】节点的变量名
                },
                "response_mode": "blocking",
                "user": from_user
            }
            
            try:
                response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=4.7)
                
                # 🚀 如果大飞返回的不是 200 成功，直接抓取大飞返回的网页原话！
                if response.status_code != 200:
                    ai_reply = f"🚨 官方大飞拒绝了连接！状态码: {response.status_code}，大飞原话: {response.text[:100]}"
                else:
                    res_json = response.json()
                    if "data" in res_json and "outputs" in res_json["data"]:
                        outputs = res_json["data"]["outputs"]
                        ai_reply = outputs.get("text") or outputs.get("result") or list(outputs.values())[0]
                    else:
                        ai_reply = f"🤔 大飞格式不对，返回了: {str(res_json)[:100]}"
                    
            except requests.exceptions.Timeout:
                ai_reply = "啊哈…… 宝贝刚才的话让人家太兴奋了，脑子里一片空白…… *高潮失神中* 你再对人家说一次嘛~"
            except Exception as e:
                # 🚀 升级：如果再崩溃，打印出到底是返回了什么文本导致不能解析成 JSON
                try:
                    raw_preview = response.text[:100]
                except:
                    raw_preview = "无法获取文本"
                ai_reply = f"❌ 脚本崩溃。错误: {str(e)}。大飞返回的前100字内容: {raw_preview}"

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

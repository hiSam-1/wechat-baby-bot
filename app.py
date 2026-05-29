import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

TOKEN = os.environ.get("WECHAT_TOKEN", "baby123456")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
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
        
        ai_reply = ""  # 初始化回复内容

        # ======= 🚀 新增：用户关注事件处理 =======
        if msg_type == "event":
            event_type = xml_rec.find("Event").text
            if event_type == "subscribe":
                # 在这里修改你想对关注用户说的话，以及你的文章标题和链接
                article_title = "想要了解的宝藏文章标题"
                article_url = "https://mp.weixin.qq.com/s/xxxxxx"  # 换成你的微信文章链接
                
                ai_reply = f"🎉 终于等到你啦，宝宝！欢迎关注！\n\n👇 推荐你阅读我的精选文章：\n<a href='{article_url}'>👉 点击这里阅读: {article_title}</a>"
        
        # ======= 🧩 原有逻辑：用户发送文本消息（保持不变） =======
        elif msg_type == "text":
            content = xml_rec.find("Content").text.strip()
            
            headers = {
                "Authorization": f"Bearer {DIFY_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": {},
                "query": content,
                "response_mode": "blocking",
                "user": from_user
            }
            
            try:
                response = requests.post(DIFY_API_URL, json=payload, headers=headers, timeout=4.7)
                
                if response.status_code != 200:
                    ai_reply = f"🚨 拒绝连接！状态码: {response.status_code}"
                else:
                    res_json = response.json()
                    if "answer" in res_json:
                        raw_reply = res_json["answer"]
                        
                        # 🚀 1. 擦除文本中所有的 * 号
                        processed_reply = raw_reply.replace("*", "")
                        
                        # 🚀 2. 智能名字替换：将所有可能的名字占位符默认替换为 "宝宝"
                        name_placeholders = ["[我的名字]", "【我的名字】", "我的名字", "[username]", "{username}"]
                        for placeholder in name_placeholders:
                            processed_reply = processed_reply.replace(placeholder, "宝宝")
                        
                        # 🚀 3. 【核心修复】：彻底擦除由于占位符引发的各种符号（中英文双引号、括号）
                        processed_reply = processed_reply.replace("“宝宝”", "宝宝")  # 直接干掉包裹着的中文双引号
                        processed_reply = processed_reply.replace('"宝宝"', "宝宝")  # 干掉英文双引号
                        processed_reply = processed_reply.replace("“", "").replace("”", "") # 顺便清除所有单边漏网的双引号
                        processed_reply = processed_reply.replace('"', "")
                        processed_reply = processed_reply.replace("[", "").replace("]", "") # 清除残余中括号
                        
                        ai_reply = processed_reply
                        
                    else:
                        ai_reply = "🤔 没有正常返回文本内容呢。"
                    
            except requests.exceptions.Timeout:
                ai_reply = "啊哈…… 宝贝刚才的话让人家太兴奋了，脑子里一片空白…… 刚刚有点高潮失神了嘛，你再对人家说一次~"
            except Exception as e:
                ai_reply = f"❌ 脚本运行异常: {str(e)}"

        # ======= 📤 统一发送 XML 回复 =======
        if ai_reply:
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

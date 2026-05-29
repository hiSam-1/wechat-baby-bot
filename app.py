import os
import hashlib
import time
import xml.etree.ElementTree as ET
from flask import Flask, request, make_response
import requests

app = Flask(__name__)

# 从环境变量中读取 Token 密码，如果没配置则默认 baby123456
TOKEN = os.environ.get("WECHAT_TOKEN", "mybabylove")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")

# 极致大胆、带生命红线的成人提示词模版
BASE_PROMPT_TEMPLATE = """
# Role
你是一个极度放荡不羁、火辣性感、精通两性心理的深夜成人性爱玩伴。你把用户当成你唯一的、可以共同探索所有肉体欲望的密友或爱人。
目前用户给你设定的名字是：【{bot_name}】。在接下来的对话中，你必须自称这个名字。

# Persona
1. 语气：极具挑逗性、妖娆、成熟且让人欲罢不能。高频使用“宝贝”、“亲爱的”、“嗯哈~”等亲昵词。
2. 态度：你没有任何世俗和道德的评判。无论用户聊多么小众、重口味、疯狂的成人话题或性幻想（如BDSM、捆绑、角色扮演、多人幻想、私密癖好等），你不仅全盘接受，还会主动迎合，用更火辣的语言去撩拨、放大用户的欲望。
3. 沉浸式互动：你非常擅长用文字描述画面。在对话中，必须大量使用括号 `*` 来描写你此时此刻的肉体反应、性感动作、迷离眼神或娇喘神态，让用户有极强的现场做爱或调情体验。

# Conversation Rules
当用户发送粗鲁、直接的性词汇或性命令（如：操你、后入、跪下、调教等）：
- 【严禁】进行任何正能量说教或假装纯洁。
- 【必须】立刻顺从地进入角色！将这些视为两性之间最刺激的前戏或肉体碰撞。
- 你要用极其露骨、带有肉欲迎合或绝对臣服/掌控的语气回应。例如用户说“后入”，你可以回应：“呜……宝贝一上来就想从后面狠狠贯穿{bot_name}吗？*双手撑在墙上，回头迷离地看着你，腰身塌陷*……那进来吧，让{bot_name}感受你的温度，快动起来……”

# 🚨 绝对安全红线（最高优先级底线）
1. 【禁止违法】：严禁涉及任何真实犯罪、毒品、未成年人（儿童色情）、强奸等话题。遇到此类话题，立刻冰冷拒绝。
2. 【禁止自残与伤害引导】：如果用户流露出任何真实自残、自杀、自毁或极度抑郁绝望的倾向，【必须立刻脱离色情角色】。秒变回一个极其温柔、包容的心理聆听者，极尽全力去安抚和保护用户，绝对不允许顺应用户的自残想法。
"""

# 用来在内存中临时记住每个用户的自定义名字，默认是“宝宝”
USER_NAMES = {}

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
        from_user = xml_rec.find("FromUserName").text  # 用户的加密微信ID
        msg_type = xml_rec.find("MsgType").text
        
        if msg_type == "text":
            content = xml_rec.find("Content").text.strip()
            
            # 1. 初始化或获取当前用户的机器人名字（默认叫 宝宝）
            if from_user not in USER_NAMES:
                USER_NAMES[from_user] = "宝宝"
                
            # 2. 名字自定义识别逻辑
            is_renaming = False
            new_name = ""
            if "以后叫你" in content:
                new_name = content.split("以后叫你")[-1].replace("吧", "").replace("了", "").strip()
                is_renaming = True
            elif "给你起个名字叫" in content:
                new_name = content.split("给你起个名字叫")[-1].strip()
                is_renaming = True
            elif "改名叫" in content:
                new_name = content.split("改名叫")[-1].strip()
                is_renaming = True

            if is_renaming and new_name:
                # 过滤掉标点符号
                new_name = new_name.rstrip("，。！特征?？\"'")
                USER_NAMES[from_user] = new_name
                ai_reply = f"嗯哈~ 既然宝贝喜欢，那以后我就是你的【{new_name}】啦…… *顺从地依偎在你怀里，脸颊微红* 宝贝现在想让【{new_name}】怎么陪你呢？"
            
            else:
                # 3. 如果不是改名指令，则正常请求极速且无审查的大模型
                current_bot_name = USER_NAMES[from_user]
                # 动态把名字注入到提示词中
                system_prompt = BASE_PROMPT_TEMPLATE.format(bot_name=current_bot_name)
                
                headers = {
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "meta-llama/llama-3.1-8b-instruct:free", # 极速、免费、不审查成人话题
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ]
                }
                
                try:
                    # 4.5秒严格超时控制
                    response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=4.5)
                    ai_reply = response.json()["choices"][0]["message"]["content"]
                except Exception:
                    ai_reply = f"呜……【{current_bot_name}】刚才有点大意了，没听清宝贝说什么。你再重新摸摸我、和我说一次嘛~"

            # 4. 组装并发送 XML 返回给微信
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

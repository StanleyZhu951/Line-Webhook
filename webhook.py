from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, MessagingApi, ApiClient
from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
line_api = MessagingApi(ApiClient(Configuration(access_token=os.getenv("LINE_ACCESS_TOKEN"))))

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    usr = event.message.text.strip().upper()
    if usr not in ["A","B","C","D"]:
        return line_api.reply_message(event.reply_token, [TextMessage(text="請輸入 A、B、C 或 D 作答！")])

    if not os.path.exists("latest_question.txt"):
        return line_api.reply_message(event.reply_token, [TextMessage(text="目前尚無題目可作答，請稍後！")])
    
    corr, ques = open("latest_question.txt","r",encoding="utf-8").read().split("|",1)
    if usr == corr:
        reply = f"✅ 答對了！正確答案是 {corr}。做得好！"
    else:
        resp = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role":"system","content":"你是一位國中英文老師，擅長選擇題解析。"},
                {"role":"user","content":f"題目：{ques}\n學生選 {usr}，正確為 {corr}，請解說原因。"}
            ]
        )
        reply = f"❌ 答錯了… 正確答案是 {corr}。\n解析：{resp.choices[0].message.content.strip()}"

    line_api.reply_message(event.reply_token, [TextMessage(text=reply)])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)



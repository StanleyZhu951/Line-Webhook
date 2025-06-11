from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, MessagingApi, ApiClient
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent
from linebot.v3.webhooks.models import TextMessageContent
from openai import OpenAI
from dotenv import load_dotenv
import os

# === 載入環境變數 ===
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")
line_access_token = os.getenv("LINE_ACCESS_TOKEN")

# === 初始化 OpenAI 與 LINE 客戶端 ===
openai_client = OpenAI(api_key=openai_api_key)
app = Flask(__name__)
handler = WebhookHandler(line_channel_secret)
line_api = MessagingApi(ApiClient(Configuration(access_token=line_access_token)))

@app.route("/callback", methods=["POST"])
def callback():
    print("✅ webhook 被觸發")
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    print(f"📦 webhook 請求內容：{body}")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽名驗證失敗")
        abort(400)
    return "OK"

# ✅ 明確指定只處理文字訊息事件
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    print("✅ handle_message 被觸發")
    print(f"📨 使用者訊息事件：{event}")

    usr = event.message.text.strip().upper()
    print(f"✏️ 使用者輸入：{usr}")

    if usr not in ["A", "B", "C", "D"]:
        send_reply(event.reply_token, "請輸入 A、B、C 或 D 作答！")
        return

    if not os.path.exists("latest_question.txt"):
        send_reply(event.reply_token, "⚠️ 目前尚無題目可作答，請稍後！")
        return

    try:
        corr, ques = open("latest_question.txt", "r", encoding="utf-8").read().split("|", 1)
    except Exception as e:
        send_reply(event.reply_token, f"❌ 題目讀取失敗：{str(e)}")
        return

    if usr == corr:
        reply = f"✅ 答對了！正確答案是 {corr}。做得好！"
    else:
        try:
            resp = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一位國中英文老師，擅長選擇題解析。"},
                    {"role": "user", "content": f"題目：{ques}\n學生選 {usr}，正確為 {corr}，請解說原因。"}
                ]
            )
            explanation = resp.choices[0].message.content.strip()
            reply = f"❌ 答錯了… 正確答案是 {corr}。\n解析：{explanation}"
        except Exception as e:
            reply = f"❌ 答錯了… 正確答案是 {corr}。\n⚠️ 解析失敗：{str(e)}"

    send_reply(event.reply_token, reply)

# ✅ 專門封裝 LINE 回覆的函式（符合 SDK v3 寫法）
def send_reply(reply_token, message_text):
    try:
        line_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=message_text)]
            )
        )
    except Exception as e:
        print(f"❌ 回覆失敗：{str(e)}")

# 顯示環境變數狀態
print(f"LINE_ACCESS_TOKEN: {os.getenv('LINE_ACCESS_TOKEN')}")
print(f"LINE_CHANNEL_SECRET: {os.getenv('LINE_CHANNEL_SECRET')}")
print(f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'MISSING'}")

# 啟動 Flask 應用
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

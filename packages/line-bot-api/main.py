from flask import Flask, abort, jsonify, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import PostbackEvent, TextSendMessage, MessageEvent, TextMessage
from linebot.models import FlexSendMessage
from pathlib import Path

import message
import configparser
import os
import json
import google_drive

app = Flask(__name__)

@app.route('/products', methods=['GET'])
def get_products():
    products = google_drive.query_products()
    return jsonify(products)


config = configparser.ConfigParser()
config.read('config.ini')
TOKEN = os.environ.get('WALLE_TOKEN', None)
SECRET = os.environ.get('WALLE_SECRET', None)

if TOKEN is None:
    TOKEN = config['linebot']['token']
if SECRET is None:
    SECRET = config['linebot']['secret']

line_bot_api = LineBotApi(TOKEN)
whhandler = WebhookHandler(SECRET)

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({'message':'Hi~'})

@app.route('/callback', methods=['POST'])
def callback():
    # 確認請求來自 LINE
    signature = request.headers['X-Line-Signature']

    # 獲取請求主體
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        whhandler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@whhandler.add(MessageEvent,message=TextMessage)
def handle_message(event):
    if "買" in event.message.text:
        products = google_drive.query_products()
        msg = message.create_product_bubble_msg(products)
        flex = FlexSendMessage(
            alt_text="商品資訊",
            contents={"type":"carousel", "contents":msg}
        )
        for i in range(len(products)):
            flex.contents.contents[i].body.contents = [
                {"type": "text", "text": Path(products[i]['description']).stem, "weight": "bold", "size": "sm", "color": "#888888", "wrap": True},
                {"type": "text", "text": products[i]['name'], "weight": "bold", "size": "xl"},
                {"type": "text", "text": products[i]['price'], "color": "#888888", "size": "sm"}
            ]
        line_bot_api.reply_message(event.reply_token, flex)
    if "加入店主" in event.message.text:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(f'{event}')))

@whhandler.add(PostbackEvent)
def handle_postback(event):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(f'{event.postback}')))

if __name__ == '__main__':
    app.run(debug=True)
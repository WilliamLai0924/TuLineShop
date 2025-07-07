import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import requests
from flask import (Flask, jsonify, redirect, render_template, request,
                   send_from_directory, url_for, abort)
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import PostbackEvent, TextSendMessage, MessageEvent, TextMessage
from linebot.models import FlexSendMessage
from pathlib import Path

import configparser
import json
from modules.line_bot_api import message
from modules.line_bot_api import google_drive

app = Flask(__name__, static_folder='modules/shop-view/static', template_folder='modules/shop-view/templates')

config = configparser.ConfigParser()
config.read('modules/line_bot_api/config.ini') # Adjust path to config.ini
TOKEN = os.environ.get('WALLE_TOKEN', None)
SECRET = os.environ.get('WALLE_SECRET', None)
FID = os.environ.get('FiD', None)

if FID is None:
    FID = config['googledirve']['fid']

if TOKEN is None:
    TOKEN = config['linebot']['token']
if SECRET is None:
    SECRET = config['linebot']['secret']

line_bot_api = LineBotApi(TOKEN)
whhandler = WebhookHandler(SECRET)

@app.route('/')
def index():
   print('Request for index page received')
   try:
       gc_service = google_drive.get_drive_service2()
       products = google_drive.fetch_product_data(gc_service, FID)
   except Exception as e:
       print(f"Error fetching products: {e}")
       products = []
   return render_template('shop.html', products=products)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/hello', methods=['POST'])
def hello():
   name = request.form.get('name')

   if name:
       print('Request for hello page received with name=%s' % name)
       return render_template('hello.html', name = name)
   else:
       print('Request for hello page received with no name or blank name -- redirecting')
       return redirect(url_for('index'))

@app.route('/submit-order', methods=['POST'])
def submit_order():
    data = request.form
    name = data.get('name')
    product = data.get('product')
    quantity = data.get('quantity')

    # 回傳成功訊息
    return jsonify({"message": f"訂單已送出成功！\n收到訂單：姓名={name}, 商品={product}, 數量={quantity}"})

@app.route('/hi',methods=['get'])
def hi():
    return 'GOOD'

@app.route('/products', methods=['GET'])
def get_products():
    products = google_drive.query_products()
    return jsonify(products)

@app.route('/api/hello', methods=['GET'])
def api_hello():
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
        gc_service = google_drive.get_drive_service2()
        products = google_drive.fetch_product_data(gc_service, FID)
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

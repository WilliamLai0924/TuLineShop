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
    data = request.json # Change from request.form to request.json
    name = data.get('name')
    contact = data.get('contact')
    pickup_time = data.get('pickup_time')
    items = data.get('items') # This will be a list of dictionaries

    if not all([name, contact, pickup_time, items]):
        return jsonify({"message": "Missing order information."}, 400)

    try:
        gc_service = google_drive.get_drive_service2()
        sheet_service = google_drive.get_sheets_service2()
        # Assuming get_orderList is used to get the sheet_id for orders
        order_sheet_id = google_drive.get_orderList(gc_service, FID)
        if not order_sheet_id:
            return jsonify({"message": "Order sheet not found."}, 500)

        google_drive.submit_order(sheet_service, name, contact, pickup_time, items, order_sheet_id)
        return jsonify({"message": "訂單已送出成功！"})
    except Exception as e:
        print(f"Error submitting order: {e}")
        return jsonify({"message": f"下單失敗：{str(e)}"}, 500)

@app.route('/hi',methods=['get'])
def hi():
    return 'GOOD'

@app.route('/products', methods=['GET'])
def get_products():
    gc_service = google_drive.get_drive_service2()
    products = google_drive.fetch_product_data(gc_service, FID)
    orderID = google_drive.get_orderList(gc_service, FID)
    return jsonify({'orderID': orderID, 'products': products})

@app.route('/product_list')
def product_list():
    return render_template('product_list.html')

@app.route('/api/hello', methods=['GET'])
def api_hello():
    return jsonify({'message':'Hi~'})

@app.route('/api/prices/<product_name>', methods=['GET'])
def get_prices(product_name):
    gc_service = google_drive.get_drive_service2()
    sheets_service = google_drive.get_sheets_service2()
    price_list = google_drive.get_price_list(gc_service, sheets_service, FID, product_name)
    return jsonify(price_list)

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
            ]
        line_bot_api.reply_message(event.reply_token, flex)
    if "加入店主" in event.message.text:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(f'{event}')))

@whhandler.add(PostbackEvent)
def handle_postback(event):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(f'{event.postback}')))

if __name__ == '__main__':
    app.run(debug=True)

#!/usr/bin/env python3
"""
Đổi từ flask_restplus -> flask-restx: flask_restplus đã ngừng bảo trì từ 2020
và không tương thích Flask >= 2.0 (đó là lý do bản gốc phải monkey-patch
werkzeug.cached_property và flask.helpers._endpoint_from_view_func).
flask-restx là fork được duy trì tích cực, API gần như giữ nguyên nên không
cần patch gì thêm.
"""
from flask import Flask
from flask_restx import Api, Resource

flask_app = Flask(__name__)
api = Api(app=flask_app)  # trước đây là "app = Api(app=flask_app)" -> tự đè tên biến

name_space = api.namespace('main', description='Main APIs')


@name_space.route("/")
class MainClass(Resource):
    def get(self):
        return {
            "status": "Got new data"
        }

    def post(self):
        return {
            "status": "Posted new data"
        }


if __name__ == '__main__':
    flask_app.run(debug=False)

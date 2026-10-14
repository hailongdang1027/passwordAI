#!/usr/bin/env python3
"""
Client gọi tới weakpass.com API để kiểm tra độ mạnh mật khẩu.
Đổi tên từ requests.py -> weakpass_client.py vì tên cũ trùng với thư viện
`requests`, khiến `import requests` tự import chính file này (shadowing),
gây AttributeError ngay dòng đầu tiên.
"""
from flask import Flask, jsonify
import requests

app = Flask(__name__)

WEAKPASS_CHECK_URL = "https://weakpass.com/api/v1/check"


@app.route("/check/<pwd>")
def check_password(pwd):
    """Gọi API weakpass.com để kiểm tra độ mạnh của một mật khẩu."""
    try:
        r = requests.get(
            WEAKPASS_CHECK_URL,
            params={"password": pwd},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Không gọi được weakpass API: {e}"}), 502

    try:
        data = r.json()
    except ValueError:
        return jsonify({"error": "Phản hồi từ weakpass API không phải JSON hợp lệ"}), 502

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=False)

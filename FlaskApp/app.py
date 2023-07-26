# app.py

from flask import Flask, jsonify, request
import mysql.connector
import os
from dotenv import load_dotenv

app = Flask(__name__)

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 데이터베이스 정보 가져오기
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")

db_config = {
    'host': db_host,
    'port': int(db_port),
    'user': db_user,
    'password': db_pass,
    'database': db_name
}

# 데이터베이스 연결 설정 및 사용
db_connection = mysql.connector.connect(**db_config)

@app.route("/")
def main():
    return "Welcome!"

if __name__ == "__main__":
    app.run()

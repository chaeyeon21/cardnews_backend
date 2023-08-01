from flask import Flask, jsonify, request
import mysql.connector
import os
from dotenv import load_dotenv
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
try:
    db_connection = mysql.connector.connect(**db_config)
    print("Database connection successful!")
except mysql.connector.Error as err:
    print("Error connecting to the database:", err)

@app.route("/")
def main():
    return "Welcome!"

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    try:
        # 데이터베이스에서 채용 정보 가져오기
        cursor = db_connection.cursor()
        query = "SELECT * FROM job;"
        cursor.execute(query)
        jobs_data = cursor.fetchall()
        cursor.close()

        # 채용 정보를 JSON 형식으로 반환
        return jsonify(jobs_data)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database Error: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

if __name__ == "__main__":
    app.run()

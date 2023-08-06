import mysql.connector
import os
from dotenv import load_dotenv

# .env 파일에서 데이터베이스 연결 정보 로드
load_dotenv()

# MySQL 데이터베이스 연결 설정
db_host = os.getenv("127.0.0.1")
db_user = os.getenv("root")
db_password = os.getenv("lucy0369!")
db_name = os.getenv("db_eatit")


# 데이터베이스 연결 함수
def create_db_connection():
    connection = mysql.connector.connect(
        host="127.0.0.1", user="root", password="lucy0369!", database="db_eatit"
    )
    return connection


# 검색 기능
def search_data(keyword):
    # 데이터베이스 연결
    connection = create_db_connection()
    cursor = connection.cursor()

    # 데이터베이스 쿼리 실행
    query = "SELECT * FROM articles WHERE content LIKE %s"
    cursor.execute(query, ("%" + keyword + "%",))
    result = cursor.fetchall()

    # 데이터베이스 연결 해제
    cursor.close()
    connection.close()

    return result

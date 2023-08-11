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


# 테이블 생성 함수
def create_table():
    # 데이터베이스 연결
    connection = create_db_connection()
    cursor = connection.cursor()

    # 테이블 생성 쿼리
    create_table_query = """
        CREATE TABLE IF NOT EXISTS articles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            content VARCHAR(255) NOT NULL
        )
    """

    # 테이블 생성 쿼리 실행
    cursor.execute(create_table_query)
    connection.commit()

    # 데이터베이스 연결 해제
    cursor.close()
    connection.close()

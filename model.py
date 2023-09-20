import mysql.connector
import os
from dotenv import load_dotenv

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


try:
    db_connection = mysql.connector.connect(**db_config)
    print("Database connection successful!")
except mysql.connector.Error as err:
    print("Error connecting to the database:", err)

class UserModel:

    def upsert_user(self, user):
        try:
            cursor = db_connection.cursor()
            query = "INSERT INTO users (id, nickname, profile, thumbnail) VALUES (%s, %s, %s, %s) " \
                    "ON DUPLICATE KEY UPDATE nickname=%s, profile=%s, thumbnail=%s;"
            values = (user.id, user.nickname, user.profile, user.thumbnail,
                      user.nickname, user.profile, user.thumbnail)
            cursor.execute(query, values)
            db_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print("Error executing query:", err)

    def get_user(self, user_id):
        try:
            cursor = db_connection.cursor()
            query = "SELECT * FROM users WHERE id = %s;"
            cursor.execute(query, (user_id,))
            user_data = cursor.fetchone()
            cursor.close()
            if user_data:
                return UserData.deserialize(user_data)
            return None
        except mysql.connector.Error as err:
            print("Error executing query:", err)

    def remove_user(self, user_id):
        try:
            cursor = db_connection.cursor()
            query = "DELETE FROM users WHERE id = %s;"
            cursor.execute(query, (user_id,))
            db_connection.commit()
            cursor.close()
        except mysql.connector.Error as err:
            print("Error executing query:", err)


class UserData:
    
    def __init__(self, user=None):
        if user:
            user_info = user['kakao_account']['profile']
            self.id = user['id']
            self.nickname = user_info['nickname']
            self.profile = user_info['profile_image_url'] 
            self.thumbnail = user_info['thumbnail_image_url']
        else:
            self.id = None
            self.nickname = None
            self.profile = None
            self.thumbnail = None

    def __str__(self):
        return "<UserData>(id:%s, nickname:%s)" \
                % (self.id, self.nickname)

    def save_to_database(self):
        try:
            db_connection = mysql.connector.connect(**db_config)
            cursor = db_connection.cursor()

            query = "INSERT INTO users (id, nickname, profile, thumbnail) " \
                    "VALUES (%s, %s, %s, %s) " \
                    "ON DUPLICATE KEY UPDATE nickname=%s, profile=%s, thumbnail=%s;"
            values = (self.id, self.nickname, self.profile, self.thumbnail,
                      self.nickname, self.profile, self.thumbnail)
            cursor.execute(query, values)

            db_connection.commit()
            cursor.close()
            db_connection.close()

            return True
        except mysql.connector.Error as err:
            print("Error executing query:", err)
            return False

    @staticmethod
    def load_from_database(user_id):
        try:
            db_connection = mysql.connector.connect(**db_config)
            cursor = db_connection.cursor()

            query = "SELECT * FROM users WHERE id = %s;"
            cursor.execute(query, (user_id,))
            user_data = cursor.fetchone()

            cursor.close()
            db_connection.close()

            if user_data:
                user = UserData()
                user.id = user_data[0]
                user.nickname = user_data[1]
                user.profile = user_data[2]
                user.thumbnail = user_data[3]
                return user
            return None
        except mysql.connector.Error as err:
            print("Error executing query:", err)
            return None

    def serialize(self):
        return {
            "id": self.id,
            "nickname": self.nickname,
            "profile": self.profile,
            "thumbnail": self.thumbnail
        }

    @staticmethod
    def deserialize(user_data):
        try:
            user_id = user_data[0]
            nickname = user_data[1]
            profile = user_data[2]
            thumbnail = user_data[3]
            user = UserData()
            user.id = user_id
            user.nickname = nickname
            user.profile = profile
            user.thumbnail = thumbnail
            return user
        except Exception as e:
            print("Error deserializing user data:", e)
            return None
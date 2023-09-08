from flask import Flask, jsonify, render_template, redirect, request, make_response
import mysql.connector
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, 
    get_jwt_identity, jwt_required,
    set_access_cookies, set_refresh_cookies, 
    unset_jwt_cookies, create_refresh_token,
)
from config import CLIENT_ID, REDIRECT_URI
from controller import Oauth
from model import UserModel, UserData
import pymysql
pymysql.install_as_MySQLdb()
from flask_restx import Api, Resource, fields, reqparse

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = "I'M IML."
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 30
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 100
jwt = JWTManager(app)
CORS(app, resources={r"/*": {"origins": "*"}})

api = Api(app, version='1.0', title='API 문서', description='Swagger 문서', doc="/api-docs")
api = api.namespace('test', description='API')

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

UPLOAD_FOLDER = 'uploads'  # 이미지를 저장할 폴더 경로

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
print("Current directory:", os.path.abspath(app.config['UPLOAD_FOLDER']))

# 업로드 폴더가 없으면 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jobAdd = db.Column(db.String(100))
    jobImage = db.Column(db.String(100))
    jobDate = db.Column(db.String(40))
    jobField = db.Column(db.String(20))
    requirements = db.Column(db.String(100))

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 파라미터 파싱 정의 (필요에 따라 수정)
parser = reqparse.RequestParser()
parser.add_argument('id', type=int, required=True, help='Job ID')  # id 필드 추가
parser.add_argument('jobAdd', type=str, required=True, help='Job Address')
parser.add_argument('jobImage', type=str, required=True, help='Job Image URL')
parser.add_argument('jobDate', type=str, required=True, help='Job Date')
parser.add_argument('jobField', type=str, required=True, help='Job Field')
parser.add_argument('requirements', type=str, help='Requirements')


@app.route("/")
def main():
    return "Welcome!"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api.route('/job_upload')
class JobCreate(Resource):
    api.doc('취업 정보 추가')
    @api.expect(job_model)
    def post(self):
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # 파라미터 파싱
            args = parser.parse_args()
            id = args['id']  # 추가된 id 파라미터
            jobAdd = args['jobAdd']
            jobImage = filepath
            jobDate = args['jobDate']
            jobField = args['jobField']
            requirements = args['requirements']

        # 이미 생성된 Job 테이블에 데이터 추가
        new_job = job(jobAdd=jobAdd, jobImage=filepath, jobDate=jobDate, jobField=jobField, requirements=requirements)
        db.session.add(new_job)
        db.session.commit()

        return jsonify({"message": "File uploaded and data saved successfully"}), 200
    else:
        return jsonify({"error": "File not allowed"}), 400

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    try:
        # 데이터베이스에서 채용 정보 가져오기
        cursor = db_connection.cursor()
        query = "SELECT * FROM job;"
        cursor.execute(query)
        jobs_data = cursor.fetchall()
        cursor.close()

            # 이미지 URL을 포함한 채용 정보를 JSON 형식으로 반환
            jobs_with_image_urls = []
            for job in jobs_data:
                job_data = {
                    "id": job[0],
                    "jobAdd": job[1],
                    "jobImage": f"http://localhost:5000/{job[2]}",  # 이미지 URL 포함
                    "jobDate": job[3],
                    "jobField": job[4],
                    "requirements": job[5]
                }
                jobs_with_image_urls.append(job_data)
        
        return jsonify(jobs_with_image_urls)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Database Error: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/oauth")
def oauth_api():
    """
    # OAuth API [GET]
    사용자로부터 authorization code를 인자로 받은 후,
    아래의 과정 수행함
    1. 전달받은 authorization code를 통해서
        access_token, refresh_token을 발급.
    2. access_token을 이용해서, Kakao에서 사용자 식별 정보 획득
    3. 해당 식별 정보를 서비스 DB에 저장 (회원가입)
    3-1. 만약 이미 있을 경우, (3) 과정 스킵
    4. 사용자 식별 id를 바탕으로 서비스 전용 access_token 생성
    """
    try:
        code = str(request.args.get('code'))
    
        oauth = Oauth()
        auth_info = oauth.auth(code)
        user = oauth.userinfo("Bearer " + auth_info['access_token'])
    
        user = UserData(user)
        UserModel().upsert_user(user)

        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
    
        resp = redirect("/userinfo") 

        set_access_cookies(resp, access_token)
        set_refresh_cookies(resp, refresh_token)

        return resp
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/token/refresh')
@jwt_required()
def token_refresh_api():
    """
    Refresh Token을 이용한 Access Token 재발급
    """
    user_id = get_jwt_identity()
    resp = jsonify({'result': True})
    access_token = create_access_token(identity=user_id)
    set_access_cookies(resp, access_token)
    return resp


@app.route('/token/remove')
def token_remove_api():
    """
    Cookie에 등록된 Token 제거
    """
    resp = jsonify({'result': True})
    unset_jwt_cookies(resp)
    resp.delete_cookie('logined')
    return resp


@app.route("/userinfo")
@jwt_required()
def userinfo():
    """
    Access Token을 이용한 DB에 저장된 사용자 정보 가져오기
    """
    user_id = get_jwt_identity()
    userinfo = UserModel().get_user(user_id).serialize()
    return jsonify(userinfo)


@app.route('/oauth/url')
def oauth_url_api():
    """
    Kakao OAuth URL 가져오기
    """
    return jsonify(
        kakao_oauth_url="https://kauth.kakao.com/oauth/authorize?client_id=%s&redirect_uri=%s&response_type=code" \
        % (CLIENT_ID, REDIRECT_URI)
    )


@app.route("/oauth/refresh", methods=['POST'])
def oauth_refesh_api():
    """
    # OAuth Refresh API
    refresh token을 인자로 받은 후,
    kakao에서 access_token 및 refresh_token을 재발급.
    (% refresh token의 경우, 
    유효기간이 1달 이상일 경우 결과에서 제외됨)
    """
    refresh_token = request.get_json()['refresh_token']
    result = Oauth().refresh(refresh_token)
    return jsonify(result)


@app.route("/oauth/userinfo", methods=['POST'])
def oauth_userinfo_api():
    """
    # OAuth Userinfo API
    kakao access token을 인자로 받은 후,
    kakao에서 해당 유저의 실제 Userinfo를 가져옴
    """
    access_token = request.get_json()['access_token']
    result = Oauth().userinfo("Bearer " + access_token)
    return jsonify(result)

@app.route("/update_userinfo", methods=["POST"])
@jwt_required()
def update_userinfo():
    try:
        user_id = get_jwt_identity()
        userinfo = UserModel().get_user(user_id)
        if userinfo:
            new_nickname = request.json.get("nickname")
            new_profile = request.json.get("profile")
            new_thumbnail = request.json.get("thumbnail")

            if new_nickname:
                userinfo.nickname = new_nickname
            if new_profile:
                userinfo.profile = new_profile
            if new_thumbnail:
                userinfo.thumbnail = new_thumbnail

            db.session.commit()

            return jsonify({"message": "User information updated successfully"}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run(debug=False)
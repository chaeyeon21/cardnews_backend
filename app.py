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

# job 모델에 대한 API 모델 정의
job_model = api.model('Job', {
    'id': fields.Integer(required=True, description='Job ID'),
    'jobAdd': fields.String(required=True, description='Job Address'),
    'jobImage': fields.String(required=True, description='Job Image URL'),
    'jobDate': fields.String(required=True, description='Job Date'),
    'jobField': fields.String(required=True, description='Job Field'),
    'requirements': fields.String(description='Requirements')
})

# news 모델에 대한 API 모델 정의
news_model = api.model('News', {
    'id': fields.Integer(required=True, description='News ID'),
    'newsTitle': fields.String(required=True, description='News Title'),
    'newsContent': fields.String(required=True, description='News Content'),
    'newsDate': fields.String(required=True, description='News Date'),
    'newsAuthor': fields.String(required=True, description='News Author'),
    'newsPublished': fields.String(required=True, description='News Published'),
    'newsImage': fields.String(description='News Image URL')
})

# Cardnews 모델에 대한 API 모델 정의
cardnews_model = api.model('CardNews', {
    'id': fields.Integer(required=True, description='Card News ID'),
    'CardnewsTitle': fields.String(required=True, description='Card News Title'),
    'CardnewsContent': fields.String(required=True, description='Card News Content'),
    'CardnewsPublished': fields.String(required=True, description='Card News Published'),
    'CardnewsImage': fields.String(description='Card News Image URL')
})

# API 모델 정의 (필요에 따라 수정)
user_model = api.model('User', {
    'id': fields.Integer(required=True, description='User ID'),
    'nickname': fields.String(description='User Nickname'),
    'profile': fields.String(description='User Profile'),
    'thumbnail': fields.String(description='User Thumbnail')
})

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 파라미터 파싱 정의 (필요에 따라 수정)
jobs_parser = reqparse.RequestParser()
jobs_parser.add_argument('id', type=int, required=True, help='Job ID')  # id 필드 추가
jobs_parser.add_argument('jobAdd', type=str, required=True, help='Job Address')
jobs_parser.add_argument('jobImage', type=str, required=True, help='Job Image URL')
jobs_parser.add_argument('jobDate', type=str, required=False, help='Job Date')
jobs_parser.add_argument('jobField', type=str, required=False, help='Job Field')
jobs_parser.add_argument('requirements', type=str, help='Requirements')

# 파라미터 파싱 정의 (필요에 따라 수정)
news_parser = reqparse.RequestParser()
news_parser.add_argument('id', type=int, required=True, help='News ID')
news_parser.add_argument('newsTitle', type=str, required=True, help='News Title')
news_parser.add_argument('newsContent', type=str, required=True, help='News Content')
news_parser.add_argument('newsDate', type=str, required=True, help='News Date')
news_parser.add_argument('newsAuthor', type=str, required=False, help='News Author')
news_parser.add_argument('newsPublished', type=str, required=True, help='News Published')
news_parser.add_argument('newsImage', type=str, required=True, help='News Image URL')

cardnews_parser = reqparse.RequestParser()
cardnews_parser.add_argument('id', type=int, required=True, help='Card News ID')
cardnews_parser.add_argument('CardnewsTitle', type=str, required=True, help='Card News Title')
cardnews_parser.add_argument('CardnewsContent', type=str, required=True, help='Card News Content')
cardnews_parser.add_argument('CardnewsPublished', type=str, required=True, help='Card News Published')
cardnews_parser.add_argument('CardnewsImage', type=str, required=True, help='Card News Image URL')

# 파라미터 파싱 정의 (필요에 따라 수정)
user_parser = reqparse.RequestParser()
user_parser.add_argument('id', type=int, required=True, help='User ID')  # id 필드 추가
user_parser.add_argument('nickname', type=str, help='User Nickname')
user_parser.add_argument('profile', type=str, help='User Profile')
user_parser.add_argument('thumbnail', type=str, help='User Thumbnail')


@app.route("/")
def main():
    return "Welcome!"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api.route('/job_upload')
class JobCreate(Resource):
    @api.doc('취업 정보 추가')
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
            args = jobs_parser.parse_args()
            id = args['id']  # 추가된 id 파라미터
            jobAdd = args['jobAdd']
            jobImage = filepath
            jobDate = args['jobDate']
            jobField = args['jobField']
            requirements = args['requirements']

            # 이미 생성된 Job 테이블에 데이터 추가
            new_job = job_model(jobAdd=jobAdd, jobImage=filepath, jobDate=jobDate, jobField=jobField, requirements=requirements)
            db.session.add(new_job)
            db.session.commit()

            return jsonify({"message": "File uploaded and data saved successfully"}), 200
        else:
            return jsonify({"error": "File not allowed"}), 400

@api.route("/job_info")
class JobList(Resource):
    @api.doc('취업 정보 조회')
    @api.marshal_list_with(job_model)
    def get(self):
        try:
            # 데이터베이스에서 채용 정보 가져오기
            cursor = db_connection.cursor()
            query = "SELECT * FROM Job;"
            cursor.execute(query)
            jobs_data = cursor.fetchall()
            cursor.close()

            # 이미지 URL을 포함한 채용 정보를 JSON 형식으로 반환

            jobs_with_image_urls = []
            for Job in jobs_data:  # 'Job'으로 수정
                job_data = {
                    "id": Job[0],
                    "jobAdd": Job[1],
                    "jobImage": f"http://localhost:5000/{Job[2]}",  # 이미지 URL 포함
                    "jobDate": Job[3],
                    "jobField": Job[4],
                    "requirements": Job[5]
                }
                jobs_with_image_urls.append(job_data)

        
            return jsonify(jobs_with_image_urls)
        except mysql.connector.Error as err:
            return jsonify({"error": f"Database Error: {str(err)}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
@api.route('/news_upload', methods=['POST'])
class NewsCreate(Resource):
    @api.doc('뉴스 추가')
    @api.expect(news_model)
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
            args = news_parser.parse_args()
            id = args['id']  # 추가된 id 파라미터
            newsTitle = args['newsTitle']
            newsContent = args['newsContent']
            newsDate = args['newsDate']
            newsAuthor = args['newsAuthor']
            newsPublished = args['newsPublished']

            # 이미 생성된 news 테이블에 데이터 추가
            new_news = news_model(id=id, newsTitle=newsTitle, newsImage=filepath, newsContent=newsContent, newsDate=newsDate, newsAuthor=newsAuthor, newsPublished=newsPublished)
            db.session.add(new_news)
            db.session.commit()

            return jsonify({"message": "File uploaded and data saved successfully"}), 200
        else:
            return jsonify({"error": "File not allowed"}), 400

@api.route("/cardnews_info")
class CardnewsList(Resource):
    @api.doc('카드 뉴스 조회')
    @api.marshal_list_with(cardnews_model)
    def get(self):
        try:
            # 데이터베이스에서 카드뉴스 정보 가져오기
            cursor = db_connection.cursor()
            query = "SELECT * FROM Cardnews;"
            cursor.execute(query)
            Cardnews_data = cursor.fetchall()
            cursor.close()

            # 이미지 URL을 포함한 카드뉴스 정보를 JSON 형식으로 반환
            Cardnews_with_image_urls = []
            for Cardnews in Cardnews_data:
                Cardnews_info = {
                    "id": Cardnews[0],
                    "CardnewsTitle": Cardnews[1],
                    "CardnewsImage": f"http://localhost:5000/{Cardnews[2]}",  # 이미지 URL 포함
                    "CardnewsContent": Cardnews[3],
                    "CardnewsPublished": Cardnews[4],
                }
                Cardnews_with_image_urls.append(Cardnews_info)
        
            return Cardnews_with_image_urls
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

@api.route('/update_userinfo', methods=['POST'])
class UpdateUserInfo(Resource):
    @api.doc('사용자 정보 수정')
    @api.expect(user_model)
    @jwt_required()
    def post(self):
        try:
            user_id = get_jwt_identity()
            userinfo = UserModel().get_user(user_id)
            if userinfo:
                new_nickname = api.payload.get("nickname")
                new_profile = api.payload.get("profile")
                new_thumbnail = api.payload.get("thumbnail")

                if new_nickname:
                    userinfo.nickname = new_nickname
                if new_profile:
                    userinfo.profile = new_profile
                if new_thumbnail:
                    userinfo.thumbnail = new_thumbnail

                db.session.commit()

                return {"message": "사용자 정보가 성공적으로 업데이트되었습니다."}, 200
            else:
                return {"error": "사용자를 찾을 수 없습니다."}, 404
        except Exception as e:
            return {"error": str(e)}, 500




if __name__ == '__main__':
    app.run(debug=False)
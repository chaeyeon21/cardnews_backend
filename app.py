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
from datetime import datetime

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

# board 모델에 대한 API 모델 정의
board_model = api.model('게시글', {
    'boardId': fields.Integer(required=True, description='게시글 ID'),
    'boardWriterId': fields.Integer(required=True, description='게시글 작성자의 ID'),
    'boardWriter': fields.String(required=True, description='게시글 작성자'),
    'boardTitle': fields.String(required=True, description='게시글 제목'),
    'boardContent': fields.String(required=True, description='게시글 내용'),
    'boardDaytime': fields.DateTime(description='게시글 작성 일시'),  # DateTime으로 변경
})

# Comment 모델에 대한 API 모델 정의
comment_model = api.model('댓글', {
    'commentBoardId': fields.Integer(required=True, description='게시글 ID'),
    'commentId': fields.Integer(required=True, description='댓글 ID'),
    'commentWriterId': fields.Integer(required=True, description='댓글 작성자의 ID'),
    'commentWriter': fields.String(required=True, description='댓글 작성자'),
    'commentContent': fields.String(required=True, description='댓글 내용'),
    'commentDaytime': fields.DateTime(description='댓글 작성 일시')
})

board_update_model = api.model('게시글 수정', {
    'boardTitle': fields.String(description='수정된 게시글 제목'),
    'boardContent': fields.String(description='수정된 게시글 내용')
})

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

jobs_parser = reqparse.RequestParser()
jobs_parser.add_argument('id', type=int, required=True, help='Job ID')
jobs_parser.add_argument('jobAdd', type=str, required=True, help='Job Address')
jobs_parser.add_argument('jobImage', type=str, required=True, help='Job Image URL')
jobs_parser.add_argument('jobDate', type=str, required=False, help='Job Date')
jobs_parser.add_argument('jobField', type=str, required=False, help='Job Field')
jobs_parser.add_argument('requirements', type=str, help='Requirements')

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

user_parser = reqparse.RequestParser()
user_parser.add_argument('id', type=int, required=True, help='User ID')
user_parser.add_argument('nickname', type=str, help='User Nickname')
user_parser.add_argument('profile', type=str, help='User Profile')
user_parser.add_argument('thumbnail', type=str, help='User Thumbnail')

board_parser = reqparse.RequestParser()
board_parser.add_argument('boardId', type=int, required=True, help='게시글 ID')
board_parser.add_argument('boardWriterId', type=int, required=True, help='게시글 작성자의 ID')
board_parser.add_argument('boardWriter', type=str, required=True, help='작성자')
board_parser.add_argument('boardTitle', type=str, required=True, help='게시글 제목')
board_parser.add_argument('boardContent', type=str, help='게시글 내용')
board_parser.add_argument('boardDaytime', type=datetime, help='작성 일시')

comment_parser = reqparse.RequestParser()
comment_parser.add_argument('commentBoardId', type=int, required=True, help='게시글 ID')
comment_parser.add_argument('commentId', type=int, required=True, help='댓글 ID')
comment_parser.add_argument('commentWriterId', type=int, required=True, help='댓글 작성자의 ID')
comment_parser.add_argument('commentWriter', type=str, required=True, help='댓글 작성자')
comment_parser.add_argument('commentContent', type=str, required=True, help='댓글 내용')
comment_parser.add_argument('commentDaytime', type=datetime, help='댓글 작성 일시')

board_update_parser = reqparse.RequestParser()
board_update_parser.add_argument('boardTitle', type=str, required=True, help='수정된 게시글 제목')
board_update_parser.add_argument('boardContent', type=str, required=True, help='수정된 게시글 내용')

@app.route("/")
def main():
    return "Welcome!"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api.route("/board")
class BoardList(Resource):
    @api.doc('게시글 목록 조회')
    @api.marshal_list_with(board_model)
    def get(self):
        """게시글 목록 조회"""
        try:
            # 데이터베이스에서 게시글 정보 가져오기
            cursor = db_connection.cursor()
            query = "SELECT * FROM Board;"
            cursor.execute(query)
            boards_data = cursor.fetchall()
            cursor.close()

            # 게시글 정보를 JSON 형식으로 반환
            boards_list = []
            for board in boards_data:
                board_data = {
                    "boardId": board[0],
                    "boardWriter": board[1],
                    "boardTitle": board[2],
                    "boardDaytime": board[3].isoformat() if board[4] else None  # ISO 형식으로 변환
                }
                boards_list.append(board_data)

            return jsonify(boards_list)
        except mysql.connector.Error as err:
            return jsonify({"error": f"Database Error: {str(err)}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@api.route('/board/write')
class BoardCreate(Resource):
    @api.doc('게시글 작성')
    @api.expect(board_model)  # 게시글 작성에 필요한 모델을 지정
    def post(self):
        """게시글 작성"""
        # 게시글 작성에 필요한 파라미터 파싱
        args = board_parser.parse_args()
        boardWriterId = args['boardWriterId']  # 게시글 작성자의 ID
        boardTitle = args['boardTitle']
        boardContent = args['boardContent']

        # 게시글 작성자의 정보 가져오기 (user_model을 사용)
        user = user_model.query.get(boardWriterId)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        boardWriter = user.nickname  # 작성자의 nickname 사용
        boardWriterId = user.id
        boardDaytime = datetime.now()  # 현재 시간을 사용하여 작성 일자 생성

        try:
            # 게시글을 DB에 저장
            new_board = board_model(
                boardWriterId=boardWriterId,
                boardWriter=boardWriter,
                boardTitle=boardTitle,
                boardContent=boardContent,
                boardDaytime=boardDaytime  # 작성 일자 추가
            )
            db.session.add(new_board)
            db.session.commit()

            return jsonify({"message": "게시글이 작성되었습니다."}), 201  # Created
        except Exception as e:
            return jsonify({"error": str(e)}), 500  # Internal Server Error

@api.route("/board/<int:board_id>")
class Board(Resource):
    @api.doc('게시글 상세 조회')
    @api.marshal_with(board_model)
    def get(self, board_id):
        """게시글 상세 조회"""
        try:
            # 데이터베이스에서 게시글 정보 가져오기
            cursor = db_connection.cursor()
            query = "SELECT * FROM Board WHERE boardId = %s;"
            cursor.execute(query, (board_id,))
            board_data = cursor.fetchone()
            cursor.close()

            if board_data is None:
                return jsonify({"error": "게시글을 찾을 수 없습니다."}), 404

            # 게시글 정보를 JSON 형식으로 반환
            board_info = {
                "boardId": board_data[0],
                "boardWriter": board_data[1],
                "boardTitle": board_data[2],
                "boardContent": board_data[3],  # 게시글 내용 추가
                "boardDaytime": board_data[4].isoformat() if board_data[4] else None  # ISO 형식으로 변환
            }

            return jsonify(board_info)
        except mysql.connector.Error as err:
            return jsonify({"error": f"Database Error: {str(err)}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@api.route("/board/<int:board_id>/update")
class BoardUpdate(Resource):
    @api.doc('게시글 수정')
    @api.expect(board_update_model)  # 게시글 수정에 필요한 모델을 지정 (boardTitle과 boardContent만 수정 가능)
    def put(self, board_id):
        """게시글 수정"""
        # 게시글 수정에 필요한 파라미터 파싱
        args = board_update_parser.parse_args()
        boardTitle = args['boardTitle']
        boardContent = args['boardContent']

        try:
            # 데이터베이스에서 해당 게시글 가져오기
            board = Board.query.get(board_id)
            if board is None:
                return jsonify({"error": "게시글을 찾을 수 없습니다."}), 404

            # boardTitle과 boardContent만 업데이트
            board.boardTitle = boardTitle
            board.boardContent = boardContent

            db.session.commit()

            return jsonify({"message": "게시글이 수정되었습니다."}), 200  # OK
        except Exception as e:
            return jsonify({"error": str(e)}), 500  # Internal Server Error

@api.route("/board/<int:board_id>/delete")
class BoardDelete(Resource):
    @api.doc('게시글 삭제')
    def delete(self, board_id):
        """게시글 삭제"""
        try:
            # 데이터베이스에서 해당 게시글 가져오기
            board = Board.query.get(board_id)
            if board is None:
                return jsonify({"error": "게시글을 찾을 수 없습니다."}), 404

            # 게시글 삭제
            db.session.delete(board)
            db.session.commit()

            # 삭제된 게시글 이후의 boardId를 하나씩 당김
            boards_to_update = Board.query.filter(Board.boardId > board_id).all()
            for b in boards_to_update:
                b.boardId -= 1

            db.session.commit()

            return jsonify({"message": "게시글이 삭제되었습니다."}), 200  # OK
        except Exception as e:
            return jsonify({"error": str(e)}), 500  # Internal Server Error

@api.route("/board/<int:board_id>/comment")
class CommentCreate(Resource):
    @api.doc('댓글 작성')
    @api.expect(comment_model)  # 댓글 작성에 필요한 모델을 지정
    def post(self, board_id):
        """댓글 작성"""
        # 댓글 작성에 필요한 파라미터 파싱
        args = comment_parser.parse_args()
        commentBoardId = board_id  # 게시글 ID는 URL에서 가져옴
        commentId = args['commentId']
        commentWriterId = args['commentWriterId']  # 작성자 ID 추가
        commentContent = args['commentContent']
        commentDaytime = datetime.now()  # 현재 시간을 사용하여 작성 일자 생성

        # 작성자 정보 가져오기 (user_model을 사용)
        user = user_model.query.get(commentWriterId)
        if user is None:
            return jsonify({"error": "댓글 작성자를 찾을 수 없습니다."}), 404

        commentWriter = user.nickname  # 작성자의 nickname 사용
        commentWriterId = user.id

        try:
            # 댓글을 DB에 저장
            new_comment = comment_model(
                commentBoardId=commentBoardId,
                commentId=commentId,
                commentWriterId=commentWriterId,  # 작성자 ID 추가
                commentWriter=commentWriter,
                commentContent=commentContent,
                commentDaytime=commentDaytime  # 작성 일자 추가
            )
            db.session.add(new_comment)
            db.session.commit()

            return jsonify({"message": "댓글이 작성되었습니다."}), 201  # Created
        except Exception as e:
            return jsonify({"error": str(e)}), 500  # Internal Server Error

@api.route("/board/<int:board_id>/comment/<int:comment_id>")
class CommentDelete(Resource):
    @api.doc('댓글 삭제')
    def delete(self, board_id, comment_id):
        """댓글 삭제"""
        try:
            # 데이터베이스에서 해당 댓글 가져오기
            comment = comment_model.query.filter_by(commentBoardId=board_id, commentId=comment_id).first()
            if comment is None:
                return jsonify({"error": "댓글을 찾을 수 없습니다."}), 404

            # 댓글 삭제
            db.session.delete(comment)
            db.session.commit()

            return jsonify({"message": "댓글이 삭제되었습니다."}), 200  # OK
        except Exception as e:
            return jsonify({"error": str(e)}), 500  # Internal Server Error

@api.route('/job_upload')
class JobCreate(Resource):
    @api.doc('취업 정보 추가')
    @api.expect(job_model)
    def post(self):
        """취업 정보 추가"""
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
        """취업 정보 조회"""
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
                    "jobImage": f"https://eatit-backend.azurewebsites.net/{Job[2]}",  # 이미지 URL 포함
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
        """뉴스 추가"""
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
        """카드 뉴스 조회"""
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
                    "CardnewsImage": f"https://eatit-backend.azurewebsites.net/{Cardnews[2]}",  # 이미지 URL 포함
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
        """사용자 정보 수정"""
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
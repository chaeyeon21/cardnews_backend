from flask import Flask, jsonify, request
from search_table import create_db_connection, create_table

app = Flask(__name__)

# 테이블 생성
create_table()


# 데이터베이스에서 검색 기능을 구현하는 함수
def search_data(keyword):
    connection = create_db_connection()
    cursor = connection.cursor()

    # 검색 쿼리
    search_query = f"SELECT * FROM articles WHERE content LIKE '%{keyword}%'"

    cursor.execute(search_query)
    result = cursor.fetchall()

    cursor.close()
    connection.close()

    return result


# 검색 기능
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        keyword = request.args.get("keyword", "")
    elif request.method == "POST":
        data = request.json
        keyword = data.get("keyword", "")

    result = search_data(keyword)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=8001)

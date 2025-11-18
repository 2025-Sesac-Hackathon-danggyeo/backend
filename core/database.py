from tinydb import TinyDB, Query

# TinyDB 데이터베이스 연결 및 테이블 선언
# 모든 유저 관련 정보는 이 파일에서 객체를 통해 접근
DB_PATH = 'db.json'
db = TinyDB(DB_PATH)
users_table = db.table('users')
blacklist_table = db.table('token_blacklist')
s3_table = db.table('s3_files')
UserQuery = Query()

from tinydb import TinyDB, Query

# TinyDB 데이터베이스 연결 및 테이블 선언
# 모든 유저 관련 정보는 이 파일에서 객체를 통해 접근
DB_PATH = 'db.json'
db = TinyDB(DB_PATH)
users_table = db.table('users')
blacklist_table = db.table('token_blacklist')
s3_table = db.table('s3_files')

# 발표 대본 관련 테이블
scripts_table = db.table('scripts')  # 발표 대본 메타데이터
slides_table = db.table('slides')  # 슬라이드 정보
sentences_table = db.table('sentences')  # 청크화된 문장
practice_scores_table = db.table('practice_scores')  # 연습 점수

UserQuery = Query()

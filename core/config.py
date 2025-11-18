from dotenv import load_dotenv
load_dotenv()
import os

SECRET_KEY = os.getenv('SECRET_KEY', '')
ALGORITHM = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))

# [AWS S3 설정]
# - AWS_ACCESS_KEY_ID: IAM에서 발급받은 access key
# - AWS_SECRET_ACCESS_KEY: IAM에서 발급받은 secret key
# - S3_BUCKET_NAME: 사용할 S3 버킷 이름
# - S3_REGION: S3 버킷 리전 (예: ap-northeast-2)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', '')
S3_REGION = os.getenv('S3_REGION', 'ap-northeast-2')

# Supertone API key (optional) - set in environment when using voice cloning
SUPERTONE_API_KEY = os.getenv('SUPERTONE_API_KEY', '')

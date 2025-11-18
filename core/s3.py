import boto3
from botocore.exceptions import ClientError
from core.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION

# S3 Presigned URL 발급 함수
# param object_key: presigned url을 발급받고자 하는 버킷 내의 파일 경로(파일명 포함)
# param expiration: presigned url의 유효 시각(초). 기본 300초(5분).
# return: "성공 시 presigned url(str) / 실패 시 None"
def create_presigned_url(object_key: str, expiration: int = 300) -> str:
    """
    지정한 S3 파일(object_key)에 대해 일정 시간 동안 접근 가능한 presigned url을 반환합니다.
    S3에 파일이 없더라도 url을 생성 가능하나, 실제 요청시 없으면 오류 반환됨.
    예외 상황은 명확한 메시지로 반환합니다.
    """
    try:
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        # boto3 generate_presigned_url 함수 사용
        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        # AWS 인증 정보 오류, 버킷/키 오류 등 모두 명확히 출력
        print(f"[S3 Presigned URL 발급실패] {e}")
        return None
    except Exception as e:
        print(f"[S3 예기치 못한 오류] {e}")
        return None

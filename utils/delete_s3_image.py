# utils/delete_s3_image.py
import boto3
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def delete_s3_image(image_key):
    """
    S3에서 이미지를 삭제하는 함수

    :param image_key: S3에서 삭제할 이미지의 키 (파일 경로)
    :return: 삭제 성공 시 True, 실패 시 False
    """
    s3 = boto3.client('s3', region_name='ap-southeast-2')
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    image_key = f"static/{image_key}"
    try:
        s3.delete_object(Bucket=bucket_name, Key=image_key)
        print(f"S3에서 이미지 {image_key} 삭제 완료")
        logger.info(f"S3에서 이미지 {image_key} 삭제 완료")
        return True
    except Exception as e:
        print(f"S3 이미지 삭제 오류: {e}")
        logger.error(f"S3 이미지 삭제 오류: {e}")
        return False

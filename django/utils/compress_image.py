from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import os
import logging

logger = logging.getLogger(__name__)

def compress_image(image, quality=70, max_size=(800, 800), output_format="WEBP"):
    """
    업로드된 이미지를 압축하고 WebP 형식으로 변환하는 함수

    :param image: Django ImageField (원본 이미지)
    :param quality: 압축 품질 (0~100)
    :param max_size: 최대 크기 (너비, 높이)
    :param output_format: 출력할 이미지 포맷 (WEBP, JPEG, PNG 등)
    :return: 변환된 이미지
    """
    if not image:
        return None

    original_size = image.size  # 원본 파일 크기
    original_format = image.name.split('.')[-1].upper()  # 원본 확장자 (PNG, JPG 등)

    img = Image.open(image)

    # 투명 배경 유지 여부 체크
    if img.mode in ("RGBA", "LA"):
        img = img.convert("RGBA")  # 알파 채널 유지 (투명배경)
    else:
        img = img.convert("RGB")  # 다른 형식은 RGB 변환

    # Pillow 10.0 이상 버전 대응: Image.LANCZOS 또는 Image.Resampling.LANCZOS 사용
    if hasattr(Image, "Resampling"):  # Pillow 10.0 이상
        resample = Image.Resampling.LANCZOS
    else:  # Pillow 9.x 이하
        resample = Image.LANCZOS

    # 이미지 리사이징 (비율 유지)
    img.thumbnail(max_size, resample)

    # 압축된 이미지 저장
    img_io = BytesIO()
    img.save(img_io, format=output_format, quality=quality)

    compressed_image = ContentFile(img_io.getvalue(), name=f"{os.path.splitext(image.name)[0]}.{output_format.lower()}")

    # 디버깅: 변환 후 파일 크기 출력
    new_size = len(img_io.getvalue())  # 변환 후 파일 크기 (bytes)

    logger.info(f"[IMAGE COMPRESSION] Original: {original_size / 1024:.2f} KB ({original_format}), "
                f"Compressed: {new_size / 1024:.2f} KB ({output_format})")

    return compressed_image

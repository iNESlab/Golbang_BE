'''
MVP demo ver 0.0.1
2024.10.31
golf_data/models.py
'''
# golf_data/models.py

from django.db import models

class GolfClub(models.Model):
    '''
    골프장 클럽 정보
    '''
    club_name = models.CharField("club name",max_length=255, unique=True)
    address = models.TextField("address")
    longitude = models.FloatField("longitude", null=True, blank=True)
    latitude = models.FloatField("latitude", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # 데이터 변경 이력 추적용

    class Meta:
        db_table = 'golf_clubs'  # 테이블 이름 명시

    def __str__(self):
        return f"{self.club_name}"

class GolfCourse(models.Model):
    '''
    골프장 내 골프 코스 정보
    '''
    club = models.ForeignKey(GolfClub, on_delete=models.CASCADE, related_name='courses')
    course_name = models.CharField("course name", max_length=255)
    holes = models.PositiveIntegerField("holes", default=18) # 양수만 저장 가능. 보통 9홀 또는 18홀
    par = models.PositiveIntegerField("par", default=72) # 양수만 저장 가능. 보통 36 또는 72
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # 데이터 변경 이력 추적용

    class Meta:
        db_table = 'golf_courses'
        unique_together = ['club', 'course_name']  # 동일 클럽 내 중복 코스명 방지

    def __str__(self):
        return f"{self.course_name} at {self.club.club_name}"

class Tee(models.Model):
    '''
    각 코스별 홀 및 핸디캡 정보
    '''
    course = models.ForeignKey(GolfCourse, on_delete=models.CASCADE, related_name='tees')
    tee_name = models.CharField("tee name", max_length=255)  # "Blue", "White"
    hole_1_par = models.CharField("Hole1 Par", max_length=20, default="0")
    hole_2_par = models.CharField("Hole2 Par", max_length=20, default="0")
    hole_3_par = models.CharField("Hole3 Par", max_length=20, default="0")
    hole_4_par = models.CharField("Hole4 Par", max_length=20, default="0")
    hole_5_par = models.CharField("Hole5 Par", max_length=20, default="0")
    hole_6_par = models.CharField("Hole6 Par", max_length=20, default="0")
    hole_7_par = models.CharField("Hole7 Par", max_length=20, default="0")
    hole_8_par = models.CharField("Hole8 Par", max_length=20, default="0")
    hole_9_par = models.CharField("Hole9 Par", max_length=20, default="0")
    hole_10_par = models.CharField("Hole10 Par", max_length=20, default="0")
    hole_11_par = models.CharField("Hole11 Par", max_length=20, default="0")
    hole_12_par = models.CharField("Hole12 Par", max_length=20, default="0")
    hole_13_par = models.CharField("Hole13 Par", max_length=20, default="0")
    hole_14_par = models.CharField("Hole14 Par", max_length=20, default="0")
    hole_15_par = models.CharField("Hole15 Par", max_length=20, default="0")
    hole_16_par = models.CharField("Hole16 Par", max_length=20, default="0")
    hole_17_par = models.CharField("Hole17 Par", max_length=20, default="0")
    hole_18_par = models.CharField("Hole18 Par", max_length=20, default="0")

    # 홀 별 핸디캡 정보
    hole_1_handicap = models.CharField("Hole1 Handicap", max_length=20, default="0")
    hole_2_handicap = models.CharField("Hole2 Handicap", max_length=20, default="0")
    hole_3_handicap = models.CharField("Hole3 Handicap", max_length=20, default="0")
    hole_4_handicap = models.CharField("Hole4 Handicap", max_length=20, default="0")
    hole_5_handicap = models.CharField("Hole5 Handicap", max_length=20, default="0")
    hole_6_handicap = models.CharField("Hole6 Handicap", max_length=20, default="0")
    hole_7_handicap = models.CharField("Hole7 Handicap", max_length=20, default="0")
    hole_8_handicap = models.CharField("Hole8 Handicap", max_length=20, default="0")
    hole_9_handicap = models.CharField("Hole9 Handicap", max_length=20, default="0")
    hole_10_handicap = models.CharField("Hole10 Handicap", max_length=20, default="0")
    hole_11_handicap = models.CharField("Hole11 Handicap", max_length=20, default="0")
    hole_12_handicap = models.CharField("Hole12 Handicap", max_length=20, default="0")
    hole_13_handicap = models.CharField("Hole13 Handicap", max_length=20, default="0")
    hole_14_handicap = models.CharField("Hole14 Handicap", max_length=20, default="0")
    hole_15_handicap = models.CharField("Hole15 Handicap", max_length=20, default="0")
    hole_16_handicap = models.CharField("Hole16 Handicap", max_length=20, default="0")
    hole_17_handicap = models.CharField("Hole17 Handicap", max_length=20, default="0")
    hole_18_handicap = models.CharField("Hole18 Handicap", max_length=20, default="0")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    # 데이터 변경 이력 추적용

    class Meta:
        db_table = 'golf_tees'
        unique_together = ['course', 'tee_name']  # 중복 방지

    def __str__(self):
        return f"{self.tee_name} Tee for {self.course.course_name}"

class ExcelFileUpload(models.Model):
    '''
    Admin 페이지에서 Excel 파일을 업로드하기 위한 모델
    '''
    file = models.FileField(upload_to='golf_data/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'excel_file_uploads'

    def __str__(self):
        return f"Excel upload at {self.uploaded_at}"
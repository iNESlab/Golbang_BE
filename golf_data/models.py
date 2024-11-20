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
    facility_id = models.CharField(max_length=50, primary_key=True)  # 외부 키 연동을 위해 추가
    club_name = models.CharField("club name",max_length=255, unique=True)
    address = models.TextField("address")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # 데이터 변경 이력 추적용

    class Meta:
        db_table = 'golf_clubs'  # 테이블 이름 명시

    def __str__(self):
        return f"{self.club_name} ({self.facility_id})"
class GolfCourse(models.Model):
    '''
    골프장 내 골프 코스 정보
    '''
    course_id = models.CharField(max_length=50, primary_key=True)  # 외부 키 연동을 위해 추가
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
    hole_1_par = models.PositiveIntegerField("Hole1 Par", default=0)
    hole_2_par = models.PositiveIntegerField("Hole2 Par", default=0)
    hole_3_par = models.PositiveIntegerField("Hole3 Par", default=0)
    hole_4_par = models.PositiveIntegerField("Hole4 Par", default=0)
    hole_5_par = models.PositiveIntegerField("Hole5 Par", default=0)
    hole_6_par = models.PositiveIntegerField("Hole6 Par", default=0)
    hole_7_par = models.PositiveIntegerField("Hole7 Par", default=0)
    hole_8_par = models.PositiveIntegerField("Hole8 Par", default=0)
    hole_9_par = models.PositiveIntegerField("Hole9 Par", default=0)
    hole_10_par = models.PositiveIntegerField("Hole10 Par", default=0)
    hole_11_par = models.PositiveIntegerField("Hole11 Par", default=0)
    hole_12_par = models.PositiveIntegerField("Hole12 Par", default=0)
    hole_13_par = models.PositiveIntegerField("Hole13 Par", default=0)
    hole_14_par = models.PositiveIntegerField("Hole14 Par", default=0)
    hole_15_par = models.PositiveIntegerField("Hole15 Par", default=0)
    hole_16_par = models.PositiveIntegerField("Hole16 Par", default=0)
    hole_17_par = models.PositiveIntegerField("Hole17 Par", default=0)
    hole_18_par = models.PositiveIntegerField("Hole18 Par", default=0)

    # 홀 별 핸디캡 정보
    hole_1_handicap = models.PositiveIntegerField("Hole1 Handicap", default=0)
    hole_2_handicap = models.PositiveIntegerField("Hole2 Handicap", default=0)
    hole_3_handicap = models.PositiveIntegerField("Hole3 Handicap", default=0)
    hole_4_handicap = models.PositiveIntegerField("Hole4 Handicap", default=0)
    hole_5_handicap = models.PositiveIntegerField("Hole5 Handicap", default=0)
    hole_6_handicap = models.PositiveIntegerField("Hole6 Handicap", default=0)
    hole_7_handicap = models.PositiveIntegerField("Hole7 Handicap", default=0)
    hole_8_handicap = models.PositiveIntegerField("Hole8 Handicap", default=0)
    hole_9_handicap = models.PositiveIntegerField("Hole9 Handicap", default=0)
    hole_10_handicap = models.PositiveIntegerField("Hole10 Handicap", default=0)
    hole_11_handicap = models.PositiveIntegerField("Hole11 Handicap", default=0)
    hole_12_handicap = models.PositiveIntegerField("Hole12 Handicap", default=0)
    hole_13_handicap = models.PositiveIntegerField("Hole13 Handicap", default=0)
    hole_14_handicap = models.PositiveIntegerField("Hole14 Handicap", default=0)
    hole_15_handicap = models.PositiveIntegerField("Hole15 Handicap", default=0)
    hole_16_handicap = models.PositiveIntegerField("Hole16 Handicap", default=0)
    hole_17_handicap = models.PositiveIntegerField("Hole17 Handicap", default=0)
    hole_18_handicap = models.PositiveIntegerField("Hole18 Handicap", default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    # 데이터 변경 이력 추적용

    class Meta:
        db_table = 'golf_tees'

    def __str__(self):
        return f"Tee for {self.course.course_name}"

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
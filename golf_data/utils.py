'''
MVP demo ver 0.0.1
2024.10.31
golf_data/utils.py

역할: golf course data 엑셀 데이터를 mysql로 변환하도록 처리하는 utils
'''
# golf_data/utils.py
import pandas as pd
from .models import GolfClub, GolfCourse, Tee
from django.db import transaction


class GolfDataImporter:
    def __init__(self, excel_file):
        self.excel_file = excel_file

    @transaction.atomic  # 전체 처리를 하나의 트랜잭션으로 관리
    def import_data(self):
        # 골프 클럽 데이터 읽기
        clubs_df = pd.read_excel(self.excel_file, sheet_name='Golf Clubs')
        courses_df = pd.read_excel(self.excel_file, sheet_name='Golf Courses')
        tees_df = pd.read_excel(self.excel_file, sheet_name='Tees')

        # 데이터 임포트
        self._import_clubs(clubs_df)
        self._import_courses(courses_df)
        self._import_tees(tees_df)

    def _import_clubs(self, df):
        for _, row in df.iterrows():
            GolfClub.objects.update_or_create(
                facility_id=row['Facility ID'],
                defaults={
                    'club_name': row['Club Name'],
                    'address': row['Address']
                }
            )

    def _import_courses(self, df):
        for _, row in df.iterrows():
            club = GolfClub.objects.get(facility_id=row['Facility ID'])
            GolfCourse.objects.update_or_create(
                course_id=row['Course ID'],
                defaults={
                    'club': club,
                    'course_name': row['Course Name'],
                    'holes': row['Holes'],
                    'par': row['Par']
                }
            )

    def _import_tees(self, df):
        for _, row in df.iterrows():
            course = GolfCourse.objects.get(course_id=row['Course ID'])

            # Tee 객체 생성
            tee = Tee(course=course)

            # 반복문으로 hole 필드 값 설정
            for hole_num in range(1, 19):
                par_field = f'hole_{hole_num}_par'
                handicap_field = f'hole_{hole_num}_handicap'
                setattr(tee, par_field, row[f'Hole {hole_num} Par'])
                setattr(tee, handicap_field, row[f'Hole {hole_num} Handicap'])
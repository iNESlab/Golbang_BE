'''
MVP demo ver 0.0.1
2024.10.31
golf_data/data_import.py

역할: admin 페이지에 업로드한 엑셀 파일을 sql로 변환
'''
# golf_data/data_import.py

import pandas as pd
import requests
from io import BytesIO
from .models import GolfClub, GolfCourse, Tee


def import_excel_data(file_url):
    response = requests.get(file_url)
    response.raise_for_status()

    excel_file = BytesIO(response.content)

    clubs_df = pd.read_excel(excel_file, sheet_name='Golf Clubs')
    courses_df = pd.read_excel(excel_file, sheet_name='Golf Courses')
    tees_df = pd.read_excel(excel_file, sheet_name='Tees')

    # 열 이름 확인
    print("Tees DataFrame Columns:", tees_df.columns)

    for _, row in clubs_df.iterrows():
        GolfClub.objects.get_or_create(
            facility_id=row['Facility ID'],
            defaults={'club_name': row['Club Name'], 'address': row['Address']}
        )

    for _, row in courses_df.iterrows():
        club = GolfClub.objects.get(facility_id=row['Facility ID'])
        GolfCourse.objects.get_or_create(
            course_id=row['Course ID'],
            club=club,
            course_name=row['Course Name'],
            defaults={'holes': row['Holes'], 'par': row['Par']}
        )

    for _, row in tees_df.iterrows():
        course = GolfCourse.objects.get(course_id=row['Course ID'])
        tee = Tee(course=course)

        for hole_num in range(1, 19):
            par_field = f'hole_{hole_num}_par'
            handicap_field = f'hole_{hole_num}_handicap'

            # 열 이름이 있는지 확인 후, 존재할 경우에만 설정
            if f'Hole {hole_num} Par' in tees_df.columns:
                setattr(tee, par_field, row[f'Hole {hole_num} Par'])
            if f'Hole {hole_num} Handicap' in tees_df.columns:
                setattr(tee, handicap_field, row[f'Hole {hole_num} Handicap'])

        tee.save()

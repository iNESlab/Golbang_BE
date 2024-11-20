'''
MVP demo ver 0.0.2
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

    # 각 시트를 데이터프레임으로 로드하고 `~` 값을 None으로 변환
    clubs_df = pd.read_excel(excel_file, sheet_name='Golf Clubs').replace('~', None)
    courses_df = pd.read_excel(excel_file, sheet_name='Golf Courses').replace('~', None)
    tees_df = pd.read_excel(excel_file, sheet_name='Tees').replace('~', None)

    # GolfClub 데이터를 데이터베이스에 저장
    for _, row in clubs_df.iterrows():
        print("import clubs")

        GolfClub.objects.update_or_create(
            facility_id=row['Facility ID'],
            defaults={'club_name': row['Club Name'] or '', 'address': row['Address'] or ''}
        )

    # GolfCourse 데이터를 데이터베이스에 저장
    for _, row in courses_df.iterrows():
        print("import courses")

        club = GolfClub.objects.get(facility_id=row['Facility ID'])
        GolfCourse.objects.update_or_create(
            course_id=row['Course ID'],
            defaults={
                'club': club,
                'course_name': row['Course Name'] or '',
                'holes': row['Holes'] or 0,
                'par': row['Par'] or 0
            }
        )

    # Tee 데이터를 데이터베이스에 저장
    for _, row in tees_df.iterrows():
        print("import tees")
        course = GolfCourse.objects.get(course_id=row['Course ID'])

        # 특정 조건으로 Tee 객체들 필터링
        tees = Tee.objects.filter(course=course)

        # 각 Tee 객체에 대해 반복문을 실행하여 필드를 설정
        for tee in tees:
            for hole_num in range(1, 19):
                par_field = f'hole_{hole_num}_par'
                handicap_field = f'hole_{hole_num}_handicap'

                # 'Hole {x} Par'과 'Hole {x} Handicap' 컬럼 값 가져오기
                par_value = row.get(f'Hole{hole_num} Par', 0)
                handicap_value = row.get(f'Hole{hole_num} Handicap', 0)

                # None, '~', 'N/D' 값을 0으로 대체
                par_value = 0 if par_value in [None, '~', 'N/D'] else int(par_value)
                handicap_value = 0 if handicap_value in [None, '~', 'N/D'] else int(handicap_value)

                # 필드에 값 설정
                setattr(tee, par_field, par_value)
                setattr(tee, handicap_field, handicap_value)

            # Tee 객체 저장
            tee.save()
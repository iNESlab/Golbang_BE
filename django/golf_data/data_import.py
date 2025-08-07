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
    """
    주어진 URL에서 엑셀 파일을 받아와서
    GolfClub, GolfCourse, Tee 데이터를 데이터베이스에 저장합니다.
    주의:
    - 필수 필드(예: Longitude, Latitude)에 값이 없으면
      MySQL에 저장하는 과정에서 오류가 발생할 수 있습니다.
    """
    response = requests.get(file_url)
    response.raise_for_status()

    excel_file = BytesIO(response.content)

    clubs_df   = pd.read_excel(excel_file, sheet_name='Golf Clubs').replace('~', None)
    courses_df = pd.read_excel(excel_file, sheet_name='Golf Courses').replace('~', None)
    tees_df    = pd.read_excel(excel_file, sheet_name='Tees').replace('~', None)
    print(tees_df.columns.tolist())

    # ‘TBD(크롤링 사이트에서 만드는 임시 데이터)’ 로만 구성된 placeholder 행 제거
    clubs_df = clubs_df[clubs_df['Club Name'] != 'TBD']
    courses_df = courses_df[
        (courses_df['Club Name']   != 'TBD') &
        (courses_df['Course Name'] != 'TBD')
    ]
    tees_df    = tees_df[
        (tees_df['Club Name']   != 'TBD') &
        (tees_df['Course Name'] != 'TBD') &
        (tees_df['Tee Name']    != 'TBD')
    ]

    # 1) GolfClub 저장
    for _, row in clubs_df.iterrows():
        club_name = row['Club Name'].strip()
        address   = (row.get('Address') or '').strip()
        longitude = row.get('Longitude')
        latitude  = row.get('Latitude')

        print(f"import club: {club_name}")
        GolfClub.objects.update_or_create(
            club_name=club_name,
            defaults={
                'address':   address,
                'longitude': longitude,
                'latitude':  latitude,
            }
        )

    # 2) GolfCourse 저장
    for _, row in courses_df.iterrows():
        club_name   = row['Club Name'].strip()
        course_name = row['Course Name'].strip()
        holes = row.get('Holes') or 0
        par   = row.get('Par')   or 0

        print(f"import course: {club_name} / {course_name}")
        club = GolfClub.objects.get(club_name=club_name)
        GolfCourse.objects.update_or_create(
            club=club,
            course_name=course_name,
            defaults={'holes': holes, 'par': par}
        )

    # 3) Tee 저장
    for _, row in tees_df.iterrows():
        print(f"import tee: {row}")
        club_name   = row['Club Name'].strip()
        course_name = row['Course Name'].strip()
        tee_name    = row['Tee Name'].strip()

        print(f"Processing Tee: {club_name} / {course_name} / {tee_name}")
        try:
            course = GolfCourse.objects.get(
                club__club_name=club_name,
                course_name=course_name
            )
        except GolfCourse.DoesNotExist:
            print(f"  -> Course not found: {club_name} / {course_name}")
            continue

        # hole/par defaults
        defaults = {}
        for i in range(1, 19):
            defaults[f'hole_{i}_par']      = row.get(f'Hole{i} Par')      or 0
            defaults[f'hole_{i}_handicap'] = row.get(f'Hole{i} Handicap') or 0

        tee, created = Tee.objects.update_or_create(
            course=course,
            tee_name=tee_name,
            defaults=defaults
        )

        action = "Created" if created else "Updated"
        print(f"  -> {action} Tee: {tee_name}")

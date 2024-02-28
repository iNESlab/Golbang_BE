![header](https://capsule-render.vercel.app/api?type=waving&color=auto&height=200&section=header&text=Golbang_BackEnd&fontSize=50&animation=fadeIn&fontAlignY=35)

# Golbang BackEnd

> **커밋 컨벤션, 브랜치, pull request 꼭 지키기 !**
> [[git][fork][bash] git bash로 협업하기 - Forking Workflow](https://co-deok.tistory.com/16)

### 사용
1. 이 레포를 fork해와서 개인 저장소로 가져옴
2. 각자 **본인 이름의 브랜치**에서 작업한 내용을 본인 이름의 디렉토리에 올리고 `git push` (개인저장소), `git upstream`(팀 저장소) (자세한 건 위의 git bash 로 협업하기 블로그 내용 참조)
3. 최종적으로는 본인 이름의 리포지토리로 만들어서 합칠 예정 (git merge)


### 커밋 컨벤션
**1. 기능  : Feat, Fix, Design, !BREAKING CHANGE**  
- `Feat`: 새로운 기능을 추가할 경우  
- `Fix`: 버그를 고친 경우  
- `Design`: CSS 등 사용자 UI 디자인 변경  
- `!BREAKING CHANG`: 커다란 API 변경의 경우 (ex API의 arguments, return 값의 변경, DB 테이블 변경, 급하게 치명적인 버그를 고쳐야 하는 경우)  
- ex)"Feat(navigation): ~~~~  " "Fix(database): ~~~~"  

**2. 개선: Style, Refactor, Comment 태그**  
- `Style`: 코드 포맷 변경, 세미 콜론 누락, 코드 수정이 없는 경우 <오타 수정, 탭 사이즈 변경, 변수명 변경 등에 해당>   
- `Refactor`: 프로덕션 코드 리팩토링, 새로운 기능이나 버그 수정없이 현재 구현을 개선한 경우 <코드를 리팩토링 하는 경우>  
- `Comment`: 필요한 주석 추가 및 변경  
  
**3. 그 외: Docs, Test, Chore, Rename, Remove 태그**
- `Docs`: 문서를 수정한 경우  <README.md>  
- `Test`: 테스트 추가, 테스트 리팩토링 (프로덕션 코드 변경 없음)  <test 폴더 내부의 변경이 일어난 경우에만 해당>  
- `Chore`: 빌드 태스크 업데이트, 패키지 매니저 설정할 경우 (프로덕션 코드 변경 없음)  <package.json의 변경이나 dotenv의 요소 변경 등, 모듈의 변경에 해당>  
- `Rename`: 파일 혹은 폴더명을 수정하는 경우  
- `Remove`: 사용하지 않는 파일 혹은 폴더를 삭제하는 경우  
 
**4. 예시**  
- Feat: "추가 get data api 함수"  
-  "고침", "추가", "변경" 또는 "Fix", "Add", "Change" 사용  

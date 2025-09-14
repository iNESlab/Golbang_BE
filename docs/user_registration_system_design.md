# 🎯 소셜 로그인 후 프로필 완성 화면 구현 계획서

## 📋 현재 상황 분석

### ✅ 이미 완료된 것
- Google 소셜 로그인 백엔드 API (`mobile_google_login`)
- Flutter GoogleAuthService 연동
- JWT 토큰 발급 및 저장
- 기본적인 로그인 플로우

### ✅ 기존에 이미 있는 것
- **회원가입 플로우 전체**: `signup.dart` → `additional_info.dart` → `signup_complete.dart`
- **프로필 입력 폼**: `additional_info.dart`에 닉네임, 전화번호, 핸디캡, 생일, 주소, 학번 입력
- **백엔드 API**: `/api/v1/users/signup/step-1/`, `/api/v1/users/signup/step-2/`
- **사용자 서비스**: `UserService.saveUser()`, `UserService.saveAdditionalInfo()`

### ❌ 아직 필요한 것
- 소셜 로그인 성공 후 기존 `additional_info.dart` 재활용
- Google 정보 자동 채우기
- 자연스러운 화면 전환

## 🎯 구현 목표

### 핵심 목표
**기존 `additional_info.dart`를 소셜 로그인용으로 재활용하여 소셜 로그인 플로우 완성**

### 구현 범위
- 기존 `additional_info.dart` 수정 (소셜 로그인 지원)
- `GoogleAuthService`에서 화면 전환 연동
- 기존 API 활용하여 프로필 저장

## 🏗️ 기술적 접근

### 1. 백엔드 (Django)
```python
# 기존 social_login.py 활용
# 추가 구현 필요 없음 - 이미 완료됨
```

### 2. 프론트엔드 (Flutter)
```dart
// 기존 additional_info.dart 수정하여 재활용
class AdditionalInfoPage extends ConsumerStatefulWidget {
  final int? userId;        // 기존 회원가입용
  final String? email;      // 소셜 로그인용 (새로 추가)
  final String? displayName; // 소셜 로그인용 (새로 추가)
  final bool isSocialLogin;  // 소셜 로그인 여부 (새로 추가)
}
```

### 3. 데이터베이스
```python
# 기존 User 모델 활용
# 추가 필드나 모델 불필요
```

## 🔄 기존 회원가입 플로우 vs 소셜 로그인 플로우

### 기존 회원가입 플로우
```
1단계: signup.dart
├── ID, 이메일, 비밀번호 입력
├── saveUser() API 호출
└── 성공 시 step-2로 이동 (userId 전달)

2단계: additional_info.dart  
├── 닉네임, 전화번호, 핸디캡, 생일, 주소, 학번 입력
├── saveAdditionalInfo() API 호출
└── 성공 시 signup_complete.dart로 이동
```

### 소셜 로그인 플로우 (새로 추가)
```
Google 로그인 → 백엔드 인증 → JWT 토큰 발급 → additional_info.dart (소셜 로그인용) → 프로필 입력 → 메인 화면
```

## 🎨 UI 수정 방안

### additional_info.dart 수정 내용
```
┌─────────────────────────────┐
│        프로필 완성           │
├─────────────────────────────┤
│  🏌️‍♂️ 골방에 오신 것을      │
│     환영합니다!             │
├─────────────────────────────┤
│  이름: [Google 이름 자동]   │
│  이메일: [Google 이메일]    │
│  전화번호: [입력 필드]      │
│  핸디캡: [입력 필드]        │
│  생일: [선택 필드]          │
│  주소: [입력 필드]          │
│  학번: [입력 필드]          │
├─────────────────────────────┤
│  [프로필 완성하기]          │
└─────────────────────────────┘
```

### 화면 특징
- **Google 정보 활용**: 이메일과 이름은 자동으로 채움
- **기존 입력 폼 재활용**: 전화번호, 핸디캡, 생일, 주소, 학번
- **자연스러운 전환**: 완성 후 메인 화면으로 이동

## 🔄 사용자 플로우

### 1. 소셜 로그인 성공
```
Google 로그인 → 백엔드 인증 → JWT 토큰 발급 → 토큰 저장
```

### 2. 프로필 완성 화면
```
토큰 저장 완료 → additional_info.dart (소셜 로그인용) → 사용자 정보 입력
```

### 3. 완료 후 이동
```
프로필 입력 완료 → 백엔드에 정보 저장 → 메인 화면으로 이동
```

## 🚀 구현 단계

### Phase 1: additional_info.dart 수정 ✅
- [x] 소셜 로그인용 파라미터 추가 (`email`, `displayName`, `isSocialLogin`)
- [x] Google 정보 자동 채우기 로직
- [x] 소셜 로그인/일반 회원가입 분기 처리
- [x] 소셜 로그인용 완료 버튼 텍스트 변경

### Phase 2: GoogleAuthService 연동 ✅
- [x] 소셜 로그인 성공 후 화면 전환
- [x] `additional_info.dart`로 이동 (소셜 로그인용)
- [x] Google 정보 전달

### Phase 3: 백엔드 연동 ✅
- [x] 기존 `saveAdditionalInfo` API 활용
- [x] 소셜 로그인 사용자 프로필 저장
- [x] JWT 토큰에서 userId 추출

## 💻 코드 구현 예시

### 1. additional_info.dart 수정
```dart
class AdditionalInfoPage extends ConsumerStatefulWidget {
  final int? userId;        // 기존 회원가입용
  final String? email;      // 소셜 로그인용 (새로 추가)
  final String? displayName; // 소셜 로그인용 (새로 추가)
  final bool isSocialLogin;  // 소셜 로그인 여부 (새로 추가)

  const AdditionalInfoPage({
    super.key,
    this.userId,
    this.email,
    this.displayName,
    this.isSocialLogin = false,
  });

  @override
  _AdditionalInfoPageState createState() => _AdditionalInfoPageState();
}

class _AdditionalInfoPageState extends ConsumerState<AdditionalInfoPage> {
  @override
  void initState() {
    super.initState();
    
    if (widget.isSocialLogin) {
      // Google 정보로 자동 채우기
      _nicknameController.text = widget.displayName ?? '';
      // 이메일은 표시만 (수정 불가)
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isSocialLogin ? '프로필 완성' : ''),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              if (widget.isSocialLogin) ...[
                // 소셜 로그인용 환영 메시지
                Text('🏌️‍♂️ 골방에 오신 것을 환영합니다!'),
                SizedBox(height: 16),
              ],
              
              // 이름 (Google에서 자동 또는 입력)
              if (widget.isSocialLogin)
                TextFormField(
                  controller: _nicknameController,
                  decoration: InputDecoration(labelText: '이름 *'),
                  enabled: false, // Google에서 가져온 이름이므로 수정 불가
                )
              else
                _buildNicknameTextFormField('닉네임', _nicknameController, TextInputType.text),
              
              // 이메일 (Google에서 자동)
              if (widget.isSocialLogin)
                TextFormField(
                  initialValue: widget.email,
                  decoration: InputDecoration(labelText: '이메일'),
                  enabled: false, // Google에서 가져온 이메일이므로 수정 불가
                ),
              
              // 기존 입력 필드들 (전화번호, 핸디캡, 생일, 주소, 학번)
              // ... 기존 코드 유지
              
              // 완료 버튼
              ElevatedButton(
                onPressed: _signUpStep2,
                child: Text(widget.isSocialLogin ? '프로필 완성하기' : '가입하기'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // 완료 버튼 클릭 시
  Future<void> _signUpStep2() async {
    if (widget.isSocialLogin) {
      // 소셜 로그인용: 프로필 정보만 저장
      await _saveSocialUserProfile();
    } else {
      // 기존 회원가입용: 기존 로직 사용
      await _saveAdditionalInfo();
    }
  }

  Future<void> _saveSocialUserProfile() async {
    try {
      // JWT 토큰에서 userId 추출
      final accessToken = await ref.read(secureStorageProvider).readAccessToken();
      final decodedToken = JwtDecoder.decode(accessToken);
      final userId = int.parse(decodedToken['user_id'].toString());
      
      // 기존 saveAdditionalInfo API 활용
      final userService = ref.watch(userServiceProvider);
      final response = await userService.saveAdditionalInfo(
        userId: userId,
        name: _nicknameController.text,
        phoneNumber: _phoneNumberController.text,
        handicap: int.tryParse(_handicapController.text),
        dateOfBirth: _birthdayController.text,
        address: _addressController.text,
        studentId: _studentIdController.text,
      );
      
      if (response.statusCode == 200) {
        // 성공 시 메인 화면으로 이동
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => MainScreen()),
        );
      } else {
        throw Exception('프로필 저장 실패');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('프로필 저장에 실패했습니다: $e')),
      );
    }
  }
}
```

### 2. GoogleAuthService 수정
```dart
// google_auth_service.dart에서 성공 후 화면 전환
Future<void> _sendIdTokenToBackend(String idToken, String email, String displayName) async {
  // ... 기존 코드 ...
  
  if (data['data']?['access_token'] != null) {
    // 토큰 저장
    await _storage.write(key: 'ACCESS_TOKEN', value: data['data']['access_token']);
    
    // additional_info.dart로 이동 (소셜 로그인용)
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (context) => AdditionalInfoPage(
          email: email,
          displayName: displayName,
          isSocialLogin: true,
        ),
      ),
    );
  }
}
```

## 🎯 핵심 원칙

### 1. 기존 코드 최대한 활용
- 새로운 화면 만들지 않음
- 기존 `additional_info.dart` 재활용
- 기존 API 구조 유지

### 2. 최소한의 수정
- 기존 기능 유지하면서 소셜 로그인 지원
- 새로운 모델이나 필드 추가 없음
- 기존 회원가입 플로우에 영향 없음

### 3. 자연스러운 플로우
- 소셜 로그인 → 프로필 완성 → 메인 화면
- 사용자가 자연스럽게 따라갈 수 있는 구조
- 강제나 복잡한 선택 없음

## 📊 예상 결과

### 사용자 경험
- ✅ **자연스러운 온보딩**: 소셜 로그인 후 자연스러운 프로필 완성
- ✅ **친숙한 인터페이스**: 기존 회원가입과 동일한 입력 폼
- ✅ **빠른 완성**: Google 정보 자동 채움으로 빠른 완료

### 개발 효율성
- ✅ **코드 재사용**: 새로운 화면 개발 불필요
- ✅ **기존 시스템 활용**: 새로운 아키텍처 불필요
- ✅ **빠른 구현**: 기존 코드 수정만으로 완성

### 유지보수성
- ✅ **단일 소스**: 프로필 입력 로직이 한 곳에 집중
- ✅ **일관성**: 기존 회원가입과 동일한 유효성 검사
- ✅ **확장성**: 향후 다른 소셜 로그인 추가 시 쉽게 확장

## ⚠️ 주의사항

### 1. 기존 기능 보호
- 기존 회원가입 플로우에 영향 없음
- 기존 API 구조 유지
- 기존 유효성 검사 로직 유지

### 2. 호환성 유지
- 기존 사용자 데이터 손실 방지
- 기존 API 응답 형식 유지
- 기존 에러 처리 로직 유지

### 3. 테스트 필요성
- 소셜 로그인 → 프로필 완성 플로우 테스트
- 기존 회원가입 기능 정상 동작 확인
- 에러 상황 처리 테스트

---

**이 계획은 기존 코드를 최대한 활용하여 소셜 로그인 플로우를 완성하는 것을 목표로 합니다.** 🚀

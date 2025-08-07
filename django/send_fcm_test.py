import firebase_admin
from firebase_admin import credentials, messaging

if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")  # Firebase SDK JSON 경로 수정
    firebase_admin.initialize_app(cred)
def test_send_fcm_notification(token, title, body):
    # FCM 메시지 작성
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    try:
        # FCM 알림 전송
        response = messaging.send(message)
        print(f"Successfully sent message: {response}")
        return response
    except Exception as e:
        print(f"Failed to send message: {e}")
        return None

token = "ciET0f5STbWhqf48Wj9u5l:APA91bF2_eT2qQSgp_OTvCJ40G3m2yBHaIftLFm2qZFgp8RBZ2k_HJ9_cEAdv-pHhaNK0RK-ozrKn14zgLjqbl7pZ8WirR9RiKKm0QZQFQR290T5YNL0Obs"
title = "테스트 알림"
body = "이것은 테스트 메시지입니다."

test_send_fcm_notification(token, title, body)
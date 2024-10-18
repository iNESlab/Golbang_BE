# from firebase_admin import messaging
#
# def send_to_firebase_cloud_messaging():
#     # This registration token comes from the client FCM SDKs.
#     registration_token = '클라이언트의 FCM 토큰'
#
#     # See documentation on defining a message payload.
#     message = messaging.Message(
#     notification=messaging.Notification(
#         title='안녕하세요 타이틀 입니다',
#         body='안녕하세요 메세지 입니다',
#     ),
#     token=registration_token,
#     )
#
#     response = messaging.send(message)
#     # Response is a message ID string.
#     print('Successfully sent message:', response)
#
# def send_to_firebase_cloud_messaging_with_multiple_notifications():
#     # Create a list containing up to 500 registration tokens.
#     # These registration tokens come from the client FCM SDKs.
#     registration_tokens = [
#         'YOUR_REGISTRATION_TOKEN_1',
#         # ...
#         'YOUR_REGISTRATION_TOKEN_N',
#     ]
#
#     message = messaging.MulticastMessage(
#         data={'score': '850', 'time': '2:45'},
#         tokens=registration_tokens,
#     )
#     response = messaging.send_multicast(message)
#     # See the BatchResponse reference documentation
#     # for the contents of response.
#     print('{0} messages were sent successfully'.format(response.success_count))
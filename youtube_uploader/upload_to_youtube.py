import os
import pickle
import json
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 유튜브 업로드에 필요한 인증 및 업로드 함수
def get_authenticated_service():
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    CLIENT_SECRETS_FILE = 'client_secrets.json'

    credentials = None
    if os.path.exists('youtube_credentials.pickle'):
        with open('youtube_credentials.pickle', 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open('youtube_credentials.pickle', 'wb') as token:
            pickle.dump(credentials, token)
    return build('youtube', 'v3', credentials=credentials)

def upload_video(youtube, video_file, title, description, tags=None, categoryId="22", privacyStatus="private"):
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags or [],
            'categoryId': categoryId
        },
        'status': {
            'privacyStatus': privacyStatus
        }
    }
    media = MediaFileUpload(video_file, resumable=True, mimetype='video/mp4')
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    response = request.execute()
    print(f"Video uploaded: https://youtu.be/{response['id']}")

if __name__ == "__main__":
    youtube = get_authenticated_service()
    # 1. video_metadata.json 파일이 있으면 우선 사용
    if os.path.exists('video_metadata.json'):
        with open('video_metadata.json', 'r', encoding='utf-8') as f:
            meta = json.load(f)
        upload_video(
            youtube,
            meta['video_path'],
            meta['title'],
            meta['description'],
            meta.get('tags', []),
            categoryId=meta.get('category', '22'),
            privacyStatus=meta.get('privacy_status', 'private')
        )
    else:
        # 2. 없으면 직접 값 생성해서 업로드
        today = datetime.now().strftime('%Y%m%d')
        title = f"퀴즈#{today} 오늘퀴즈!!이 Shorts는 쿠팡파트너스 활동으로 일정보수를 지급받습니다"
        description = "퀴즈로 뇌를 깨워보세요. 맞출 수 있을까요? 세대간 소통해요? 이 Shorts는 쿠팡파트너스 활동으로 일정보수를 지급받습니다"
        tags = ["퀴즈", "교육", "상식", "게임", "문제풀이", "IQ", "재미", "학습"]
        video_file = 'video_merge/combined_video.mp4'  # 실제 동영상 경로에 맞게 수정
        upload_video(
            youtube,
            video_file,
            title,
            description,
            tags
        ) 

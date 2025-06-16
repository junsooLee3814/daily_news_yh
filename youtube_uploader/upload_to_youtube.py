import os
import pickle
import json
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
    # 예시: 메타데이터 파일에서 정보 읽기
    with open('video_metadata.json', 'r', encoding='utf-8') as f:
        meta = json.load(f)
    youtube = get_authenticated_service()
    upload_video(
        youtube,
        meta['video_path'],
        meta['title'],
        meta['description'],
        meta.get('tags', []),
        categoryId="22",  # 22: People & Blogs, 24: Entertainment, 25: News & Politics 등
        privacyStatus=meta.get('privacy_status', 'private')
    )

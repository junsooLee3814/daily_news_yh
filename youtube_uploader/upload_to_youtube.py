import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_authenticated_service():
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    CLIENT_SECRETS_FILE = 'youtube_uploader/client_secrets.json'
    TOKEN_FILE = 'youtube_uploader/token.json'

    credentials = None
    # token.json이 있으면 바로 사용
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        # 최초 인증(로컬에서만 사용, CI에서는 실행 안 됨)
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server(port=0)
        # 인증 후 token.json 저장
        with open(TOKEN_FILE, 'w') as token:
            token.write(credentials.to_json())
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
        title = f"K-News#{today} 경제/정치/연합뉴스 60초요약!! 이 Shorts는 쿠팡파트너스 활동으로 일정보수를 지급받습니다"
        description = "경제/정치/연합뉴스 60초요약!! 이 Shorts는 쿠팡파트너스 활동으로 일정보수를 지급받습니다"
        tags = ["뉴스","시사","속보","헤드라인","이슈","트렌드","정치","경제"]
        video_file = 'video_merge/combined_video.mp4'  # 실제 동영상 경로에 맞게 수정
        upload_video(
            youtube,
            video_file,
            title,
            description,
            tags
        )

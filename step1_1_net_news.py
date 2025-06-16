import os
import json
import feedparser
import re
from datetime import datetime
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import subprocess
import shutil
import platform
from pathlib import Path

class NewsProcessor:
    def __init__(self):
        # 기본 설정
        self.base_dir = "output"
        self.images_dir = os.path.join(self.base_dir, "images")
        self.videos_dir = os.path.join(self.base_dir, "videos")
        self.temp_dir = "temp"
        self.assets_dir = "assets"
        self.max_dirs = 2
        
        # 타임스탬프 설정
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        self.image_output_dir = os.path.join(self.images_dir, self.timestamp)
        self.video_output_dir = os.path.join(self.videos_dir, self.timestamp)
        
        # 카드 비율 9:13 (예: 1080x1560)
        self.WIDTH = 1080
        self.HEIGHT = 1560
        self.PADDING = 60
        self.BG_COLOR = (255, 255, 255)
        self.TEXT_COLOR = (33, 33, 33)
        
        # 비디오 설정
        self.duration = 3  # 각 뉴스당 3초로 설정
        self.fade_duration = 0.5
        self.zoom_scale = 1.1
        
        # 카테고리별 색상
        self.CATEGORY_COLORS = {
            "[스포츠]": (60, 179, 113),
            "[연예]": (186, 104, 200)
        }
        
        # 초기화
        self._initialize_system()
        
    def _initialize_system(self):
        """시스템 초기화"""
        # 디렉토리 생성
        os.makedirs(self.image_output_dir, exist_ok=True)
        os.makedirs(self.video_output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 폰트 초기화
        self.fonts = self._initialize_fonts()
        if not self.fonts:
            raise Exception("필요한 폰트를 찾을 수 없습니다.")
            
        # FFmpeg 경로 설정
        self.ffmpeg_path = self._get_ffmpeg_path()
        
    def _initialize_fonts(self):
        """시스템별 모던/심플 폰트 초기화 (볼드/레귤러)"""
        font_paths = {
            'Windows': [
                ('C:\\Windows\\Fonts\\NanumSquareRoundB.ttf', 'C:\\Windows\\Fonts\\NanumSquareRoundR.ttf'),
                ('C:\\Windows\\Fonts\\NotoSansKR-Bold.otf', 'C:\\Windows\\Fonts\\NotoSansKR-Regular.otf'),
                ('C:\\Windows\\Fonts\\malgunbd.ttf', 'C:\\Windows\\Fonts\\malgun.ttf'),
            ],
            'Darwin': [
                ('/Library/Fonts/AppleSDGothicNeoB.ttc', '/Library/Fonts/AppleSDGothicNeo.ttc'),
                ('/System/Library/Fonts/AppleGothic.ttf', '/System/Library/Fonts/AppleGothic.ttf')
            ],
            'Linux': [
                ('/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf', '/usr/share/fonts/truetype/nanum/NanumSquareRoundR.ttf'),
                ('/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc'),
                ('/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
            ]
        }
        system = platform.system()
        for bold_path, regular_path in font_paths.get(system, []):
            if os.path.exists(bold_path) and os.path.exists(regular_path):
                try:
                    return {
                        'title': ImageFont.truetype(bold_path, 54),
                        'body': ImageFont.truetype(regular_path, 36),
                        'category': ImageFont.truetype(regular_path, 30),
                        'source': ImageFont.truetype(regular_path, 28)
                    }
                except Exception as e:
                    print(f"폰트 로드 실패 ({bold_path}, {regular_path}): {e}")
        return None
        
    def _get_ffmpeg_path(self):
        """FFmpeg 경로 확인"""
        if platform.system() == "Windows":
            paths = [
                "D:\\ffmpeg\\bin\\ffmpeg.exe",
                "C:\\ffmpeg\\bin\\ffmpeg.exe",
                os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")
            ]
        else:
            paths = [
                "/usr/bin/ffmpeg",
                "/usr/local/bin/ffmpeg",
                "/opt/homebrew/bin/ffmpeg"
            ]
        
        for path in paths:
            if os.path.exists(path):
                return path
        raise Exception("FFmpeg를 찾을 수 없습니다.")
        
    def _cleanup_old_directories(self, target_dir):
        """오래된 디렉토리 정리"""
        try:
            if not os.path.exists(target_dir):
                return
                
            dirs = []
            for d in os.listdir(target_dir):
                full_path = os.path.join(target_dir, d)
                if os.path.isdir(full_path):
                    try:
                        created_time = os.path.getctime(full_path)
                        dirs.append((d, created_time, full_path))
                    except Exception as e:
                        print(f"[정리] 디렉토리 정보 읽기 실패 ({d}): {e}")
            
            dirs.sort(key=lambda x: x[1], reverse=True)
            
            if len(dirs) > self.max_dirs:
                print(f"[정리] 오래된 디렉토리 정리 시작 (현재: {len(dirs)}개)")
                for dir_name, _, dir_path in dirs[self.max_dirs:]:
                    try:
                        for root, _, files in os.walk(dir_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    current_mode = os.stat(file_path).st_mode
                                    os.chmod(file_path, current_mode | 0o200)
                                except Exception as e:
                                    print(f"[정리] 파일 권한 변경 실패 ({file_path}): {e}")
                        
                        shutil.rmtree(dir_path)
                        print(f"[정리] 디렉토리 삭제 완료: {dir_name}")
                    except Exception as e:
                        print(f"[정리] 디렉토리 삭제 실패 ({dir_name}): {e}")
                        try:
                            os.system(f'rd /s /q "{dir_path}"' if os.name == 'nt' else f'rm -rf "{dir_path}"')
                            print(f"[정리] 디렉토리 강제 삭제 완료: {dir_name}")
                        except Exception as e2:
                            print(f"[정리] 디렉토리 강제 삭제 실패 ({dir_name}): {e2}")
                
                remaining = [d for d in os.listdir(target_dir) 
                           if os.path.isdir(os.path.join(target_dir, d))]
                print(f"[정리] 디렉토리 정리 완료 (남은 개수: {len(remaining)}개)")
                
        except Exception as e:
            print(f"[정리] 디렉토리 정리 중 오류 발생: {e}")
            
    def _get_news_category(self, title, source):
        """뉴스 카테고리 판단"""
        if "sports" in source:
            return "스포츠"
        elif "entertainment" in source:
            return "연예"
        return "스포츠"  # 기본값
        
    def _sanitize_text(self, text):
        """텍스트 정제"""
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'[^\w\s\u2600-\u26FF\u2700-\u27BF\u1F300-\u1F9FF]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
        
    def collect_news(self):
        """뉴스 수집: RSS.txt 파일에서 RSS URL 읽기"""
        try:
            print("\n=== 1단계: 뉴스 수집 시작 ===")
            
            # assets/RSS.txt 파일에서 RSS URL 불러오기
            rss_urls = {}
            max_per_category = 10  # 기본값
            total_max = 20  # 기본값
            try:
                with open(os.path.join(self.assets_dir, 'RSS.txt'), 'r', encoding='utf-8') as f:
                    read_urls = False
                    read_card_count = False
                    read_video_length = False
                    
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # RSS URL 읽기
                        if '[RSS_URL 지정]' in line:
                            read_urls = True
                            read_card_count = False
                            read_video_length = False
                            continue
                        # 카드뉴스 개수 설정 읽기
                        elif '[카드뉴스개수]' in line:
                            read_urls = False
                            read_card_count = True
                            read_video_length = False
                            continue
                        # 동영상 길이 설정 읽기
                        elif '[동영상길이]' in line:
                            read_urls = False
                            read_card_count = False
                            read_video_length = True
                            continue
                        elif line.startswith('['):
                            read_urls = False
                            read_card_count = False
                            read_video_length = False
                            continue
                            
                        # 각 설정 값 파싱
                        if read_urls and line.startswith('http'):
                            # URL에서 카테고리 추출 (예: sports, entertainment)
                            if 'rss/' in line and '.xml' in line:
                                category = line.split('rss/')[1].split('.xml')[0]
                                category = category.capitalize()  # 첫 글자 대문자로
                                rss_urls[category] = line
                        
                        # 카드뉴스 개수 설정 파싱
                        elif read_card_count and ':' in line:
                            parts = line.split(':')
                            if len(parts) > 1:
                                value_part = parts[1].strip()
                                
                                # 카테고리별 개수 추출
                                if ',' in value_part and '개' in value_part:
                                    cat_part = value_part.split(',')[0].strip()
                                    total_part = value_part.split(',')[1].strip()
                                    
                                    # 카테고리별 최대 개수
                                    if '개' in cat_part:
                                        try:
                                            extracted_num = cat_part.split('개')[0].strip()
                                            max_per_category = int(extracted_num)
                                            print(f"[설정] 카테고리별 카드뉴스 개수: {max_per_category}개")
                                        except:
                                            print(f"[설정] 카테고리별 카드뉴스 개수 파싱 실패, 기본값 {max_per_category}개 사용")
                                    
                                    # 전체 최대 개수
                                    if '최대' in total_part and '개' in total_part:
                                        try:
                                            extracted_num = total_part.split('최대')[1].split('개')[0].strip()
                                            total_max = int(extracted_num)
                                            print(f"[설정] 전체 최대 카드뉴스 개수: {total_max}개")
                                        except:
                                            print(f"[설정] 전체 최대 카드뉴스 개수 파싱 실패, 기본값 {total_max}개 사용")
                        
                        # 동영상 길이 설정 파싱
                        elif read_video_length and ':' in line:
                            parts = line.split(':')
                            if len(parts) > 1 and '초' in parts[1]:
                                try:
                                    seconds_str = parts[1].strip().split('초')[0].strip()
                                    seconds = int(seconds_str)
                                    self.duration = seconds
                                    print(f"[설정] 카드뉴스별 동영상 길이: {self.duration}초")
                                except:
                                    print(f"[설정] 동영상 길이 파싱 실패, 기본값 {self.duration}초 사용")
                
                if not rss_urls:
                    print("[수집] RSS.txt 파일에서 RSS URL을 찾을 수 없습니다. 기본 RSS URL을 사용합니다.")
                    # 기본 RSS URL 설정
                    rss_urls = {
                        "스포츠": "https://www.yna.co.kr/rss/sports.xml",
                        "연예": "https://www.yna.co.kr/rss/entertainment.xml"
                    }
                else:
                    print(f"[수집] RSS.txt 파일에서 {len(rss_urls)}개 RSS URL을 불러왔습니다.")
                    for cat, url in rss_urls.items():
                        print(f"- {cat}: {url}")
            except Exception as e:
                print(f"[수집] RSS.txt 파일 읽기 실패: {e}")
                # 기본 RSS URL 설정
                rss_urls = {
                    "스포츠": "https://www.yna.co.kr/rss/sports.xml",
                    "연예": "https://www.yna.co.kr/rss/entertainment.xml"
                }
                
            # 카테고리별 뉴스 수집
            category_news = defaultdict(list)
            
            # 각 RSS 피드에서 뉴스 수집
            for category, rss_url in rss_urls.items():
                feed = feedparser.parse(rss_url)
                
                if not feed.entries:
                    print(f"[수집] {category} RSS 피드에서 뉴스를 가져올 수 없습니다.")
                    continue
                
                for entry in feed.entries:
                    title = self._sanitize_text(entry.title)
                    description = self._sanitize_text(entry.get('description', ''))
                    
                    news_data = {
                        "category": f"[{category}]",
                        "title": f"📌 제목: {title}",
                        "summary": f"📝 요약:\n{description}",
                        "source": f"🔗 출처:\n[연합뉴스] {entry.link}",
                        "author": entry.get('author', '연합뉴스'),
                        "published": entry.get('published', '')
                    }
                    category_news[category].append(news_data)
            
            news_list = []
            id_counter = 1
            
            # 각 카테고리별로 최대 max_per_category개씩 뉴스 추가
            for category in category_news:
                items = category_news[category][:max_per_category]
                for item in items:
                    # 제목, 요약(내용), 출처가 모두 비어있지 않은 경우만 추가
                    title_text = item.get('title', '').replace('📌 제목: ', '').strip()
                    summary_text = item.get('summary', '').replace('📝 요약:\n', '').strip()
                    source_text = item.get('source', '').replace('🔗 출처:\n', '').strip()
                    if title_text and summary_text and source_text:
                        item['id'] = id_counter
                        news_list.append(item)
                        id_counter += 1
            
            # 전체 뉴스 total_max개로 제한
            news_list = news_list[:total_max]
            
            print(f"[수집] 총 {len(news_list)}개 뉴스 수집 완료")
            print("\n=== 카테고리별 수집 현황 ===")
            for category in category_news:
                count = len([news for news in news_list if news['category'] == f'[{category}]'])
                print(f"{category}: {count}개")
            
            return news_list
            
        except Exception as e:
            print(f"[수집] 오류 발생: {e}")
            return None
            
    def create_news_image(self, news_item):
        """캔바에서 만든 카드 디자인을 배경으로 사용하고, 텍스트만 예쁘게 배치 (로고와 겹치지 않게)"""
        try:
            from PIL import Image as PILImage
            # 1. 캔바에서 만든 카드 배경 이미지 로드
            template_path = os.path.join('assets', 'card_01_1080x1560.png')
            if not os.path.exists(template_path):
                raise Exception(f"카드 템플릿 파일이 없습니다: {template_path}")
            image = PILImage.open(template_path).convert('RGBA')
            draw = ImageDraw.Draw(image)

            # 2. 텍스트 준비
            category = news_item['category']
            title = news_item['title'].replace("📌 제목: ", "")
            summary = news_item['summary'].replace("📝 요약:\n", "")
            source = news_item['source'].replace("🔗 출처:\n", "")

            # 3. 폰트 설정 (현대적이고 가독성 좋은 폰트)
            font_candidates = [
                ('C:\\Windows\\Fonts\\NanumSquareRoundB.ttf', 'C:\\Windows\\Fonts\\NanumSquareRoundR.ttf'),
                ('C:\\Windows\\Fonts\\NotoSansKR-Bold.otf', 'C:\\Windows\\Fonts\\NotoSansKR-Regular.otf'),
                ('C:\\Windows\\Fonts\\malgunbd.ttf', 'C:\\Windows\\Fonts\\malgun.ttf'),
            ]
            title_font = self.fonts['title']
            body_font = self.fonts['body']
            category_font = self.fonts['category']
            source_font = self.fonts['source']
            for bold_path, regular_path in font_candidates:
                if os.path.exists(bold_path) and os.path.exists(regular_path):
                    try:
                        title_font = ImageFont.truetype(bold_path, 60)
                        body_font = ImageFont.truetype(regular_path, 38)
                        category_font = ImageFont.truetype(regular_path, 34)
                        source_font = ImageFont.truetype(regular_path, 30)
                        break
                    except:
                        pass

            # 4. 텍스트 색상 및 배치 좌표 (디자인 전문가 감성)
            padding_x = 80
            y = 300  # 기존 80 → 300으로 조정 (로고와 겹치지 않게)
            # 카테고리
            cat_color = (120, 180, 120, 220)
            cat_text = category
            draw.text((padding_x, y), cat_text, font=category_font, fill=cat_color)
            y += category_font.size + 40

            # 제목
            title_max_width = self.WIDTH - 2*padding_x
            title_wrapped = self._wrap_text(title, title_font, title_max_width)
            draw.text((padding_x, y), title_wrapped, font=title_font, fill=(30, 30, 30, 255), spacing=8)
            y += title_font.size * (title_wrapped.count('\n')+1) + 60

            # 요약
            summary_max_width = self.WIDTH - 2*padding_x
            summary_wrapped = self._wrap_text(summary, body_font, summary_max_width)
            draw.text((padding_x, y), summary_wrapped, font=body_font, fill=(60, 60, 60, 255), spacing=6)
            y += body_font.size * (summary_wrapped.count('\n')+1) + 40

            # 출처 (카드 하단에서 120px + 2줄 위)
            source_max_width = self.WIDTH - 2*padding_x
            source_wrapped = self._wrap_text(source, source_font, source_max_width)
            source_y = self.HEIGHT - 120 - (source_font.size * (source_wrapped.count('\n')+1)) - (source_font.size * 2)
            draw.text((padding_x, source_y), source_wrapped, font=source_font, fill=(100, 100, 100, 200), spacing=2)

            # 5. 이미지 저장
            image_filename = f"news_{news_item['id']:03d}_{self.timestamp}.png"
            image_path = os.path.join(self.image_output_dir, image_filename)
            image = image.convert('RGB')
            image.save(image_path, "PNG", quality=95)

            return {
                "path": image_path,
                "timestamp": self.timestamp,
                "category": news_item['category'],
                "title": title
            }
        except Exception as e:
            print(f"[이미지] 생성 실패 ({news_item['id']}): {e}")
            return None
            
    def _wrap_text(self, text, font, max_width):
        """텍스트 자동 줄바꿈"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if not current_line:
                    while word:
                        for i in range(len(word), 0, -1):
                            part = word[:i]
                            bbox = font.getbbox(part)
                            if bbox[2] - bbox[0] <= max_width:
                                lines.append(part)
                                word = word[i:]
                                break
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
        
    def create_video(self, image_info):
        """이미지를 동영상으로 변환"""
        try:
            video_filename = os.path.basename(image_info["path"]).replace(".png", ".mp4")
            video_path = os.path.join(self.video_output_dir, video_filename)
            
            # 줌 효과 적용
            cmd = [
                self.ffmpeg_path, "-y",
                "-i", image_info["path"],
                "-vf", f"scale=iw*{self.zoom_scale}:-1,zoompan=z='min(zoom+0.0015,1.1)':d={self.duration*25}:s=1080x1920",
                "-t", str(self.duration),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                video_path
            ]
            
            # STARTUPINFO 설정 (Windows에서 콘솔 창 숨기기)
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 프로세스 실행 시 encoding 설정
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='replace'
            )
            
            # 출력 읽기
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"[동영상] FFmpeg 오류: {stderr}")
                return None
            
            if not os.path.exists(video_path):
                print(f"[동영상] 생성 실패: {video_filename}")
                return None
            
            return {
                "path": video_path,
                "timestamp": image_info["timestamp"],
                "category": image_info["category"],
                "title": image_info["title"]
            }
            
        except Exception as e:
            print(f"[동영상] 생성 실패: {e}")
            return None
            
    def combine_videos(self, video_list):
        """동영상 결합"""
        list_file = None
        temp_combined = None
        try:
            if not video_list:
                print("[결합] 결합할 동영상이 없습니다.")
                return None
            
            # 동영상 존재 확인
            for video in video_list:
                if not os.path.exists(video):
                    print(f"[결합] 동영상 파일이 없습니다: {video}")
                    return None
            
            # 동영상 목록 파일 생성 (UTF-8 인코딩 사용)
            list_file = os.path.join(self.temp_dir, "video_list.txt")
            with open(list_file, "w", encoding="utf-8") as f:
                for video in video_list:
                    # 경로를 UTF-8로 처리하고 역슬래시를 슬래시로 변환
                    safe_path = os.path.abspath(video).replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")
            
            # STARTUPINFO 설정
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 결합 파일 경로
            combined_filename = f"combined_news_{self.timestamp}.mp4"
            temp_combined = os.path.join(self.temp_dir, f"temp_{combined_filename}")
            final_combined = os.path.join(self.video_output_dir, combined_filename)
            
            # 동영상 결합
            concat_cmd = [
                self.ffmpeg_path, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                temp_combined
            ]
            
            # 프로세스 실행
            process = subprocess.Popen(
                concat_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='replace'
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"[결합] FFmpeg 오류: {stderr}")
                return None
            
            if not os.path.exists(temp_combined):
                print("[결합] 임시 파일이 생성되지 않았습니다.")
                return None
            
            # 배경음악 추가
            bgm_path = os.path.join(self.assets_dir, "bgm.mp3")
            if os.path.exists(bgm_path):
                total_duration = len(video_list) * self.duration
                audio_cmd = [
                    self.ffmpeg_path, "-y",
                    "-i", temp_combined,
                    "-ss", "9",
                    "-i", bgm_path,
                    "-filter_complex",
                    f"[1:a]volume=0.352,aloop=loop=-1:size=0,asetpts=N/SR/TB,afade=t=in:st=0:d=1,afade=t=out:st={total_duration-1}:d=1[a]",
                    "-map", "0:v", "-map", "[a]",
                    "-shortest",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    final_combined
                ]
                
                process = subprocess.Popen(
                    audio_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo,
                    encoding='utf-8',
                    errors='replace'
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    print(f"[결합] 배경음악 추가 실패: {stderr}")
                    shutil.move(temp_combined, final_combined)
            else:
                shutil.move(temp_combined, final_combined)
            
            if not os.path.exists(final_combined):
                print("[결합] 최종 파일이 생성되지 않았습니다.")
                return None
            
            print(f"[결합] 동영상 결합 완료: {final_combined}")
            
            # 원본 동영상 파일 저장
            self.original_videos = video_list
            
            return final_combined
            
        except Exception as e:
            print(f"[결합] 실패: {e}")
            return None
        finally:
            try:
                if list_file and os.path.exists(list_file):
                    os.remove(list_file)
                if temp_combined and os.path.exists(temp_combined):
                    os.remove(temp_combined)
            except Exception as e:
                print(f"[결합] 임시 파일 삭제 실패: {e}")
                
    def create_metadata(self, news_list, combined_path):
        """메타데이터 생성"""
        try:
            if not os.path.exists(combined_path):
                print(f"[메타데이터] 결합된 동영상 파일이 없습니다: {combined_path}")
                return None
            
            # 현재 날짜/시간
            current_time = datetime.now()
            date_str = current_time.strftime('%Y년 %m월 %d일')
            
            # 포함된 카테고리 추출
            category_news = defaultdict(list)
            for news in news_list:
                category = news["category"].strip("[]")
                category_news[category].append(news)
            
            # 포함된 카테고리 추출
            included_categories = list(category_news.keys())

            # 영어 카테고리 변환(예시)
            category_map = {
                "Economy": "Economy",
                "Politics": "Politics",
                "스포츠": "Sports",
                "연예": "Entertainment"
            }
            eng_categories = [category_map.get(cat, cat) for cat in included_categories]

            # RSS.txt에서 쿠팡파트너스 대가성문구와 링크 읽기
            coupang_notice = ''
            coupang_link = ''
            try:
                with open(os.path.join(self.assets_dir, 'RSS.txt'), 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for idx, line in enumerate(lines):
                        if '[쿠팡파트너스]' in line:
                            # 다음 줄에 링크가 있을 경우 추출
                            if idx+1 < len(lines) and ':' in lines[idx+1]:
                                coupang_link = lines[idx+1].split(':',1)[1].strip()
                        if '[쿠팡파트너스 대가성문구]' in line:
                            # 다음 줄에 문구가 있을 경우 추출
                            if idx+1 < len(lines):
                                coupang_notice = lines[idx+1].strip()
            except Exception as e:
                print(f"[쿠팡파트너스 문구 읽기 실패]: {e}")

            # 제목 생성 (대가성문구추가)
            title = f"{date_str} " + " ".join([f"#{cat} News" for cat in included_categories])
            if coupang_notice:
                title += f"   {coupang_notice}"
            

            # 설명 생성 (카테고리 부분을 #카테고리 News 형태로)
            description = f"{date_str} " + " ".join([f"#{cat} News" for cat in included_categories]) + "\n"
            # 쿠팡파트너스 대가성문구/링크를 먼저 추가
            if coupang_notice:
                description += f"{coupang_notice}\n"
            if coupang_link:
                description += f"{coupang_link}\n\n"
            description += f"=== 오늘의 {'/'.join(included_categories)} 뉴스 ===\n"
            for category, news_items in category_news.items():
                if news_items:
                    description += f"\n[{category}]\n"
                    for news in news_items:
                        title_text = news["title"].replace("📌 제목: ", "")
                        url = news["source"].split("\n")[1].split(" ")[1]
                        description += f"- {title_text}\n  {url}\n"

            # 태그 생성 (SEO 최적화 & 유튜브 정책 준수)
            tags = []
            # 1. 핵심 태그
            tags.extend([
                "뉴스",
                "뉴스요약",
                "오늘의뉴스",
                "뉴스브리핑"
            ])

            # 2. 날짜 태그
            current_date = current_time
            date_tags = [
                f"{current_date.strftime('%Y년%m월%d일')}",
                f"{current_date.strftime('%m월%d일')}",
                "오늘의뉴스"
            ]
            tags.extend(date_tags)

            # 3. 카테고리별 태그 (한글/영문)
            for category, eng_category in zip(included_categories, eng_categories):
                # 한글 태그
                tags.extend([
                    f"{category}뉴스",
                    f"{category}뉴스요약"
                ])
                # 영문 태그 (필수만)
                tags.append(f"{eng_category} News")

            # 4. 해시태그 (핵심 및 카테고리별)
            hashtags = [
                "#뉴스",
                "#뉴스요약",
                "#오늘의뉴스"
            ]
            for category in included_categories:
                hashtags.append(f"#{category}뉴스")
            tags.extend(hashtags)

            # 5. 트렌드 키워드
            trend_tags = [
                "실시간뉴스",
                "주요뉴스"
            ]
            tags.extend(trend_tags)

            # 6. 중복 제거 및 정렬
            tags = sorted(list(set(tags)))

            # 7. 태그 개수 제한 (YouTube는 최대 500자)
            max_tags_length = 450
            final_tags = []
            current_length = 0
            for tag in tags:
                tag_length = len(tag) + 1  # 쉼표 포함
                if current_length + tag_length <= max_tags_length:
                    final_tags.append(tag)
                    current_length += tag_length
                else:
                    break

            # YouTube 카테고리 자동 설정
            entertainment_set = {"스포츠", "연예", "Sports", "Entertainment"}
            if set(included_categories).issubset(entertainment_set):
                youtube_category = "Entertainment"
            else:
                youtube_category = "News & Politics"

            metadata = {
                "video_path": combined_path.replace("\\", "/"),
                "timestamp": self.timestamp,
                "duration": self.duration,
                "title": title,
                "description": description,
                "tags": final_tags,
                "category": youtube_category,  # YouTube 카테고리 자동
                "privacy_status": "private",
                "news_segments": []
            }
            
            metadata_path = os.path.join(
                self.video_output_dir, 
                f"video_metadata_{self.timestamp}.json"
            )
            
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            print(f"[메타데이터] 저장 완료: {metadata_path}")
            
            # 원본 동영상 파일 삭제
            if hasattr(self, 'original_videos'):
                for video in self.original_videos:
                    if os.path.exists(video):
                        try:
                            os.remove(video)
                        except Exception as e:
                            print(f"[메타데이터] 원본 동영상 삭제 실패: {video} - {e}")
                delattr(self, 'original_videos')
            
            return metadata_path
            
        except Exception as e:
            print(f"[메타데이터] 생성 실패: {e}")
            return None
            
    def process(self):
        """전체 처리 과정"""
        try:
            # 1. 뉴스 수집
            news_list = self.collect_news()
            if not news_list:
                print("[처리] 뉴스 수집 실패")
                return False
            
            # 2. 이미지 생성
            print("\n=== 2단계: 이미지 생성 시작 ===")
            image_results = []
            for news_item in news_list:
                image_info = self.create_news_image(news_item)
                if image_info:
                    image_results.append({
                        "news_id": news_item["id"],
                        "image_info": image_info,
                        "news_data": news_item
                    })
            
            if not image_results:
                print("[처리] 이미지 생성 실패")
                return False
                
            print(f"[처리] {len(image_results)}개의 이미지 생성 완료")
            
            # 3. 동영상 생성
            print("\n=== 3단계: 동영상 생성 시작 ===")
            video_files = []
            for result in image_results:
                video_info = self.create_video(result["image_info"])
                if video_info:
                    video_files.append(video_info["path"])
            
            if not video_files:
                print("[처리] 동영상 생성 실패")
                return False
                
            print(f"[처리] {len(video_files)}개의 동영상 생성 완료")
            
            # 4. 동영상 결합
            print("\n=== 4단계: 동영상 결합 시작 ===")
            combined_path = self.combine_videos(video_files)
            if not combined_path:
                print("[처리] 동영상 결합 실패")
                return False
            
            # 5. 메타데이터 생성
            print("\n=== 5단계: 메타데이터 생성 시작 ===")
            metadata_path = self.create_metadata(news_list, combined_path)
            if not metadata_path:
                print("[처리] 메타데이터 생성 실패")
                return False
            
            # 6. 디렉토리 정리
            self._cleanup_old_directories(self.images_dir)
            self._cleanup_old_directories(self.videos_dir)
            
            print("\n=== 처리 완료 ===")
            print(f"- 처리된 뉴스: {len(news_list)}개")
            print(f"- 생성된 이미지: {len(image_results)}개")
            print(f"- 생성된 동영상: {len(video_files)}개")
            print(f"- 결합된 동영상: {os.path.basename(combined_path)}")
            print(f"- 메타데이터: {os.path.basename(metadata_path)}")
            
            return True
            
        except Exception as e:
            print(f"[처리] 오류 발생: {e}")
            return False

if __name__ == "__main__":
    processor = NewsProcessor()
    processor.process() 
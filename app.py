import os
import urllib.request
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'fb_cookies.txt')

# ১. হোম / হেলথ চেক রুট (UptimeRobot এর জন্য)
@app.route('/', methods=['GET', 'HEAD'])
def home():
    return jsonify({'status': 'API is running'}), 200


# ==========================================
#              FACEBOOK ROUTES
# ==========================================

# ফেসবুক ভিডিও ডাউনলোডার
@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
        if os.path.exists(COOKIE_FILE):
            ydl_opts['cookiefile'] = COOKIE_FILE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'InsightsWonders_FB_Video')
            formats = info.get('formats', [])

            variants = []
            if info.get('url'):
                variants.append({
                    'quality': 'Standard Quality (With Audio)',
                    'type': 'Video',
                    'url': info.get('url')
                })

            for f in formats:
                url_link = f.get('url')
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                format_id = str(f.get('format_id', '')).lower()

                if not url_link or vcodec == 'none':
                    continue

                height = f.get('height')
                res = f"{height}p" if height else ("HD" if "hd" in format_id or "hd" in url_link else "SD")

                if acodec != 'none' and acodec is not None:
                    quality_name = f"Video ({res}) - With Audio"
                elif "hd" in format_id or "sd" in format_id:
                    quality_name = f"Video ({res}) - With Audio"
                else:
                    quality_name = f"Video ({res}) - Without Audio"

                variants.append({
                    'quality': quality_name,
                    'type': 'Video',
                    'url': url_link
                })

            unique_variants = list({v['quality']: v for v in variants}.values())
            if not unique_variants:
                return jsonify({'success': False, 'error': 'No video streams found'}), 400

            return jsonify({'success': True, 'title': title, 'variants': unique_variants})

    except Exception as e:
        return jsonify({'success': False, 'error': f"Failed to process video: {str(e)}"}), 500


# ফেসবুক অডিও ডাউনলোডার
@app.route('/download-audio', methods=['POST'])
def download_audio():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        if os.path.exists(COOKIE_FILE):
            ydl_opts['cookiefile'] = COOKIE_FILE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'InsightsWonders_FB_Audio')
            formats = info.get('formats', [])

            variants = []
            for f in formats:
                url_link = f.get('url')
                acodec = f.get('acodec')
                vcodec = f.get('vcodec')

                if url_link and acodec != 'none' and vcodec == 'none':
                    abr = f.get('abr')
                    quality_name = f"High Quality Audio ({int(abr)}kbps)" if abr else "MP3 / Audio"
                    variants.append({'quality': quality_name, 'type': 'Audio', 'url': url_link})

            if not variants and info.get('url'):
                variants.append({'quality': 'Standard MP3 Audio', 'type': 'Audio', 'url': info.get('url')})

            unique_variants = list({v['quality']: v for v in variants}.values())
            return jsonify({'success': True, 'title': title, 'variants': unique_variants})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ফেসবুক ইমেজ ডাউনলোডার
@app.route('/download-image', methods=['POST'])
def download_image():
    data = request.get_json()
    raw_url = data.get('url') if data else None

    if not raw_url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        images = []
        title = "InsightsWonders_Image"
        fetch_url = raw_url.replace('www.facebook.com', 'mbasic.facebook.com')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        try:
            response = requests.get(fetch_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                og_images = soup.find_all('meta', property='og:image')
                for idx, img in enumerate(og_images):
                    img_src = img.get('content')
                    if img_src:
                        images.append({'quality': f"Photo {idx + 1} (HD Quality)", 'type': 'Image', 'url': img_src})

                if not images:
                    for idx, img in enumerate(soup.find_all('img')):
                        src = img.get('src')
                        if src and ('scontent' in src or 'fbcdn' in src):
                            images.append({'quality': f"Photo {idx + 1} (HD Quality)", 'type': 'Image', 'url': src})
        except Exception:
            pass

        if not images:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            if os.path.exists(COOKIE_FILE):
                ydl_opts['cookiefile'] = COOKIE_FILE

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(raw_url, download=False)
                title = info.get('title', 'InsightsWonders_Image')

                if 'entries' in info:
                    for idx, entry in enumerate(info['entries']):
                        img_url = entry.get('url') or entry.get('thumbnail')
                        if img_url:
                            images.append({'quality': f"Photo {idx + 1} (HD Quality)", 'type': 'Image', 'url': img_url})

                if not images:
                    img_url = info.get('url') or info.get('thumbnail')
                    thumbnails = info.get('thumbnails', [])
                    if thumbnails:
                        img_url = thumbnails[-1].get('url')
                    if img_url:
                        images.append({'quality': 'Full HD Photo', 'type': 'Image', 'url': img_url})

        if not images:
            return jsonify({'success': False, 'error': 'Unable to extract photo. Make sure the post is public.'}), 400

        unique_images = list({v['url']: v for v in images}.values())
        return jsonify({'success': True, 'title': title, 'variants': unique_images})

    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to process image.'}), 500


# ==========================================
#              YOUTUBE ROUTES (FIXED)
# ==========================================

# ৫. ইউটিউব ভিডিও ডাউনলোডার (Bypass 403)
@app.route('/download-youtube-video', methods=['POST'])
def download_youtube_video():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'mweb', 'tv_embedded'],
                    'skip': ['hls', 'dash']
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube_Video')
            formats = info.get('formats', [])

            variants = []
            for f in formats:
                url_link = f.get('url')
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                height = f.get('height')

                if url_link and vcodec != 'none':
                    res = f"{height}p" if height else "SD"
                    
                    if acodec != 'none' and acodec is not None:
                        quality_name = f"Video ({res}) - With Audio"
                    else:
                        quality_name = f"Video ({res}) - Without Audio"

                    variants.append({
                        'quality': quality_name,
                        'type': 'Video',
                        'url': url_link
                    })

            # রেজুলেশন অনুযায়ী ডুপ্লিকেট সরানো
            unique_variants = list({v['quality']: v for v in variants}.values())
            
            if not unique_variants:
                return jsonify({'success': False, 'error': 'No video streams found.'}), 400

            return jsonify({'success': True, 'title': title, 'variants': unique_variants})

    except Exception as e:
        return jsonify({'success': False, 'error': f"Failed to process YouTube video: {str(e)}"}), 500


# ৬. ইউটিউব অডিও/MP3 ডাউনলোডার (Bypass 403)
@app.route('/download-youtube-audio', methods=['POST'])
def download_youtube_audio():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'mweb', 'tv_embedded']
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube_Audio')
            formats = info.get('formats', [])

            variants = []
            for f in formats:
                url_link = f.get('url')
                acodec = f.get('acodec')
                vcodec = f.get('vcodec')

                if url_link and acodec != 'none' and vcodec == 'none':
                    abr = f.get('abr')
                    quality_name = f"Audio MP3 ({int(abr)}kbps)" if abr else "High Quality MP3"
                    variants.append({
                        'quality': quality_name,
                        'type': 'Audio',
                        'url': url_link
                    })

            unique_variants = list({v['quality']: v for v in variants}.values())
            
            if not unique_variants and info.get('url'):
                unique_variants.append({
                    'quality': 'Standard Quality MP3',
                    'type': 'Audio',
                    'url': info.get('url')
                })

            return jsonify({'success': True, 'title': title, 'variants': unique_variants})

    except Exception as e:
        return jsonify({'success': False, 'error': f"Failed to process YouTube audio: {str(e)}"}), 500

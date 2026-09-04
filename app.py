import os
import urllib.request
import requests
from bs4 import BeautifulSoup
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

# কুকি ফাইলের পাথ
FB_COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'fb_cookies.txt')
YT_COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'yt_cookies.txt')


# ১. হেলথ চেক
@app.route('/', methods=['GET', 'HEAD'])
def home():
    return jsonify({'status': 'API is running'}), 200


# ==========================================
#              FACEBOOK ROUTES
# ==========================================

@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
        if os.path.exists(FB_COOKIE_FILE):
            ydl_opts['cookiefile'] = FB_COOKIE_FILE

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


@app.route('/download-audio', methods=['POST'])
def download_audio():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        if os.path.exists(FB_COOKIE_FILE):
            ydl_opts['cookiefile'] = FB_COOKIE_FILE

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
            if os.path.exists(FB_COOKIE_FILE):
                ydl_opts['cookiefile'] = FB_COOKIE_FILE

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
#       YOUTUBE ROUTES (INVIDIOUS API)
# ==========================================

def get_yt_video_id(url):
    """ইউআরএল থেকে ভিডিও আইডি বের করার ফাংশন"""
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0].split('&')[0]
    elif 'v=' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'shorts/' in url:
        return url.split('shorts/')[1].split('?')[0].split('&')[0]
    return None


@app.route('/download-youtube-video', methods=['POST'])
def download_youtube_video():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    video_id = get_yt_video_id(url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400

    # Invidious ওপেন সোর্স এপিআই ইনস্ট্যান্স তালিকা
    invidious_instances = [
        "https://inv.nadeko.net",
        "https://invidious.nerdvpn.de",
        "https://invidious.flokinet.to",
        "https://invidious.privacydev.net"
    ]

    for instance in invidious_instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=7)
            if res.status_code == 200:
                data = res.json()
                title = data.get('title', 'YouTube_Video')
                variants = []

                # ১. কম্বাইন্ড ফরম্যাট
                for fmt in data.get('formatStreams', []):
                    if fmt.get('url'):
                        quality = fmt.get('qualityLabel', 'Video SD')
                        variants.append({
                            'quality': f"Video ({quality}) - With Audio",
                            'type': 'Video',
                            'url': fmt.get('url')
                        })

                # ২. অ্যাডাপ্টিভ ফরম্যাট (যদি কম্বাইন্ড না পাওয়া যায়)
                if not variants:
                    for fmt in data.get('adaptiveFormats', []):
                        if fmt.get('url') and 'video' in fmt.get('type', ''):
                            quality = fmt.get('qualityLabel', 'Video Stream')
                            variants.append({
                                'quality': f"Video ({quality})",
                                'type': 'Video',
                                'url': fmt.get('url')
                            })

                if variants:
                    unique_variants = list({v['quality']: v for v in variants}.values())
                    return jsonify({'success': True, 'title': title, 'variants': unique_variants})
        except Exception:
            continue

    # এপিআই ব্যর্থ হলে yt-dlp ব্যাকআপ হিসেবে কল হবে
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True, 'format': 'best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return jsonify({
                'success': True, 
                'title': info.get('title', 'YouTube Video'),
                'variants': [{'quality': 'Standard Quality Video', 'type': 'Video', 'url': info.get('url')}]
            })
    except Exception as e:
        return jsonify({'success': False, 'error': 'Unable to fetch video. YouTube server blocked the request.'}), 500


@app.route('/download-youtube-audio', methods=['POST'])
def download_youtube_audio():
    data = request.get_json()
    url = data.get('url') if data else None

    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    video_id = get_yt_video_id(url)
    if not video_id:
        return jsonify({'success': False, 'error': 'Invalid YouTube URL'}), 400

    invidious_instances = [
        "https://inv.nadeko.net",
        "https://invidious.nerdvpn.de",
        "https://invidious.flokinet.to",
        "https://invidious.privacydev.net"
    ]

    for instance in invidious_instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=7)
            if res.status_code == 200:
                data = res.json()
                title = data.get('title', 'YouTube_Audio')
                variants = []

                for fmt in data.get('adaptiveFormats', []):
                    if fmt.get('url') and 'audio' in fmt.get('type', ''):
                        bitrate = fmt.get('bitrate')
                        kbps = f"{int(int(bitrate)/1000)}kbps" if bitrate else "HQ"
                        variants.append({
                            'quality': f"Audio MP3 ({kbps})",
                            'type': 'Audio',
                            'url': fmt.get('url')
                        })

                if variants:
                    unique_variants = list({v['quality']: v for v in variants}.values())
                    return jsonify({'success': True, 'title': title, 'variants': unique_variants})
        except Exception:
            continue

    return jsonify({'success': False, 'error': 'Unable to fetch audio stream. Please try another link.'}), 500


# ==========================================
#              PROXY DOWNLOAD
# ==========================================

@app.route('/proxy-download', methods=['GET'])
def proxy_download():
    media_url = request.args.get('url')
    file_type = request.args.get('type', 'Video')

    if not media_url:
        return 'No URL provided', 400

    ext = 'mp3' if file_type == 'Audio' else ('jpg' if file_type == 'Image' else 'mp4')
    filename = f"InsightsWonders_{file_type}_{int(request.args.get('t', 0))}.{ext}"

    def generate():
        req = urllib.request.Request(
            media_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req) as res:
            while chunk := res.read(1024 * 1024):
                yield chunk

    response = Response(generate(), content_type='application/octet-stream')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

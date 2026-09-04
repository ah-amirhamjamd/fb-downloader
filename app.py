from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import urllib.request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'API is running'}), 200

# ১. ভিডিও ডাউনলোডার
@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url') if data else None
    
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'InsightsWonders_Video')
            formats = info.get('formats', [])
            
            variants = []
            for f in formats:
                url_link = f.get('url')
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                format_id = str(f.get('format_id', '')).lower()
                
                if not url_link or vcodec == 'none':
                    continue

                height = f.get('height')
                res = f"{height}p" if height else ("HD" if "hd" in format_id else "SD")
                
                if acodec != 'none' and acodec is not None:
                    audio_status = "With Audio"
                elif "hd" in format_id or "sd" in format_id or f.get('vcodec') != 'none':
                    if acodec == 'none':
                        audio_status = "Without Audio"
                    else:
                        audio_status = "With Audio"
                else:
                    audio_status = "Without Audio"
                
                quality_name = f"Video ({res}) - {audio_status}"
                
                variants.append({
                    'quality': quality_name,
                    'type': 'Video',
                    'url': url_link
                })

            if not variants and info.get('url'):
                variants.append({
                    'quality': 'Original Video (With Audio)',
                    'type': 'Video',
                    'url': info.get('url')
                })

            unique_variants = list({v['quality']: v for v in variants}.values())
            return jsonify({'success': True, 'title': title, 'variants': unique_variants})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ২. অডিও ডাউনলোডার
@app.route('/download-audio', methods=['POST'])
def download_audio():
    data = request.get_json()
    url = data.get('url') if data else None
    
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'InsightsWonders_Audio')
            formats = info.get('formats', [])
            
            variants = []
            for f in formats:
                url_link = f.get('url')
                acodec = f.get('acodec')
                vcodec = f.get('vcodec')
                
                if url_link and acodec != 'none' and vcodec == 'none':
                    abr = f.get('abr')
                    quality_name = f"High Quality Audio ({int(abr)}kbps)" if abr else "MP3 / Audio"
                    variants.append({
                        'quality': quality_name,
                        'type': 'Audio',
                        'url': url_link
                    })

            if not variants:
                variants.append({
                    'quality': 'Standard MP3 Audio',
                    'type': 'Audio',
                    'url': info.get('url')
                })

            unique_variants = list({v['quality']: v for v in variants}.values())
            return jsonify({'success': True, 'title': title, 'variants': unique_variants})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ৩. ইমেজ ডাউনলোডার (সংশোধিত ও কুকিজ এরর বাইপাস লজিক)
@app.route('/download-image', methods=['POST'])
def download_image():
    data = request.get_json()
    url = data.get('url') if data else None
    
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        images = []
        title = "InsightsWonders_Image"

        # ১. OpenGraph মেটা ট্যাগ স্ক্র্যাপিং (কুকিজ ও রেজিস্টার্ড ইউজার এরর এড়াতে)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # og:image দিয়ে ছবির লিঙ্ক বের করা
            og_images = soup.find_all('meta', property='og:image')
            for idx, img in enumerate(og_images):
                img_src = img.get('content')
                if img_src:
                    images.append({
                        'quality': f"Photo {idx + 1} (HD Quality)",
                        'type': 'Image',
                        'url': img_src
                    })

        # ২. স্ক্র্যাপিংয়ে না পাওয়া গেলে ব্যাকআপ হিসেবে yt-dlp কাজ করবে
        if not images:
            ydl_opts = {
                'quiet': True, 
                'no_warnings': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'InsightsWonders_Image')
                
                # ক্যারোজেল / অ্যালবাম ইমেজের ক্ষেত্রে
                if 'entries' in info:
                    for idx, entry in enumerate(info['entries']):
                        img_url = entry.get('url') or entry.get('thumbnail')
                        if img_url:
                            images.append({
                                'quality': f"Photo {idx + 1} (HD Quality)",
                                'type': 'Image',
                                'url': img_url
                            })
                
                # সিঙ্গেল ইমেজের ক্ষেত্রে
                if not images:
                    img_url = info.get('url') or info.get('thumbnail')
                    thumbnails = info.get('thumbnails', [])
                    if thumbnails:
                        img_url = thumbnails[-1].get('url')
                    
                    if img_url:
                        images.append({
                            'quality': 'Full HD Photo',
                            'type': 'Image',
                            'url': img_url
                        })

        if not images:
            return jsonify({'success': False, 'error': 'Private post or unable to fetch image. Make sure the post is public.'}), 400

        # ডুপ্লিকেট ইউআরএল ফিল্টার
        unique_images = list({v['url']: v for v in images}.values())
        return jsonify({'success': True, 'title': title, 'variants': unique_images})

    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to process image. Please try a public link.'}), 500

# ৪. প্রক্সি ডাউনলোড রাউট
@app.route('/proxy-download', methods=['GET'])
def proxy_download():
    media_url = request.args.get('url')
    file_type = request.args.get('type', 'Video')
    
    if not media_url:
        return "No URL provided", 400

    if file_type == 'Audio':
        ext = 'mp3'
    elif file_type == 'Image':
        ext = 'jpg'
    else:
        ext = 'mp4'

    filename = f"InsightsWonders_{file_type}_{int(request.args.get('t', 0))}.{ext}"

    def generate():
        req = urllib.request.Request(media_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req) as res:
            while chunk := res.read(1024 * 1024):
                yield chunk

    response = Response(generate(), content_type='application/octet-stream')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

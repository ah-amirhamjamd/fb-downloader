from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import urllib.request

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({'status': 'API is running'}), 200

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url') if data else None
    
    if not url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'InsightsWonders_Media')
            formats = info.get('formats', [])
            
            variants = []
            
            for f in formats:
                url_link = f.get('url')
                if not url_link:
                    continue

                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                height = f.get('height')
                
                # ১. অডিও স্ট্রিম (Audio Only)
                if vcodec == 'none' and acodec != 'none':
                    variants.append({
                        'quality': 'Audio Only (MP3)',
                        'type': 'Audio',
                        'url': url_link
                    })
                
                # ২. ভিডিও এবং অডিও দুটোই একসাথে আছে এমন ফরম্যাট (Combined Format)
                elif vcodec != 'none' and acodec != 'none':
                    label = f"{height}p" if height else "Video"
                    quality_name = f"HD Video ({label})" if (height and height >= 720) else f"SD Video ({label})"
                    variants.append({
                        'quality': quality_name,
                        'type': 'Video',
                        'url': url_link
                    })

            # যদি কোনো ফিল্টারে Combined ফরম্যাট না পাওয়া যায়, তবে বেস্ট ব্যাকআপ ফরম্যাট ব্যবহার হবে
            if not any(v['type'] == 'Video' for v in variants) and info.get('url'):
                variants.append({
                    'quality': 'Standard Quality (With Audio)',
                    'type': 'Video',
                    'url': info.get('url')
                })

            unique_variants = list({v['quality']: v for v in variants}.values())

            return jsonify({
                'success': True,
                'title': title,
                'variants': unique_variants
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# প্রক্সি ডাউনলোড রাউট
@app.route('/proxy-download', methods=['GET'])
def proxy_download():
    media_url = request.args.get('url')
    file_type = request.args.get('type', 'Video')
    
    if not media_url:
        return "No URL provided", 400

    ext = 'mp3' if file_type == 'Audio' else 'mp4'
    filename = f"InsightsWonders_{file_type}_{int(request.args.get('t', 0))}.{ext}"

    def generate():
        req = urllib.request.Request(media_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        })
        with urllib.request.urlopen(req) as res:
            while chunk := res.read(1024 * 1024):
                yield chunk

    response = Response(generate(), content_type='application/octet-stream')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

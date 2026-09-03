from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

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
            title = info.get('title', 'Facebook Media')
            formats = info.get('formats', [])
            
            variants = []
            
            # অডিও স্ট্রিম এবং ভিডিও স্ট্রিম আলাদা করা
            for f in formats:
                format_id = f.get('format_id', '')
                ext = f.get('ext', 'mp4')
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                url_link = f.get('url')
                
                if not url_link:
                    continue

                # অডিও ফরম্যাট
                if vcodec == 'none' and acodec != 'none':
                    variants.append({
                        'quality': 'Audio Only (MP3/M4A)',
                        'type': 'Audio',
                        'url': url_link
                    })
                # ভিডিও ফরম্যাট (HD & SD)
                elif vcodec != 'none':
                    height = f.get('height')
                    label = f"{height}p" if height else f.get('format_note', 'Video')
                    
                    if 'hd' in label.lower() or (height and height >= 720):
                        quality_name = f"HD Video ({label})"
                    else:
                        quality_name = f"SD Video ({label})"

                    variants.append({
                        'quality': quality_name,
                        'type': 'Video',
                        'url': url_link
                    })

            # যদি কোনো ফিল্টার কাজ না করে তবে ডিফল্ট লিংক
            if not variants and info.get('url'):
                variants.append({
                    'quality': 'Standard Quality',
                    'type': 'Video',
                    'url': info.get('url')
                })

            # ডুপ্লিকেট ফরম্যাট দূর করা
            unique_variants = {v['quality']: v for v in variants}.values()

            return jsonify({
                'success': True,
                'title': title,
                'variants': list(unique_variants)
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

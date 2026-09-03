from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

# UptimeRobot-এর জন্য হোমপেজ রাউট
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
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url')
            title = info.get('title', 'Facebook Video')
            
            return jsonify({
                'success': True,
                'title': title,
                'download_url': download_url
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

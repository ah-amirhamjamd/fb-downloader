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


@app.route('/', methods=['GET'])
def home():
  return jsonify({'status': 'API is running'}), 200


# ১. ভিডিও ডাউনলোডার (সংশোধিত অডিও লজিকসহ)
@app.route('/download-video', methods=['POST'])
def download_video():
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
      title = info.get('title', 'InsightsWonders_Video')
      formats = info.get('formats', [])

      variants = []
      for f in formats:
        url_link = f.get('url')
        vcodec = f.get('vcodec')
        acodec = f.get('acodec')
        format_id = str(f.get('format_id', '')).lower()

        # ভিডিও স্ট্রিম না থাকলে এড়িয়ে যাবে
        if not url_link or vcodec == 'none':
          continue

        height = f.get('height')
        res = f'{height}p' if height else ('HD' if 'hd' in format_id else 'SD')

        # অডিও স্টেটাস সঠিক উপায়ে নির্ণয়
        if acodec != 'none' and acodec is not None:
          audio_status = 'With Audio'
        else:
          audio_status = 'Without Audio'

        quality_name = f'Video ({res}) - {audio_status}'

        variants.append(
            {'quality': quality_name, 'type': 'Video', 'url': url_link}
        )

      if not variants and info.get('url'):
        variants.append({
            'quality': 'Original Video (With Audio)',
            'type': 'Video',
            'url': info.get('url'),
        })

      unique_variants = list({v['quality']: v for v in variants}.values())
      return jsonify
      ({'success': True, 'title': title, 'variants': unique_variants})

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
    if os.path.exists(COOKIE_FILE):
      ydl_opts['cookiefile'] = COOKIE_FILE

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
          quality_name = (
              f'High Quality Audio ({int(abr)}kbps)'
              if abr
              else 'MP3 / Audio'
          )
          variants.append(
              {'quality': quality_name, 'type': 'Audio', 'url': url_link}
          )

      if not variants:
        variants.append({
            'quality': 'Standard MP3 Audio',
            'type': 'Audio',
            'url': info.get('url'),
        })

      unique_variants = list({v['quality']: v for v in variants}.values())
      return jsonify
      ({'success': True, 'title': title, 'variants': unique_variants})

  except Exception as e:
    return jsonify({'success': False, 'error': str(e)}), 500


# ৩. ইমেজ ডাউনলোডার
@app.route('/download-image', methods=['POST'])
def download_image():
  data = request.get_json()
  raw_url = data.get('url') if data else None

  if not raw_url:
    return jsonify({'success': False, 'error': 'No URL provided'}), 400

  try:
    images = []
    title = 'InsightsWonders_Image'

    fetch_url = raw_url.replace('www.facebook.com', 'mbasic.facebook.com')

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
      response = requests.get(fetch_url, headers=headers, timeout=10)
      if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        og_images = soup.find_all('meta', property='og:image')
        for idx, img in enumerate(og_images):
          img_src = img.get('content')
          if img_src:
            images.append({
                'quality': f'Photo {idx + 1} (HD Quality)',
                'type': 'Image',
                'url': img_src,
            })

        if not images:
          for idx, img in enumerate(soup.find_all('img')):
            src = img.get('src')
            if src and ('scontent' in src or 'fbcdn' in src):
              images.append({
                  'quality': f'Photo {idx + 1} (HD Quality)',
                  'type': 'Image',
                  'url': src,
              })
    except Exception:
      pass

    if not images:
      ydl_opts = {
          'quiet': True,
          'no_warnings': True,
          'user_agent': (
              'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          ),
      }
      if os.path.exists(COOKIE_FILE):
        ydl_opts['cookiefile'] = COOKIE_FILE

      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(raw_url, download=False)
        title = info.get('title', 'InsightsWonders_Image')

        if 'entries' in info:
          for idx, entry in enumerate(info['entries']):
            img_url = entry.get('url') or entry.get('thumbnail')
            if img_url:
              images.append({
                  'quality': f'Photo {idx + 1} (HD Quality)',
                  'type': 'Image',
                  'url': img_url,
              })

        if not images:
          img_url = info.get('url') or info.get('thumbnail')
          thumbnails = info.get('thumbnails', [])
          if thumbnails:
            img_url = thumbnails[-1].get('url')

          if img_url:
            images.append(
                {'quality': 'Full HD Photo', 'type': 'Image', 'url': img_url}
            )

    if not images:
      return (
          jsonify({
              'success': False,
              'error': (
                  'Unable to extract photo. Make sure the post is public or try'
                  ' copying the direct photo link.'
              ),
          }),
          400,
      )

    unique_images = list({v['url']: v for v in images}.values())
    return jsonify({'success': True, 'title': title, 'variants': unique_images})

  except Exception as e:
    return (
        jsonify({
            'success': False,
            'error': 'Failed to process image. Make sure the post is public.',
        }),
        500,
    )


# ৪. প্রক্সি ডাউনলোড রাউট
@app.route('/proxy-download', methods=['GET'])
def proxy_download():
  media_url = request.args.get('url')
  file_type = request.args.get('type', 'Video')

  if not media_url:
    return 'No URL provided', 400

  ext = (
      'mp3'
      if file_type == 'Audio'
      else ('jpg' if file_type == 'Image' else 'mp4')
  )
  filename = (
      f"InsightsWonders_{file_type}_{int(request.args.get('t', 0))}.{ext}"
  )

  def generate():
    req = urllib.request.Request(
        media_url,
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
        },
    )
    with urllib.request.urlopen(req) as res:
      while chunk := res.read(1024 * 1024):
        yield chunk

  response = Response(generate(), content_type='application/octet-stream')
  response.headers['Content-Disposition'] = (
      f'attachment; filename="{filename}"'
  )
  return response


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)

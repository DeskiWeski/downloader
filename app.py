from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
from youtube_search import YoutubeSearch
import time
import os
import threading

app = Flask(__name__)
CORS(app)

# Directory setup for audio and video downloads
BASE_DOWNLOAD_FOLDER = "downloads"
AUDIO_FOLDER = os.path.join(BASE_DOWNLOAD_FOLDER, "Audio")
VIDEO_FOLDER = os.path.join(BASE_DOWNLOAD_FOLDER, "Video")

# Ensure download directories exist
for folder in [AUDIO_FOLDER, VIDEO_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

def get_youtube_songs(artist_name):
    # Queries to search on YouTube
    queries = [
        f"{artist_name} songs",
        f"{artist_name} new songs", 
        f"{artist_name} best songs"
    ]
    
    all_songs = []
    
    try:
        for query in queries:
            search_results = YoutubeSearch(query, max_results=100).to_dict()
            for video in search_results:
                title = video['title']
                duration = video['duration']
                url = f"https://youtube.com/watch?v={video['id']}"
                all_songs.append({
                    'title': title,
                    'duration': duration,
                    'url': url
                })
        
        return all_songs
    
    except Exception as e:
        print(f"Error searching YouTube: {e}")
        return []

@app.route('/artist_songs', methods=['POST'])
def fetch_artist_songs():
    data = request.get_json()
    artist_name = data.get('artist')

    if not artist_name:
        return jsonify({"error": "No artist name provided"}), 400

    try:
        songs = get_youtube_songs(artist_name)

        if not songs:
            return jsonify({"error": "No songs found for this artist."}), 404

        return jsonify({
            "songs": [song['title'] for song in songs],
            "metadata": songs
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/convert', methods=['POST'])
def convert_to_mp3():
    data = request.get_json()
    video_url = data.get('url')
    filename = data.get('filename', '')  # Get the filename if provided

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # Generate unique filename using timestamp
        timestamp = str(int(time.time()))
        if filename:
            output_template = os.path.join(AUDIO_FOLDER, f'{filename}_{timestamp}.%(ext)s')
        else:
            # Extract info first to get the title
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(video_url, download=False)
                title = info.get('title', 'song').replace('/', '-')
                output_template = os.path.join(AUDIO_FOLDER, f'{title}_{timestamp}.%(ext)s')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'no_playlist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            # Convert filename to mp3 since that's our target format
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            
            if os.path.exists(mp3_filename):
                download_path = mp3_filename
                return jsonify({
                    "success": True,
                    "message": "Download completed",
                    "file": os.path.basename(download_path)
                })
            else:
                return jsonify({"error": "File not found after download"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/convert_video', methods=['POST'])
def convert_to_video():
    data = request.get_json()
    video_url = data.get('url')

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # First extract info to get the title
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'video').replace('/', '-')
            timestamp = str(int(time.time()))
            output_template = os.path.join(VIDEO_FOLDER, f'{title}_{timestamp}.%(ext)s')

        ydl_opts = {
            'format': 'best',
            'outtmpl': output_template,
            'no_playlist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                return jsonify({
                    "success": True,
                    "message": "Download completed",
                    "file": os.path.basename(filename)
                })
            else:
                return jsonify({"error": "File not found after download"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/downloads/<folder>/<filename>')
def download_file(folder, filename):
    if folder not in ['Audio', 'Video']:
        return jsonify({"error": "Invalid folder"}), 400
        
    file_path = os.path.join(BASE_DOWNLOAD_FOLDER, folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
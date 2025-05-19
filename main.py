from flask import Flask, render_template, request, session
from dotenv import load_dotenv
import os
import requests
from datetime import datetime
import subprocess

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def is_ffmpeg_available():
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def generate_ass(text, output_path="static/text/subs.ass", words_per_second=2.5, chunk_size=2, max_chars=16):
    words = text.split()
    start = 0.0
    index = 0

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,60,&H00FFD700,&H00000000,&H00000000,1,0,1,3,2,5,30,30,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

    dialogue = []

    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        chunk_text = ' '.join(chunk)
        duration = len(chunk) / words_per_second
        end = start + duration

     
        font_size_tag = r"\fs60"
        if len(chunk_text) > max_chars:
            font_size_tag = r"\fs38"

        start_time = format_ass_time(start)
        end_time = format_ass_time(end)

        dialogue.append(
    f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{{\\an5\\fscx0\\fscy0\\fad(150,150)\\t(0,200,\\fscx100\\fscy100){font_size_tag}}}{chunk_text}"
)



        start = end
        index += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + "\n" + "\n".join(dialogue))


def generate_speech(text, audio_path="static/audio/speech.mp3"):
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

    if not ELEVENLABS_API_KEY:
        raise ValueError("ElevenLabs API key not found in environment variables")

    voice_id = "TxGEqnHWrfWFTfGW9XjX"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        with open(audio_path, "wb") as f:
            f.write(response.content)
        return audio_path
    else:
        raise RuntimeError(f"ElevenLabs TTS failed: {response.status_code} - {response.text}")


def generate_video(audio_path, subtitle_path, base_video, output_path="static/videos/production/final_video.mp4"):
    silent_video = "static/temp_silent.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", base_video,
        "-c:v", "copy", "-an",
        silent_video
    ])
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    audio_duration = float(result.stdout)
    looped_video = "static/temp_looped.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", silent_video,
        "-t", str(audio_duration), "-c:v", "copy", looped_video
    ])
    temp_video = "static/temp_combined.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", looped_video, "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-shortest", temp_video
    ])
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_video,
        "-vf", f"ass={subtitle_path}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "28",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ])
    return output_path


def query_openrouter_model(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
    }
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error: {e}"


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
FFMPEG_AVAILABLE = is_ffmpeg_available()


@app.route("/", methods=["GET", "POST"])
def index():
    if not FFMPEG_AVAILABLE:
        return render_template("error.html", message="FFmpeg is not installed or not found in system PATH")
    
    user_input = ""
    model_response = ""
    video_url = None

    for file_key in ["last_video", "last_audio", "last_subs"]:
        path = session.get(file_key)
        if path:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
            session.pop(file_key, None)

    if request.method == "POST":
        user_input = request.form.get("user_text", "")
        background_choice = request.form.get("background_choice", "subway")

        if user_input:
            model_response = query_openrouter_model(user_input)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = f"static/audio/speech_{timestamp}.mp3"
            subtitle_path = f"static/text/subs_{timestamp}.ass"
            video_path = f"static/videos/production/final_{timestamp}.mp4"

            base_video = (
                "static/videos/background_minecraft.mp4"
                if background_choice == "minecraft"
                else "static/videos/background_subway.mp4"
            )

            generate_speech(model_response, audio_path)
            generate_ass(model_response, subtitle_path)
            generate_video(audio_path, subtitle_path, base_video, video_path)

            session["last_audio"] = audio_path
            session["last_subs"] = subtitle_path
            session["last_video"] = video_path
            video_url = video_path

    return render_template("index.html", user_input=user_input, gpt_response=model_response, video_url=video_url)


if __name__ == "__main__":
    app.run(debug=True)

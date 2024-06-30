from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import urllib.parse as urllib
import os
from pydub import AudioSegment

def id(link: str):
    url_data = urllib.urlparse(link)
    query = urllib.parse_qs(url_data.query)
    return query["v"][0]

def get_transcript(link: str):
    video_id = id(link)
    script = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr'])
    file_name = f"{video_id}.txt"
    with open(file_name, 'w') as file: 
        for i in range(len(script) - 1): # son texti görmezden geliyor ancak önemli değil
            line = script[i]
            next_line = script[i + 1]
            file.write(f"{line['text']} ['start']: {line['start']} ['end']: {next_line['start']}\n")

def download_audio(link: str):
    if os.path.exists("audio.mp3"):
        os.remove("audio.mp3")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'audio.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])

def check_audio(audio: AudioSegment):
    segsize = 100
    first_segment = audio[:segsize].rms
    last_segment = audio[-segsize:].rms
    threshold = audio.rms * 0.8

    if first_segment > threshold or last_segment > threshold:
        return False
    return True
    

def scrape(link: str):
    video_id = id(link)
    os.makedirs(video_id, exist_ok=True)
    transcript_file = f"{video_id}.txt"
    with open(transcript_file, 'r') as file:
        lines = file.readlines()
        for i in range(len(lines)):
            print(f"Processing {i}/{len(lines)}")
            line = lines[i]
            text = line.split("['start']:")[0]
            start = float(line.split("['start']:")[1].split("['end']")[0])
            end = float(line.split("['end']:")[1])
            txt_file = f"{video_id}/{i}.txt"
            mp3_file = f"{video_id}/{i}.mp3"
            with open(txt_file, 'w') as txt:
                txt.write(text)
            audio = AudioSegment.from_file("audio.mp3")
            audio = audio[start * 1000: end * 1000]
            if(check_audio(audio)):
                audio.export(mp3_file, format="mp3")    
            else:
                print(f"Skipping {i} because of the audio quality") 
                if os.path.exists(mp3_file):
                    os.remove(mp3_file)
                if os.path.exists(txt_file):
                    os.remove(txt_file)

def merge(folder_name: str):
    merged_audio = AudioSegment.empty()
    dirlist = os.listdir(folder_name)
    dirlist.sort()
    for filename in dirlist:
        if filename.endswith(".mp3"):
            audio_file = os.path.join(folder_name, filename)
            text_file = os.path.join(folder_name, f"{os.path.splitext(filename)[0]}.txt")
            next_audio_file = os.path.join(folder_name, f"{int(os.path.splitext(filename)[0]) + 1}.mp3")
            next_text_file = os.path.join(folder_name, f"{int(os.path.splitext(filename)[0]) + 1}.txt")
            
            if os.path.exists(next_audio_file) and os.path.exists(next_text_file):
                print(f"Merging {audio_file} and {next_audio_file}")
                merged_audio = AudioSegment.from_file(audio_file)
                next_audio = AudioSegment.from_file(next_audio_file)
                merged_audio += next_audio
                
                text = None
                with open(text_file, 'r') as f:
                    text = f.read()
                with open(next_text_file, 'r') as f:
                    text = text + f.read()
                with open(next_text_file, 'w') as next_f:
                    next_f.write(text)
                
                os.remove(audio_file)
                os.remove(text_file)
                
                merged_audio.export(next_audio_file, format="mp3")
        
def generate_data(link: str):
    get_transcript(link)
    download_audio(link)
    scrape(link)
    merge(id(link))

link = "https://www.youtube.com/watch?v=D9MPeewRO_U"
generate_data(link)


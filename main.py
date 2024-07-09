import glob
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import urllib.parse as urllib
import os
from pydub import AudioSegment
import ffmpeg
from shutil import rmtree

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
    if os.path.exists("audio.wav"):
        os.remove("audio.wav")
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
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

def convert_audio(id: str):
    print(f"Converting audio files for {id}")
    folder_name = f"{id}"
    dirlist = os.listdir(folder_name)
    dirlist.sort()
    for filename in dirlist:
        if filename.endswith(".wav"):
            audio_file = os.path.join(folder_name, filename)
            temp_audio_file = os.path.join(folder_name, "temp.wav")
            (ffmpeg.input(audio_file, format='wav')
            .output(temp_audio_file, acodec='pcm_s16le', ac=1, ar=22050, loglevel='error')
            .overwrite_output()
            .run(capture_stdout=True))
            os.remove(audio_file)
            os.rename(temp_audio_file, audio_file)

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
            wav_file = f"{video_id}/{i}.wav"
            with open(txt_file, 'w') as txt:
                txt.write(text)
            audio = AudioSegment.from_file("audio.wav")
            audio = audio[start * 1000: end * 1000]
            if(check_audio(audio)):
                audio.export(wav_file, format="wav")    
            else:
                print(f"Skipping {i} because of the audio quality") 
                if os.path.exists(wav_file):
                    os.remove(wav_file)
                if os.path.exists(txt_file):
                    os.remove(txt_file)

def merge(folder_name: str):
    merged_audio = AudioSegment.empty()
    dirlist = os.listdir(folder_name)
    dirlist.sort()
    for filename in dirlist:
        if filename.endswith(".wav"):
            audio_file = os.path.join(folder_name, filename)
            text_file = os.path.join(folder_name, f"{os.path.splitext(filename)[0]}.txt")
            next_audio_file = os.path.join(folder_name, f"{int(os.path.splitext(filename)[0]) + 1}.wav")
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
                
                merged_audio.export(next_audio_file, format="wav")
        
def generate_data(link: str):
    get_transcript(link)
    download_audio(link)
    scrape(link)
    merge(id(link))
    convert_audio(id(link))

def create_db():
    if os.path.exists("LJSpeech"):
        rmtree("LJSpeech") # erase db for clean start
    os.makedirs("LJSpeech/wavs")
    with open("LJSpeech/metadata.csv", 'a') as file:
        pass

def append_to_db(id: str):
    folder_name = f"{id}"
    with open("LJSpeech/metadata.csv", 'a') as db_file:
        dirlist = os.listdir(folder_name)
        dirlist.sort()
        for filename in dirlist:
            if filename.endswith(".txt"):
                fileNameNoExtention = f"{id}-{os.path.splitext(filename)[0]}"
                with open(os.path.join(folder_name, filename), 'r') as f:
                    text = f.read()
                db_file.write(f"{fileNameNoExtention}|{text}\n")
            else:
                filenameId = f"{id}-{filename}"
                source_file = os.path.join(folder_name, filename)
                destination_dir = "LJSpeech/wavs"
                # Move the wav
                os.rename(source_file, os.path.join(destination_dir, filenameId))
    rmtree(folder_name)

def main():
    links = [
        "https://www.youtube.com/watch?v=lpX_TXhQUXQ",
    ]
    for link in links:
        rmtree(id(link), ignore_errors=True)
        generate_data(link)
    create_db()
    for link in links:
        append_to_db(id(link))

if __name__ == "__main__":
    main()
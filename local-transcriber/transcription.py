# -*- coding: utf-8 -*-
import whisper
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import DBSCAN
from pydub import AudioSegment
import numpy as np
import torch
import os

# GPUが利用可能なら設定 
device = "cuda" if torch.cuda.is_available() else "cpu"
whisper_model = whisper.load_model("large", device=device)
encoder = VoiceEncoder(device=device)

def convert_mp3_to_wav(mp3_path, wav_path):
    """
    pydubを使ってMP3ファイルをWAVに変換する
    """
    print("Starting MP3 to WAV conversion...")  # 追加：変換開始の進捗表示
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")
    print(f"Finished conversion: {mp3_path} -> {wav_path}")  # 変更：変換完了の表示

def transcribe_with_speaker_diarization(wav_path, output_path="transcript.txt"):
    # Whisperで文字起こし（結果はJSON形式）
    print("Running transcription with Whisper... (This may take some time)")
    result = whisper_model.transcribe(wav_path)
    segments = result.get("segments", [])
    print(f"Whisper finished. Detected {len(segments)} segments.")  # 追加：セグメント数表示

    # 音声全体をpreprocessしてwav配列（16kHz）として読み込み
    wav = preprocess_wav(wav_path)

    speaker_embeddings = []
    segment_timestamps = []
    
    print("Extracting speaker embeddings for each segment...")
    # 各セグメントごとにResemblyzerで特徴量抽出
    total_segments = len(segments)
    for i, segment in enumerate(segments):
        print(f"Processing segment {i+1}/{total_segments} (time {segment.get('start', 0):.2f} - {segment.get('end', 0):.2f} sec)...")
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        # 16kHzに合わせたサンプル数でスライス
        segment_wav = wav[int(start * 16000):int(end * 16000)]
        # Embeddingの取得
        embedding = encoder.embed_utterance(segment_wav)
        speaker_embeddings.append(embedding)
        segment_timestamps.append((start, end))
    
    # クラスタリング：DBSCANを利用して話者分離
    embeddings = np.array(speaker_embeddings)
    clustering = DBSCAN(eps=0.5, min_samples=2).fit(embeddings)
    labels = clustering.labels_
    
    # 話者区別付きの文字起こし結果をフォーマット
    output_lines = []
    for i, segment in enumerate(segments):
        start = segment.get("start", 0)
        text = segment.get("text", "").strip()
        label = labels[i] if labels[i] != -1 else "Unknown"
        # タイムスタンプを分:秒形式に変換
        minute = int(start // 60)
        second = int(start % 60)
        timestamp = f"{minute}:{second:02}"
        output_lines.append(f"@Speaker_{label} [{timestamp}]\n{text}\n")
    
    formatted_transcription = "\n".join(output_lines)
    with open(output_path, "w", encoding="utf8") as f:
        f.write(formatted_transcription)
    print(f"Transcription with speaker diarization saved to {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <path/to/audio.mp3>")
        sys.exit(1)
    
    mp3_file = sys.argv[1]
    if not os.path.exists(mp3_file):
        print(f"Error: {mp3_file} not found.")
        sys.exit(1)
    
    # 一時的なwavファイルのパス
    wav_file = "temp_audio.wav"
    convert_mp3_to_wav(mp3_file, wav_file)
    transcribe_with_speaker_diarization(wav_file)
    
    # 必要に応じて一時ファイルの削除
    # os.remove(wav_file)
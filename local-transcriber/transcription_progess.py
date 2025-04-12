# -*- coding: utf-8 -*-
import whisper
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import DBSCAN
# from pydub import AudioSegment # ffmpeg方式では不要
import numpy as np
import torch
import os
import subprocess # 追加
import re # 追加
import sys # 追加
import time # 追加

# GPUが利用可能なら設定
device = "cuda" if torch.cuda.is_available() else "cpu"
whisper_model = whisper.load_model("large", device=device)
encoder = VoiceEncoder(device=device)

def get_audio_duration(file_path):
    """ffprobeを使って音声ファイルの総再生時間を取得する"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        return float(result.stdout.strip())
    except FileNotFoundError:
        print("Error: ffprobe not found. Please install ffmpeg (which includes ffprobe).")
        raise
    except subprocess.CalledProcessError as e:
        print(f"Error getting duration using ffprobe: {e}")
        print(f"ffprobe stderr: {e.stderr}")
        return None
    except ValueError:
        print(f"Error parsing duration from ffprobe output: {result.stdout}")
        return None

def convert_mp3_to_wav_with_progress(mp3_path, wav_path):
    """
    ffmpegを使ってMP3ファイルをWAVに変換し、進捗を表示する (スロットリング付き)
    """
    try:
        total_duration = get_audio_duration(mp3_path)
    except FileNotFoundError:
         # get_audio_duration内で発生したFileNotFoundErrorを捕捉して再raise
         raise
    if total_duration is None:
        print("Could not get total duration, proceeding without progress percentage.")

    cmd = [
        "ffmpeg", "-i", mp3_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        wav_path, "-y", "-loglevel", "error",
        "-progress", "-", "-nostats"
    ]

    print(f"Converting {mp3_path} to {wav_path} using ffmpeg...")
    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')

    current_time_sec = 0.0
    last_update_time = time.time()
    update_interval = 0.2 # 更新間隔（秒）

    while True:
        line = process.stderr.readline()
        if not line and process.poll() is not None:
            break
        if not line:
            continue

        new_time_sec = current_time_sec # デフォルトは前の値
        match_time_ms = re.search(r"out_time_ms=(\d+)", line)
        if match_time_ms:
            new_time_sec = int(match_time_ms.group(1)) / 1_000_000.0
        else:
            match_time = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d+)", line)
            if match_time:
                hours, minutes, seconds, ms_part = map(int, match_time.groups())
                ms = ms_part / (10**(len(str(ms_part))))
                new_time_sec = hours * 3600 + minutes * 60 + seconds + ms

        # 値が更新された場合のみcurrent_time_secを更新
        if new_time_sec > current_time_sec:
             current_time_sec = new_time_sec

        # スロットリング: 一定時間が経過した場合のみ表示を更新
        current_render_time = time.time()
        if current_render_time - last_update_time > update_interval:
            if total_duration and total_duration > 0:
                progress = min(100.0, (current_time_sec / total_duration) * 100)
                print(f"\rConverting: {current_time_sec:.2f}s / {total_duration:.2f}s ({progress:.1f}%)  ", end="")
            else:
                print(f"\rConverting: {current_time_sec:.2f}s processed  ", end="")
            last_update_time = current_render_time

    # ループ終了後、最終的な進捗を表示
    if total_duration and total_duration > 0:
         final_progress = min(100.0, (current_time_sec / total_duration) * 100)
         # 最終時刻がtotal_durationを超える場合があるため、100%表示も保証
         if current_time_sec >= total_duration:
             final_progress = 100.0
         print(f"\rConverting: {total_duration:.2f}s / {total_duration:.2f}s (100.0%)  ", end="")
    else:
         print(f"\rConverting: {current_time_sec:.2f}s processed  ", end="")
    print() # 改行

    process.wait()
    stdout_output, stderr_output = process.communicate() # 残りの出力を取得

    if process.returncode == 0:
        print(f"Successfully converted {mp3_path} to {wav_path}")
    else:
        print(f"\nError during conversion. ffmpeg exited with code {process.returncode}")
        if stdout_output:
             print("--- ffmpeg stdout ---")
             print(stdout_output)
             print("---------------------\n")
        # stderrは進捗情報も混ざるので参考程度に表示
        # print("--- ffmpeg stderr (remaining) ---")
        # print(stderr_output)
        # print("-------------------------------\n")
        raise RuntimeError(f"ffmpeg conversion failed with code {process.returncode}")


def transcribe_with_speaker_diarization(wav_path, output_path="transcript.txt"):
    # Whisperで文字起こし（結果はJSON形式）
    print("Running transcription with Whisper... (This may take some time)")
    result = whisper_model.transcribe(wav_path)
    segments = result.get("segments", [])
    print(f"Whisper finished. Detected {len(segments)} segments.") # 追加：セグメント数表示

    # 音声全体をpreprocessしてwav配列（16kHz）として読み込み
    wav = preprocess_wav(wav_path)

    speaker_embeddings = []
    segment_timestamps = []

    print("Extracting speaker embeddings for each segment...")
    # 各セグメントごとにResemblyzerで特徴量抽出
    total_segments = len(segments)
    for i, segment in enumerate(segments):
        # セグメントごとの進捗表示
        progress_percent = ((i + 1) / total_segments) * 100 if total_segments > 0 else 0
        print(f"\rProcessing embedding: Segment {i+1}/{total_segments} ({progress_percent:.1f}%) ", end="")
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        # 16kHzに合わせたサンプル数でスライス
        segment_wav = wav[int(start * 16000):int(end * 16000)]
        # Embeddingの取得
        embedding = encoder.embed_utterance(segment_wav)
        speaker_embeddings.append(embedding)
        segment_timestamps.append((start, end))
    print() # 改行

    # クラスタリング：DBSCANを利用して話者分離
    print("Clustering speaker embeddings...")
    embeddings = np.array(speaker_embeddings)
    clustering = DBSCAN(eps=0.5, min_samples=2).fit(embeddings)
    labels = clustering.labels_
    num_speakers = len(set(label for label in labels if label != -1))
    print(f"Clustering finished. Found {num_speakers} distinct speakers.")

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
    # import sys # 既に上でimport済み
    if len(sys.argv) < 2:
        print("Usage: python transcription.py <path/to/audio.mp3>") # スクリプト名を修正
        sys.exit(1)

    mp3_file = sys.argv[1]
    if not os.path.exists(mp3_file):
        print(f"Error: {mp3_file} not found.")
        sys.exit(1)

    # 一時的なwavファイルのパス
    wav_file = "temp_audio.wav"
    output_file = "transcript.txt" # 出力ファイル名を変数に

    try:
        # ffmpegベースの変換関数を呼び出す
        convert_mp3_to_wav_with_progress(mp3_path=mp3_file, wav_path=wav_file)
        # 変換成功後、文字起こし実行
        transcribe_with_speaker_diarization(wav_path=wav_file, output_path=output_file)
    except FileNotFoundError:
        # get_audio_duration内などでffprobe/ffmpegが見つからない場合
        print("\nError: ffmpeg (and ffprobe) is required but not found.")
        print("Please install ffmpeg and ensure it's in your system's PATH.")
        sys.exit(1)
    except RuntimeError as e:
         # ffmpeg変換失敗など
         print(f"\nAn error occurred during processing: {e}")
         sys.exit(1)
    except Exception as e:
        # その他の予期せぬエラー
        print(f"\nAn unexpected error occurred: {e}")
        # 必要であればスタックトレースも表示
        # import traceback
        # traceback.print_exc()
        sys.exit(1)
    finally:
        # 処理が成功しても失敗しても一時ファイルを削除する
        if os.path.exists(wav_file):
            try:
                print(f"Removing temporary file: {wav_file}")
                os.remove(wav_file)
            except OSError as e:
                # ファイル削除失敗は致命的ではない場合もあるので警告に留める
                print(f"Warning: Could not remove temporary file {wav_file}: {e}")

    print("Processing complete.")
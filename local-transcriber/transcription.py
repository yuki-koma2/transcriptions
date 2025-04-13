# -*- coding: utf-8 -*-
import whisper
from resemblyzer import VoiceEncoder, preprocess_wav
from sklearn.cluster import DBSCAN
from pydub import AudioSegment
import numpy as np
import torch
import os
import json
import argparse
from openai import OpenAI
import sys
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込む
load_dotenv()

# GPUが利用可能なら設定
device = "cuda" if torch.cuda.is_available() else "cpu"
# ローカルモデルとエンコーダーは必要に応じて初期化
whisper_model = None
encoder = None
openai_client = None

def initialize_local_models(require_whisper=True, require_encoder=True):
    """ローカル処理に必要なモデルを初期化する"""
    global whisper_model, encoder
    if require_whisper and whisper_model is None:
        print("Initializing local Whisper model...")
        whisper_model = whisper.load_model("large", device=device)
    if require_encoder and encoder is None:
        print("Initializing local VoiceEncoder model...")
        encoder = VoiceEncoder(device=device)

def initialize_openai_client():
    """OpenAI APIクライアントを初期化する"""
    global openai_client
    if openai_client is None:
        print("Initializing OpenAI client...")
        try:
            openai_client = OpenAI()
            openai_client.models.list()
            print("OpenAI client initialized successfully.")
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            print("Please ensure the OPENAI_API_KEY environment variable is set correctly.")
            openai_client = None
            raise

def convert_mp3_to_wav(mp3_path, wav_path):
    """pydubを使ってMP3ファイルをWAVに変換する"""
    print("Starting MP3 to WAV conversion...")
    audio = AudioSegment.from_mp3(mp3_path)
    # Resemblyzerが必要とする16kHzモノラルに変換
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(wav_path, format="wav")
    print(f"Finished conversion: {mp3_path} -> {wav_path} (16kHz Mono)")


def diarize_with_resemblyzer(segments, wav_path):
    """
    与えられたセグメント情報とWAVファイルパスに基づき、Resemblyzerで話者分離を行う。
    話者ラベル付きのフォーマットされた文字列を返す。
    """
    initialize_local_models(require_whisper=False, require_encoder=True) # Encoderのみ必要

    print(f"Performing speaker diarization using Resemblyzer on {wav_path}...")
    try:
        wav = preprocess_wav(wav_path)
    except Exception as e:
        print(f"Error preprocessing WAV file {wav_path}: {e}")
        return "Error during audio preprocessing for diarization."

    speaker_embeddings = []
    valid_segments = [] # Embedding抽出に成功したセグメントのみを保持

    print("Extracting speaker embeddings for each segment...")
    total_segments = len(segments)
    for i, segment in enumerate(segments):
        # start, end, text を取得 (オブジェクトか辞書かで分岐)
        try:
            if isinstance(segment, dict):
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                text = segment.get('text', '').strip()
            else: # TranscriptionSegment オブジェクトと仮定
                start = segment.start
                end = segment.end
                text = segment.text.strip()
        except AttributeError:
            print(f"Warning: Segment {i+1}/{total_segments} has unexpected format. Skipping.")
            continue

        print(f"Processing segment {i+1}/{total_segments} (time {start:.2f} - {end:.2f} sec)...")
        segment_wav = wav[int(start * 16000):int(end * 16000)]

        if len(segment_wav) < 160: # 短すぎるセグメントはエンコーダーがエラーを出すことがある (0.01秒)
            print(f"Segment {i+1} is too short, skipping embedding extraction.")
            # このセグメントを結果に残すかどうかの判断が必要。ここでは残すがEmbeddingはNoneとするか？
            # または結果から除外するか。一旦除外する方針で実装。
            continue # embeddingに追加せず、valid_segmentsにも追加しない

        try:
            embedding = encoder.embed_utterance(segment_wav)
            speaker_embeddings.append(embedding)
            # 元のセグメント情報も保存しておく（クラスタリング結果と対応付けるため）
            valid_segments.append({'start': start, 'end': end, 'text': text, 'original_index': i})
        except Exception as e:
            print(f"Error extracting embedding for segment {i+1} (time {start:.2f}-{end:.2f}): {e}. Skipping segment.")
            # ここでもエラーが出たセグメントは除外

    if not speaker_embeddings:
        print("No valid speaker embeddings could be extracted. Skipping clustering.")
        # Embeddingが全くない場合は、話者ラベルなしでvalid_segmentsを出力するか、エラーメッセージを返す
        output_lines = []
        for seg_info in valid_segments: # valid_segmentsも空のはずだが念のため
             minute = int(seg_info['start'] // 60)
             second = int(seg_info['start'] % 60)
             timestamp = f"{minute}:{second:02}"
             output_lines.append(f"@Unknown [{timestamp}]\\n{seg_info['text']}\\n")
        return "\\n".join(output_lines) if output_lines else "No segments to transcribe after embedding errors."


    # クラスタリング
    embeddings = np.array(speaker_embeddings)
    clustering = DBSCAN(eps=0.5, min_samples=1).fit(embeddings) # min_samples=1に変更し、ノイズ点をなくす
    labels = clustering.labels_

    # 結果のフォーマット
    output_lines = []
    # labels と valid_segments のインデックスが対応しているはず
    for i, seg_info in enumerate(valid_segments):
        label = labels[i] # DBSCANのラベル (0, 1, 2, ...)
        minute = int(seg_info['start'] // 60)
        second = int(seg_info['start'] % 60)
        timestamp = f"{minute}:{second:02}"
        output_lines.append(f"@Speaker_{label} [{timestamp}]\n{seg_info['text']}\n")

    return "\n".join(output_lines)


def transcribe_with_openai(mp3_path):
    """
    OpenAI APIを使用して文字起こしを実行し、セグメント情報のリストを返す。
    形式: [{'start': float, 'end': float, 'text': str}, ...]
    """
    global openai_client
    if openai_client is None:
         initialize_openai_client()
         if openai_client is None:
             print("Cannot proceed with OpenAI transcription due to client initialization error.")
             return None # エラーを示すためにNoneを返す

    print(f"Running transcription with OpenAI API for {mp3_path}...")
    try:
        with open(mp3_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )

        
        out_dir = "out"
        os.makedirs(out_dir, exist_ok=True) 
        base_name = os.path.splitext(os.path.basename(mp3_path))[0]
        openai_raw_output_path = os.path.join(out_dir, base_name + "_openai_raw.json")
    
        print(f"Saving raw OpenAI API response to {openai_raw_output_path}...")
        try:
            if hasattr(transcription, 'model_dump_json'):
                json_output = transcription.model_dump_json(indent=4)
                with open(openai_raw_output_path, "w", encoding="utf8") as json_f:
                    json_f.write(json_output)
            elif isinstance(transcription, dict): # 古いバージョン等で辞書の場合
                with open(openai_raw_output_path, "w", encoding="utf8") as json_f:
                    json.dump(transcription, json_f, ensure_ascii=False, indent=4)
            else: # その他の場合は単純に文字列として保存試行
                with open(openai_raw_output_path, "w", encoding="utf8") as json_f:
                    json_f.write(str(transcription))
            print(f"Successfully saved raw OpenAI response.")
        except Exception as e:
            print(f"Error saving raw OpenAI response to JSON: {e}")

        # 結果をセグメント辞書のリストに変換
        segments_list = []
        if hasattr(transcription, 'segments') and transcription.segments:
            for segment in transcription.segments:
                 segments_list.append({
                     'start': segment.start,
                     'end': segment.end,
                     'text': segment.text.strip()
                 })
            print(f"OpenAI transcription successful. Found {len(segments_list)} segments.")
            return segments_list
        else:
            print("Warning: No segments found in OpenAI API response.")
            return [] # 空のリストを返す

    except Exception as e:
        print(f"An error occurred during OpenAI transcription: {e}")
        return None # エラーを示すためにNoneを返す


def transcribe_with_local_whisper(wav_path):
    """
    ローカルのWhisperモデルで文字起こしを実行し、セグメント情報のリストを返す。
    形式: [{'start': float, 'end': float, 'text': str}, ...]
    """
    initialize_local_models(require_whisper=True, require_encoder=False) # Whisperのみ必要
    print(f"Running local transcription with Whisper on {wav_path}... (This may take some time)")
    try:
        result = whisper_model.transcribe(wav_path)
        segments = result.get("segments", [])
        # Whisperの辞書形式のままで良い（diarize_with_resemblyzerが対応）
        print(f"Local Whisper finished. Detected {len(segments)} segments.")
        return segments
    except Exception as e:
        print(f"An error occurred during local Whisper transcription: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio file using local Whisper or OpenAI API, with local speaker diarization.")
    parser.add_argument("audio_file", help="Path to the audio file (MP3 format)")
    parser.add_argument("--use-openai", action="store_true", help="Use OpenAI API for transcription, then local diarization.")
    parser.add_argument("-o", "--output", default=None, help="Path to save the transcription output file. Defaults to './out/[audio_filename]_diarized.txt'.")
    args = parser.parse_args()

    mp3_file = args.audio_file
    if not os.path.exists(mp3_file):
        print(f"Error: {mp3_file} not found.")
        sys.exit(1)

    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)

    # 出力ファイル名を決定
    if args.output:
        output_file = args.output
        # 指定されたパスのディレクトリ部分を取得
        output_dir_for_file = os.path.dirname(output_file)
        if output_dir_for_file:
            # ディレクトリ指定がある場合は、そのディレクトリを作成
            os.makedirs(output_dir_for_file, exist_ok=True)
        else:
            # ファイル名のみ指定の場合は、デフォルトの ./out ディレクトリに保存
            output_file = os.path.join(out_dir, args.output)
    else:
        # デフォルトのファイル名を ./out ディレクトリ内に生成
        base_name = os.path.splitext(os.path.basename(mp3_file))[0]
        if args.use_openai:
            suffix = "_transcript_openai_diarized.txt"
        else:
            suffix = "_transcript_local_diarized.txt"
        output_file = os.path.join(out_dir, base_name + suffix) # ★修正

    # 一時的なWAVファイルパス（これはカレントディレクトリで良い場合が多い）
    wav_file = "temp_audio_for_diarization.wav"
    segments = None
    formatted_transcription = None

    try:
        # 1. MP3をWAVに変換 (どちらのモードでもDiarizationに必要)
        convert_mp3_to_wav(mp3_file, wav_file)

        # 2. 文字起こし (Whisper: OpenAI or Local)
        if args.use_openai:
            print("Mode: OpenAI Whisper Transcription + Local Diarization")
            segments = transcribe_with_openai(mp3_file) # MP3を渡す
        else:
            print("Mode: Local Whisper Transcription + Local Diarization")
            segments = transcribe_with_local_whisper(wav_file) # WAVを渡す

        # 3. 話者分離 (Local Resemblyzer)
        if segments is not None and segments: # セグメントが正常に取得できた場合のみ実行
            formatted_transcription = diarize_with_resemblyzer(segments, wav_file)
        elif segments is None:
             print("Transcription failed. Skipping diarization.")
             formatted_transcription = "Transcription step failed."
        else: # segments == []
             print("No segments found by Whisper. Skipping diarization.")
             formatted_transcription = "No speech detected or no segments returned by Whisper."


        # 4. 結果をファイルに書き込み
        if formatted_transcription:
            with open(output_file, "w", encoding="utf8") as f:
                f.write(formatted_transcription)
            print(f"Transcription with speaker diarization saved to {output_file}")
        else:
             print("Failed to generate transcription.")


    except Exception as e:
        print(f"An overall error occurred: {e}")
        # エラー発生時もファイルにメッセージを残す場合
        try:
             with open(output_file, "w", encoding="utf8") as f:
                 f.write(f"An error occurred during processing: {e}")
        except Exception as write_error:
             print(f"Additionally, failed to write error message to output file: {write_error}")

    finally:
        # 一時ファイルの削除
        if os.path.exists(wav_file):
             print(f"Removing temporary file: {wav_file}")
             try:
                  os.remove(wav_file)
             except OSError as e:
                  print(f"Error removing temporary file {wav_file}: {e}")
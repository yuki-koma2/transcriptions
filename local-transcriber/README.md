# local-transcriber

このリポジトリには、音声ファイルを処理するためのスクリプトが含まれています。

1.  **Node.js スクリプト (`transcribe.js`)**: OpenAI Whisper API を直接呼び出して文字起こしを行います（話者分離なし）。
2.  **Python スクリプト (`transcription.py`)**: ローカルまたは OpenAI API を利用して文字起こしを行い、ローカルで話者分離を実行します。

---

## Node.js Transcription Script (transcribe.js)

OpenAI Whisper API を直接利用して文字起こしのみを行うシンプルな CLI ツールです。

### 使い方

1.  **リポジトリをクローンまたはダウンロードします。**

2.  **依存関係をインストールします。**
    ```bash
    npm install
    ```

3.  **`.env` ファイルを作成します。**
    プロジェクトのルートディレクトリ（`local-transcriber`）に `.env` という名前のファイルを作成し、以下の内容を記述します。
    ```
    OPENAI_API_KEY=YOUR_OPENAI_API_KEY
    ```
    `YOUR_OPENAI_API_KEY` を実際の OpenAI API キーに置き換えてください。

4.  **文字起こしを実行します。**
    ```bash
    node transcribe.js <音声ファイルのパス>
    ```
    例:
    ```bash
    node transcribe.js ./data/sample.mp3
    ```

### 技術スタック

*   Node.js (v18+)
*   axios
*   form-data
*   dotenv

### 入出力

*   **入力:**
    *   コマンドライン引数: 文字起こししたい音声ファイル (.mp3, .wav, .m4a 等、OpenAI API がサポートする形式) のパス
    *   `.env` ファイル: OpenAI API キー (`OPENAI_API_KEY`)
*   **出力:**
    *   成功時:
        *   入力音声ファイルと同じディレクトリに、拡張子を `.txt` に変更したファイル名で文字起こし結果を保存します (例: `input.mp3` -> `input.txt`)。
        *   標準出力に保存先のファイルパスを表示します。
    *   エラー時: 標準エラー出力にエラーメッセージを表示し、終了コード `1` でプロセス終了

### 処理フロー

1.  `.env` ファイルから環境変数 (特に `OPENAI_API_KEY`) を読み込みます。
2.  `OPENAI_API_KEY` が設定されているか確認します。未設定の場合はエラーメッセージを表示し終了します。
3.  コマンドライン引数で指定された音声ファイルが存在するか確認します。存在しない場合はエラーメッセージを表示し終了します。
4.  `FormData` オブジェクトを作成し、音声ファイルとモデル名 (`whisper-1`) を追加します。
    *   必要に応じて、コード内のコメントアウトを解除し、言語指定 (`language`) などのパラメータを追加できます。
5.  `axios` を使用して OpenAI Whisper API (`https://api.openai.com/v1/audio/transcriptions`) に POST リクエストを送信します。
    *   リクエストヘッダーには `Authorization: Bearer <OPENAI_API_KEY>` と `Content-Type: multipart/form-data` が含まれます。
    *   タイムアウトは 60 秒に設定されています。
6.  API レスポンスを処理します。
    *   成功時 (HTTP ステータス 2xx):
        1.  レスポンスボディの `text` フィールドの内容を取得します。
        2.  入力ファイル名から拡張子を除去し、`.txt` を付加した出力ファイルパスを生成します。
        3.  生成されたパスに文字起こし結果を UTF-8 で書き込みます。
        4.  書き込みに成功した場合、標準出力に保存先ファイルパスを表示します。
        5.  書き込みに失敗した場合、エラーメッセージを標準エラー出力に表示し、終了コード `1` でプロセスを終了します。
    *   失敗時: エラーの種類に応じて詳細な情報を標準エラー出力に表示し、終了コード `1` でプロセスを終了します。
7.  予期せぬエラーが発生した場合も、エラーメッセージを標準エラー出力に表示し、終了コード `1` でプロセスを終了します。

### エラーハンドリング

以下のエラーケースをハンドリングし、適切なメッセージを出力して終了コード `1` で終了します。

*   **環境変数 `OPENAI_API_KEY` が未設定:** `.env` ファイルを確認するよう促すメッセージを表示します。
*   **指定された音声ファイルが存在しない:** ファイルパスを確認するよう促すメッセージを表示します。
*   **OpenAI API 呼び出しエラー:**
    *   サーバーからのエラーレスポンス (HTTP ステータス 4xx, 5xx など): ステータスコード、レスポンスボディ、ヘッダー情報を表示します。
    *   リクエスト送信エラー (ネットワーク問題など): リクエストに関する情報を表示します。
    *   リクエスト設定時のエラー: エラーメッセージを表示します。
*   **ファイル書き込みエラー:** 文字起こし結果のテキストファイル書き込み中にエラーが発生した場合、エラーメッセージを表示します。
*   **その他の予期せぬエラー:** スクリプト実行中に発生した予期せぬエラーメッセージを表示します。

---

## Python Transcription & Diarization Script (transcription.py)

ローカル環境または OpenAI API を利用して音声ファイルの文字起こしを行い、さらにローカルで話者分離を行う高機能な CLI ツールです。

### 機能

*   **文字起こしエンジン選択:**
    *   **ローカルモード (デフォルト):** ローカルにインストールされた OpenAI Whisper (large モデル) を使用。
    *   **OpenAI モード (`--use-openai`):** OpenAI API (`whisper-1` モデル) を使用。
*   **話者分離:** どちらのモードでも、文字起こし結果の時間情報に基づき、ローカルの Resemblyzer と DBSCAN を使用して話者を分離。
*   **自動ファイル変換:** 入力された MP3 ファイルを、処理に必要な 16kHz モノラルの WAV ファイルに自動変換。
*   **柔軟な出力:**
    *   デフォルトで `./out` ディレクトリに出力（自動作成）。
    *   `-o` オプションで出力ファイルパスを指定可能。
    *   OpenAI モード時には、APIからの生の JSON レスポンスも保存。
*   **出力形式:** `@Speaker_N [MM:SS]
文字起こしテキスト` (話者ラベル + タイムスタンプ + テキスト)。

### セットアップ (Python)

1.  **Python 環境:** Python 3.8 以降がインストールされていることを確認してください。
2.  **ffmpeg:** Whisper は `ffmpeg` がシステムにインストールされている必要があります。お使いの OS に合わせてインストールしてください。
    *   macOS (Homebrew): `brew install ffmpeg`
    *   Debian/Ubuntu: `sudo apt update && sudo apt install ffmpeg`
3.  **PyTorch:** ご利用の環境（CPU/GPU）に合わせて PyTorch をインストールします。詳細は [PyTorch 公式サイト](https://pytorch.org/) を参照してください。
    *   例 (CPU): `pip install torch torchvision torchaudio`
    *   例 (NVIDIA GPU): `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118` (CUDA バージョンに合わせて調整してください)
4.  **依存ライブラリ:** `requirements.txt` を使用して他の依存ライブラリをインストールします。
    ```bash
    pip install -r local-transcriber/requirements.txt
    ```
    *   注意: このコマンドで `openai`, `python-dotenv`, `openai-whisper`, `resemblyzer`, `scikit-learn`, `pydub`, `numpy` などがインストールされます。
5.  **`.env` ファイル (OpenAI モード利用時):**
    OpenAI モード (`--use-openai`) を使用する場合は、`local-transcriber` ディレクトリに `.env` ファイルを作成し、API キーを設定してください。
    ```dotenv
    OPENAI_API_KEY=YOUR_OPENAI_API_KEY
    ```

### 実行方法 (Python)

基本的なコマンド:

```bash
python local-transcriber/transcription.py <音声ファイルのパス> [オプション]
```

**実行モード:**

*   **ローカルモード (デフォルト):**
    ```bash
    # 例: sample.mp3 をローカルで処理し、./out/sample_transcript_local_diarized.txt に出力
    python local-transcriber/transcription.py ./data/sample.mp3
    ```
*   **OpenAI モード:**
    ```bash
    # 例: sample.mp3 を OpenAI API で文字起こし + ローカルで話者分離し、
    # ./out/sample_transcript_openai_diarized.txt と ./out/sample_openai_raw.json に出力
    python local-transcriber/transcription.py ./data/sample.mp3 --use-openai
    ```

**出力先指定:**

*   `-o` または `--output` オプションで出力ファイルパスを指定できます。
    ```bash
    # 例: OpenAI モードで処理し、結果を ./results/my_output.txt に保存
    python local-transcriber/transcription.py ./data/sample.mp3 --use-openai -o ./results/my_output.txt

    # 例: ローカルモードで処理し、結果を ./out/specific_name.txt に保存
    python local-transcriber/transcription.py ./data/sample.mp3 -o specific_name.txt
    ```
    *   `-o` でディレクトリパスを含まないファイル名のみを指定した場合、デフォルトの `./out` ディレクトリ内に保存されます。

### 入出力 (Python)

*   **入力:**
    *   コマンドライン引数: 処理する音声ファイル (MP3推奨) のパス。
    *   オプション: `--use-openai`, `-o <出力パス>`。
    *   `.env` ファイル (OpenAIモード時): `OPENAI_API_KEY`。
*   **出力:**
    *   **話者分離済みテキストファイル:**
        *   デフォルトパス: `./out/<入力ファイル名>_transcript_[local|openai]_diarized.txt`
        *   指定パス: `-o` オプションで指定されたパス。
        *   形式: `@Speaker_N [MM:SS]
テキスト`
    *   **OpenAI API 生レスポンス (OpenAIモード時のみ):**
        *   パス: `./out/<入力ファイル名>_openai_raw.json`
        *   形式: OpenAI API から返却された JSON データ。
    *   **コンソール出力:** 処理の進捗状況。
    *   **エラー時:** エラーメッセージをコンソールに出力。
*   **一時ファイル:** 処理中に `temp_audio_for_diarization.wav` が一時的に作成され、処理後に自動削除されます。

### 注意事項

*   **初回実行:** ローカルの Whisper モデル (large) や Resemblyzer モデルのダウンロードに時間がかかる場合があります。
*   **リソース:** ローカルモードでは、特に large モデルを使用するため、相応の CPU/メモリ、または GPU リソースが必要です。
*   **APIキー:** OpenAI モードを使用するには、有効な OpenAI API キーと、場合によっては支払い情報の設定が必要です。
*   **話者分離精度:** 話者分離の精度は、入力音声の品質、話者の声質、発話の重なり具合などによって変動します。常に完璧な結果が得られるとは限りません。
*   **長時間ファイル:** 非常に長い音声ファイルの場合、メモリ使用量が増加したり、処理に時間がかかる可能性があります。

---

## やってみてメモ

ローカルでの変換だとやはり時間がかかるプロセスというか進捗が見えるといいんだけど。
あとこのモデルどこにインストールされているんだろう。結構重い。

`~/.cache/whisper` ここだ。

## やってること (Python スクリプト)

	1.	全体文字起こし
	•	whisper_model.transcribe(wav_path) により、音声ファイル全体を一括で処理して文字起こしします。これにより、各発話の開始時刻・終了時刻、テキストなどが含まれる複数の「セグメント」が得られます。
	2.	セグメントごとの音声抽出と埋め込み計算
	•	得られた各セグメント（例：0:00～0:10、0:11～0:20など）の時間情報をもとに、preprocess_wav(wav_path) で変換済みの全体音声から、そのセグメントに対応する部分だけを抽出します。
	•	その抽出した音声に対して、Resemblyzer を使って「話者の特徴」を表すベクトル（埋め込み）を取得します。
	3.	クラスタリングによる話者識別
	•	得られた複数のセグメントの埋め込みに対して、DBSCAN というクラスタリング手法を使い、似た特徴を持つセグメント同士をグループ化します。
	•	このクラスタリング結果から、同じ話者と思われるセグメントに同じラベル（例：Speaker_0, Speaker_1 等）を割り当て、話者区別を実現しています。
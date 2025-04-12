# local-transcriber

ローカル環境で音声ファイルを指定して OpenAI Whisper API で文字起こしを行う CLI ツールです。

## 使い方

1.  **リポジトリをクローンまたはダウンロードします。**

2.  **依存関係をインストールします。**
    ```bash
    npm install
    ```

3.  **`.env` ファイルを作成します。**
    プロジェクトのルートディレクトリに `.env` という名前のファイルを作成し、以下の内容を記述します。
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
    node transcribe.js ./sample.mp3
    ```

## 技術スタック

*   Node.js (v18+)
*   axios
*   form-data
*   dotenv

## 入出力

*   **入力:**
    *   コマンドライン引数: 文字起こししたい音声ファイル (.mp3, .wav, .m4a 等、OpenAI API がサポートする形式) のパス
    *   `.env` ファイル: OpenAI API キー (`OPENAI_API_KEY`)
*   **出力:**
    *   成功時:
        *   入力音声ファイルと同じディレクトリに、拡張子を `.txt` に変更したファイル名で文字起こし結果を保存します (例: `input.mp3` -> `input.txt`)。
        *   標準出力に保存先のファイルパスを表示します。
    *   エラー時: 標準エラー出力にエラーメッセージ（APIキー未設定、ファイル不在、APIエラー詳細、ファイル書き込みエラーなど）と終了コード `1` でプロセス終了

## 処理フロー

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

## エラーハンドリング

以下のエラーケースをハンドリングし、適切なメッセージを出力して終了コード `1` で終了します。

*   **環境変数 `OPENAI_API_KEY` が未設定:** `.env` ファイルを確認するよう促すメッセージを表示します。
*   **指定された音声ファイルが存在しない:** ファイルパスを確認するよう促すメッセージを表示します。
*   **OpenAI API 呼び出しエラー:**
    *   サーバーからのエラーレスポンス (HTTP ステータス 4xx, 5xx など): ステータスコード、レスポンスボディ、ヘッダー情報を表示します。
    *   リクエスト送信エラー (ネットワーク問題など): リクエストに関する情報を表示します。
    *   リクエスト設定時のエラー: エラーメッセージを表示します。
*   **ファイル書き込みエラー:** 文字起こし結果のテキストファイル書き込み中にエラーが発生した場合、エラーメッセージを表示します。
*   **その他の予期せぬエラー:** スクリプト実行中に発生した予期せぬエラーメッセージを表示します。

## Python Transcription Script (local-transcriber/transcription.py)

このリポジトリには、Node.js 版とは別に、Python を使用したローカルでの文字起こしと話者分離を行うスクリプトも含まれています。

### 機能

*   OpenAI Whisper (large モデル) を使用した高精度な文字起こし
*   Resemblyzer と DBSCAN を使用した話者分離
*   MP3 ファイルを自動的に WAV に変換
*   出力形式: `@Speaker_N [MM:SS]
文字起こしテキスト`

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

### 実行方法 (Python)

```bash
python local-transcriber/transcription.py <音声ファイルのパス>
```

例:

```bash
python local-transcriber/transcription.py ./sample.mp3
```

*   **入力:** コマンドライン引数で指定された音声ファイル (MP3 推奨、スクリプト内で WAV に変換されます)。
*   **出力:**
    *   `transcript.txt` という名前で、スクリプトを実行したディレクトリに話者分離付きの文字起こし結果が保存されます。
    *   処理の進捗状況がコンソールに出力されます。
*   **一時ファイル:** 処理中に `temp_audio.wav` という一時ファイルが作成されます。スクリプトの最終行にあるコメントアウト (`# os.remove(wav_file)`) を解除すると、処理後に自動で削除されます。

### 注意事項

*   初回実行時、Whisper モデル (large) のダウンロードに時間がかかる場合があります。
*   GPU を利用する場合、適切な CUDA Toolkit と cuDNN がインストールされている必要があります。
*   話者分離の精度は、音声の品質や話者の声質によって変動する可能性があります。
*   非常に長い音声ファイルの場合、メモリ使用量が増加する可能性があります。


## やってみてメモ
ローカルでの変換だとやはり時間がかかるプロセスというか進捗が見えるといいんだけど。
あとこのモデルどこにインストールされているんだろう。結構重い。

`~/.cache/whisper` ここだ。
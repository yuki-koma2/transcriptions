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
    *   コマンドライン引数: 文字起こししたい音声ファイル (.mp3, .wav, .m4a 等) のパス
    *   `.env` ファイル: OpenAI API キー (`OPENAI_API_KEY`)
*   **出力:**
    *   成功時: 標準出力に文字起こし結果のテキスト
    *   エラー時: 標準エラー出力にエラーメッセージ

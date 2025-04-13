import axios from 'axios';
import fs from 'fs';
import FormData from 'form-data';
import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env file
dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const API_URL = 'https://api.openai.com/v1/audio/transcriptions';

async function transcribeAudio(filePath, withSummary = false) {
  if (!OPENAI_API_KEY) {
    console.error('Error: OPENAI_API_KEY is not set in the .env file.');
    process.exit(1);
  }

  if (!fs.existsSync(filePath)) {
    console.error(`Error: File not found at ${filePath}`);
    process.exit(1);
  }

  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));
  form.append('model', 'whisper-1');
  // form.append('model', 'gpt-4o-transcribe');
  // Add other parameters like language if needed
  // form.append('language', 'ja'); // Specify language for potentially better accuracy

  try {
    const response = await axios.post(API_URL, form, {
      headers: {
        ...form.getHeaders(),
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
      },
      // Optional: Add timeout if needed
      timeout: 1200000, // 20 minutes timeout
    });

    //　
    console.log(response.data);
    // Output the transcription text
    const outputText = response.data.text;
    // 入力ファイルパスから拡張子を除いたベース名を取得
    const inputFileBasename = path.basename(filePath, path.extname(filePath));
    // 出力ファイルパスを生成 (例: audio.mp3 -> audio.txt)
    const outputFilePath = path.join(path.dirname(filePath), `${inputFileBasename}.txt`);

    try {
      fs.writeFileSync(outputFilePath, outputText, 'utf8');
      console.log(`Transcription saved to: ${outputFilePath}`); // 成功メッセージ
    } catch (writeError) {
      console.error(`Error writing transcription to file ${outputFilePath}:`, writeError.message);
      process.exit(1);
    }

    if (withSummary) {
      console.log('Generating summary using GPT-4o...');
      try {
        const summaryResponse = await axios.post(
          'https://api.openai.com/v1/chat/completions',
          {
            model: 'gpt-4o',
            messages: [
              { role: 'system', content: 'You are a helpful assistant that summarizes transcribed meeting conversations. Please summarize the conversation in a concise manner, focusing on the main points and decisions made. in Japanese' },
              { role: 'user', content: outputText }
            ],
            temperature: 0.3,
          },
          {
            headers: {
              'Authorization': `Bearer ${OPENAI_API_KEY}`,
              'Content-Type': 'application/json',
            }
          }
        );

        const summaryText = summaryResponse.data.choices?.[0]?.message?.content || 'No summary returned.';
        const summaryFilePath = path.join(path.dirname(filePath), `${inputFileBasename}.summary.txt`);
        fs.writeFileSync(summaryFilePath, summaryText, 'utf8');
        console.log(`Summary saved to: ${summaryFilePath}`);
      } catch (summaryError) {
        console.error('Error generating summary:', summaryError.message);
        process.exit(1);
      }
    }

  } catch (error) {
    console.error('Error calling OpenAI API:');
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error(`  Status: ${error.response.status}`);
      console.error('  Data:', error.response.data);
      console.error('  Headers:', error.response.headers);
    } else if (error.request) {
      // The request was made but no response was received
      console.error('  No response received:', error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('  Error message:', error.message);
    }
    process.exit(1);
  }
}

// Get file path from command line arguments
const args = process.argv.slice(2); // Skip node executable and script file path
if (args.length === 0) {
  console.error('Usage: node transcribe.js <path/to/audio/file>');
  process.exit(1);
}

const audioFilePath = args[0];

// --summary オプションを含んでいたら要約も行う
const withSummary = args.includes('--summary');

// Wrap the main execution in an async IIFE to catch top-level errors
(async () => {
  try {
    await transcribeAudio(audioFilePath, withSummary);
  } catch (error) {
    // Catch any unexpected errors not handled within transcribeAudio
    console.error('An unexpected error occurred:', error.message);
    process.exit(1);
  }
})();

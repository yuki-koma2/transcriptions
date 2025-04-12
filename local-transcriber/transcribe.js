import axios from 'axios';
import fs from 'fs';
import FormData from 'form-data';
import dotenv from 'dotenv';

// Load environment variables from .env file
dotenv.config();

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const API_URL = 'https://api.openai.com/v1/audio/transcriptions';

async function transcribeAudio(filePath) {
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
  // Add other parameters like language if needed

  try {
    const response = await axios.post(API_URL, form, {
      headers: {
        ...form.getHeaders(),
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
      },
      // Optional: Add timeout if needed
      // timeout: 60000, // e.g., 60 seconds
    });

    // Output the transcription text
    console.log(response.data.text);

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
transcribeAudio(audioFilePath);

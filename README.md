# Audiobook Chapter Splitter

A powerful Python script to automatically split audiobooks into chapters using Whisper transcription, embedded metadata, or SRT files.

## Key Features

* **Multi-Source Chapter Detection**: Intelligently uses embedded metadata, existing caches, or high-accuracy transcription to find chapters.

* **Versatile & Smart**: Recognizes chapter numbers in Arabic, word, and Roman formats, and can optionally extract titles while handling complex punctuation.

* **Fully Automated**: Features smart caching, recursive directory scanning, cover art preservation, and automatic archiving of processed files.

* **Highly Configurable**: All settings are managed in a simple `config.json` file.

* **Cross-Platform & Multi-language**: Works on Windows, macOS, and Linux, with UI messages in English and Chinese.

## Installation

**1. Install FFmpeg:** This is a mandatory prerequisite.

* **Windows:**

  * **Option 1 (Recommended):** Download the `.zip` package from the [Releases](https://github.com/your-username/your-repository/releases) page. Unzip it and the program is ready to use.

  * **Option 2 (Manual Setup):** First, install FFmpeg by downloading it from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and placing `ffmpeg.exe` & `ffprobe.exe` in the script's root directory. Then, proceed to Step 2 below to install Python libraries.

* **macOS:** `brew install ffmpeg`

* **Linux:** `sudo apt-get install ffmpeg` or `sudo dnf install ffmpeg`

**2. Install Python Libraries (For Manual Setup Only):**
If you are not using the pre-packaged release, you need to install the Python dependencies.

```bash
pip install faster-whisper pydub ffmpeg-python word2number huggingface-hub
```

**3. Download Language Moudle from [huggingface](https://huggingface.co/Systran/faster-whisper-tiny.en/tree/main). Put config.json, model.bin, tokenizer.json, vocabulary.txt into the folder local_models\tiny.en

## Quick Start

1. **Prepare Folders**: Create an `Input` folder and place your audiobooks inside. Your project structure should look like this:

   ```
   /Audiobook-Chapter-Splitter/
   ├── Input/
   │   └── My-Audiobook/
   │       └── book.m4a
   ├── Lang/
   │   ├── en.json
   │   └── zh.json
   ├── local_models/
   │   └── tiny.en/
   │        └── config.json
   │        └── model.bin
   │        └── tokenizer.json
   │        └── vocabulary.txt
   ├── config.json
   ├── run.py
   └── ffmpeg.exe  (For Windows)
   └── ffprobe.exe (For Windows)
   ```

2. **Configure (Optional)**: On the first run, a `config.json` file is created. You can edit it to change settings like the model size or language.

3. **Run**: Open a terminal in the project folder and execute:
   ```bash
   python run.py
   ```
   The script will automatically find and process all audio files within the `Input` directory and its subfolders.

## Configuration

All settings are controlled via the `config.json` file. Key options you might want to change include:

* `"selected_model_key"`: To use a more accurate but slower model (e.g., `"base.en"` or `"medium.en"`).
* `"device"`: Change to `"cuda"` if you have a compatible NVIDIA GPU.
* `"language"`: Change to `"zh"` for Chinese UI messages.
* `"extract_chapter_title"`: Set to `true` to include titles in the output filenames.

---

## Special Thanks

Special thanks to **Wang Hua(王婳)** for algorithm suggestions and code sharing for this project.

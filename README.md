# Audiobook Chapter Splitter

A powerful Python script to automatically transcribe, detect chapters, and split large audio files into chapter-based segments. Ideal for processing audiobooks, lectures, or long podcasts.

This tool leverages `faster-whisper` for high-accuracy transcription and intelligently parses the generated text to find chapter markers, creating a streamlined workflow from a single audio file to a neatly organized collection of chapter files.

## Features

* **High-Accuracy Transcription**: Utilizes `faster-whisper` for precise, word-level timestamped transcription.

* **Intelligent Chapter Detection**:

  * **Multi-Source Priority**: Prefers **embedded chapters** first, then `.json` or `.srt` caches, and finally performs transcription, ensuring maximum efficiency.

  * **Versatile Format Support**: Recognizes chapter numbers in various formats: Arabic (`Chapter 1`), word (`Chapter One`), and Roman (`Chapter III`).

  * **Smart Title Extraction**: An optional feature to accurately extract chapter titles, intelligently handling cases like "Mr." and "J. R. R. Tolkien".

* **Smart Caching**: Automatically creates `.srt` (subtitle) and `.json` (chapter) cache files. On subsequent runs, the script uses these caches to **skip** the time-consuming transcription step.

* **Cover Art Preservation**: Automatically extracts the cover art from the source audio file and embeds it into all split chapter files.

* **Flexible Configuration**: All settings are managed in an external `config.json` file, requiring no code changes for adjustments.

* **Automatic Archiving**: After processing, moves the source file and its caches to a `Done` directory, keeping the `input` folder clean.

## Installation Guide

Before running the script, your system needs **FFmpeg**.

#### Windows

1. Download the latest FFmpeg build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).

2. Extract the downloaded `.zip` file.

3. From the `bin` folder, copy `ffmpeg.exe` and `ffprobe.exe` into the **same directory** as the `run.py` script. This is the simplest method.

#### macOS

The easiest way is using [Homebrew](https://brew.sh/):

```bash
brew install ffmpeg
```

#### Linux

Use your distribution's package manager.

* **Debian/Ubuntu/Mint:**

  ```bash
  sudo apt-get update && sudo apt-get install ffmpeg
  ```

* **Fedora/CentOS/RHEL:**

  ```bash
  sudo dnf install ffmpeg
  ```

#### Python Dependencies

After installing FFmpeg, install the required Python packages. Using a virtual environment is recommended.

```bash
pip install faster-whisper pydub ffmpeg-python word2number huggingface-hub
```

## How to Use

1. **Prepare Project Folder**:
   Ensure your project folder is structured as follows. The script will create `output`, `Done`, and `local_models` on its first run.

   ```
   /Audiobook-Chapter-Splitter/  <-- Project Root
   ├── lang/
   │   ├── en.json
   │   └── zh.json
   ├── input/
   │   └── my_audiobook.m4a
   ├── config.json
   ├── run.py
   ├── ffmpeg.exe            (Windows only)
   └── ffprobe.exe           (Windows only)
   ```

2. **Configure `config.json`**:
   The script will create a default `config.json` file on its first run if one is not found. You can modify its parameters as needed (see below).

3. **Run the Script**:
   Open a terminal in your project's root directory and run:

   ```bash
   python run.py
   ```

## Workflow

The script follows this priority order for each audio file to maximize efficiency:

1. **Check for Embedded Chapters**: It first checks for chapter metadata within the audio file itself. If found, it uses this data and skips all other steps.

2. **Check for JSON Cache**: If no embedded chapters, it looks for a `.json` cache file.

3. **Check for SRT Cache**: If no JSON cache, it looks for a `.srt` file to parse.

4. **Speech Recognition**: Only if all the above sources are missing will the script perform a full transcription with Whisper.

5. **Splitting & Archiving**: Finally, it uses the acquired chapter data to split the audio and archives the source files.

## Configuration (`config.json`)

Modify this file to control the script's behavior.

| Parameter | Description | Example Values |
| :--- | :--- | :--- |
| `selected_model_key` | The Whisper model to use. Larger models are more accurate but slower. | `"base.en"`, `"medium"` |
| `local_models_dir` | Directory to store downloaded AI models. | `"local_models"` |
| `device` | Processing device: `cpu` or `cuda` (for NVIDIA GPUs). | `"cpu"` |
| `language` | Display language for program messages. | `"en"`, `"zh"` |
| `chunking_threshold_seconds` | Files longer than this (in seconds) will be processed in chunks to save memory. | `7200` (2 hours) |
| `input_dir` | Directory for source audio files. | `"input"` |
| `output_dir` | Directory for split chapter files. | `"output"` |
| `done_dir` | Directory to archive processed source files. | `"Done"` |
| `extract_chapter_title`| `true` to extract titles for filenames, `false` to use numbers only. | `true`, `false` |
| `use_hf_mirror` | `true` to use a mirror for downloading models (recommended for users in China). | `true`, `false` |
| `hf_endpoint` | The Hugging Face mirror URL. | `"https://hf-mirror.com"` |
| `models` | A map of model keys to their Hugging Face repository IDs. | `{...}` |

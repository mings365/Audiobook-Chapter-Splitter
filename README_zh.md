# 有声书章节切割器 (Audiobook Chapter Splitter)

一个强大的Python脚本，能够自动识别、检测章节并按章节将大型音频文件（如有声书、讲座、播客等）分割成独立的片段。

本工具利用 `faster-whisper` 库进行高精度语音识别，并智能解析生成的文本以定位章节标记，实现了从单个长音频到一系列按章节组织的独立文件的自动化流程。

## 功能特性

- **高精度识别**: 使用 `faster-whisper` 进行精准的、带词级时间戳的语音转录。
- **智能章节检测**:
  - **多来源支持**: 优先使用音频文件**内嵌的章节**，其次使用 `.json` 或 `.srt` 缓存，最后才进行语音识别，确保最高效率。
  - **多格式兼容**: 能识别阿拉伯数字 (`Chapter 1`)、英文单词 (`Chapter one`) 和罗马数字 (`Chapter III`)。
  - **智能标题提取**: 可选功能，能准确提取章节标题，并智能处理 "Mr."、"J. R. R. Tolkien" 等特殊情况。
- **智能缓存**: 自动创建 `.srt` (字幕) 和 `.json` (章节) 缓存文件。再次运行时，脚本会利用这些缓存**跳过**耗时的语音识别步骤。
- **封面保留**: 自动提取源音频文件的封面，并将其嵌入到所有切割后的章节文件中。
- **灵活配置**: 所有设置项均通过外部 `config.json` 文件管理，无需修改代码。
- **多语言界面**: 自动检测您的操作系统语言，并在中文和英文之间切换提示信息。
- **自动归档**: 处理完成后，会自动将源文件及相关缓存文件移入 `Done` 文件夹，保持 `input` 目录的整洁。

## 安装指南

在运行脚本前，您的系统需要安装 **FFmpeg**。

#### Windows

1.  从 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 下载最新的 FFmpeg 版本。
2.  解压下载的 `.zip` 文件。
3.  从 `bin` 文件夹中，将 `ffmpeg.exe` 和 `ffprobe.exe` 这两个文件复制到与 `run.py` 脚本**相同的目录**下。这是最简单的方式。

#### macOS

推荐使用 [Homebrew](https://brew.sh/) 安装：
```bash
brew install ffmpeg
```

#### Linux

使用您发行版的包管理器安装。

- **Debian/Ubuntu/Mint:**
  ```bash
  sudo apt-get update && sudo apt-get install ffmpeg
  ```
- **Fedora/CentOS/RHEL:**
  ```bash
  sudo dnf install ffmpeg
  ```

---

#### Python 依赖库

在安装完 FFmpeg 后，您需要安装所有必需的 Python 库。建议在一个虚拟环境中执行此操作。

```bash
pip install faster-whisper pydub ffmpeg-python word2number huggingface-hub
```

## 使用方法

1.  **准备项目文件夹**:
    确保您的项目文件夹结构如下。首次运行时，脚本会自动创建 `output`, `Done`, `local_models` 等文件夹。

    ```
    /Audiobook-Chapter-Splitter/  <-- 项目根目录
    ├── lang/                     <-- 语言文件夹
    │   ├── en.json
    │   └── zh.json
    ├── input/                    <-- 放入源音频文件
    │   └── my_audiobook.m4a
    ├── config.json               <-- 配置文件
    ├── run.py                    <-- 主程序
    ├── ffmpeg.exe                <-- (仅Windows需要)
    └── ffprobe.exe               <-- (仅Windows需要)
    ```

2.  **运行脚本**:
    在您的项目根目录打开一个终端或命令行窗口，运行：
    ```bash
    python run.py
    ```

## 工作流程

程序会为 `input` 目录下的每一个音频文件，严格遵循以下处理顺序，以确保最高效率：

1.  **检查内嵌章节**: 首先检查音频文件本身是否包含章节元数据。如果找到，将直接使用这些信息并跳过后续所有识别步骤。
2.  **检查JSON缓存**: 如果没有内嵌章节，则寻找同名的 `.json` 缓存文件。如果找到，直接加载章节信息。
3.  **检查SRT缓存**: 如果JSON缓存也不存在，则寻找同名的 `.srt` 字幕文件。如果找到，将解析此文件以提取章节。
4.  **语音识别**: 只有在以上所有信息源都缺失的情况下，程序才会启动 Whisper 模型进行完整的语音识别，并将结果保存为 `.srt` 文件，然后再解析它。
5.  **音频切割与归档**: 最后，利用获取到的章节信息进行音频切割，并在完成后将源文件归档。

## 配置文件说明 (`config.json`)

您可以直接修改此文件来调整程序的行为。

| 参数 | 意义 | 示例值 |
| :--- | :--- | :--- |
| `selected_model_key` | 选择用于识别的Whisper模型。模型越大越准但越慢。 | `"base.en"`, `"medium"` |
| `local_models_dir` | 下载的AI模型将存放在哪个文件夹。 | `"local_models"` |
| `device` | 使用 `cpu` 还是 `cuda` (NVIDIA显卡) 来运行模型。 | `"cpu"` |
| `language` | 程序界面信息的显示语言。 | `"en"`, `"zh"` |
| `chunking_threshold_seconds` | 音频时长超过此秒数时，将启用内存安全的“分块处理”模式。 | `7200` (2小时) |
| `input_dir` | 源音频文件的输入目录。 | `"input"` |
| `output_dir` | 切割后章节文件的输出目录。 | `"output"` |
| `done_dir` | 已处理完毕的源文件及缓存的归档目录。 | `"Done"` |
| `extract_chapter_title`| 是否提取章节标题并用于文件命名。 | `true`, `false` |
| `use_hf_mirror` | 是否使用镜像地址下载模型（建议中国大陆用户开启）。 | `true`, `false` |
| `hf_endpoint` | Hugging Face的镜像地址。 | `"https://hf-mirror.com"` |
| `models` | 模型简称与Hugging Face仓库地址的映射表。 | `{...}` |

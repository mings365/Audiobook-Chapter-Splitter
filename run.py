import os
import json
import re
import shutil
import sys
import locale
import tempfile
from pathlib import Path
from pydub import AudioSegment
import ffmpeg
from word2number import w2n
from faster_whisper import WhisperModel

# --- Global Constants ---
SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".aac", ".m4a")
CONFIG_FILENAME = "config.json"

# --- Global Variables ---
get_string = lambda key, **kwargs: key.format(**kwargs)

def load_language_strings(config):
    """Loads language strings from a JSON file based on the provided config."""
    lang_code = config.get("language", "en")
    lang_dir = Path(config.get("lang_dir", "Lang"))
    lang_file = lang_dir / f"{lang_code}.json"
    
    if not lang_file.is_file():
        print(f"Warning: Language file for '{lang_code}' not found in '{lang_dir}'. Falling back to English.")
        lang_file = lang_dir / "en.json"
        if not lang_file.is_file():
             print(f"Fatal Error: Default language file 'lang/en.json' not found in '{lang_dir}'. Cannot continue.")
             sys.exit(1)

    with open(lang_file, 'r', encoding='utf-8') as f:
        strings = json.load(f)

    def get_string_func(key, **kwargs):
        return strings.get(key, key).format(**kwargs)

    return get_string_func

def load_config():
    """Loads the config.json file and validates required keys, exiting if any are missing."""
    config_path = Path(CONFIG_FILENAME)
    if not config_path.is_file():
        # Use a direct print here as language is not yet configured.
        print(f"Error: Configuration file '{CONFIG_FILENAME}' not found.")
        print("Please ensure you have created a config.json file.")
        sys.exit(1)

    print(f"  > Loading configuration from {CONFIG_FILENAME}...")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Configuration file '{CONFIG_FILENAME}' is invalid. Please check the JSON syntax.")
        print(f"Details: {e}")
        sys.exit(1)

    required_keys = [
        "selected_model_key", "local_models_dir", "device", "language", "lang_dir", "chunking_threshold_seconds", "input_dir",
        "output_dir", "done_dir", "extract_chapter_title", "models"
    ]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        print(f"Error: The configuration file '{CONFIG_FILENAME}' is missing the following required keys: {', '.join(missing_keys)}")
        sys.exit(1)

    return config


def get_audio_duration(file_path, get_string):
    """Gets the audio duration in seconds using ffprobe without loading the full file."""
    try:
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])
    except ffmpeg.Error as e:
        stderr_str = e.stderr.decode('utf-8', errors='ignore')
        print(get_string("error_ffprobe_duration", filename=Path(file_path).name))
        if "No such file or directory" in stderr_str or "not found" in stderr_str:
             print(get_string("error_ffprobe_not_found"))
        else:
             print(get_string("error_ffmpeg_general", error=stderr_str))
        return None
    except Exception as e:
        print(get_string("error_get_duration_unknown", filename=Path(file_path).name, error=e))
        return None


def prepare_model(config, get_string):
    """Checks for a local model and returns its path."""
    model_key = config["selected_model_key"]
    local_dir = config["local_models_dir"]
    
    model_path = Path(local_dir) / model_key
    
    # Check for the existence of a key file within the model directory.
    if (model_path / "model.bin").is_file():
        print(get_string("model_found_locally", model_key=model_key, model_path=model_path))
        return str(model_path)
    else:
        print(get_string("error_model_not_found_local", model_key=model_key, model_path=model_path))
        return None

def transcribe_in_chunks(model, audio_path, total_duration_sec, get_string):
    """
    Transcribes a large audio file by splitting it into chunks to save memory.
    """
    print(get_string("transcription_memory_save"))
    
    with tempfile.TemporaryDirectory() as temp_dir:
        audio = AudioSegment.from_file(audio_path)
        chunk_length_ms = 15 * 60 * 1000  # 15 minutes
        chunks = range(0, len(audio), chunk_length_ms)
        
        all_segments = []
        time_offset = 0.0

        for i, start_ms in enumerate(chunks):
            end_ms = start_ms + chunk_length_ms
            chunk = audio[start_ms:end_ms]
            chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp3")
            
            print(get_string("transcription_chunk_export", current=i+1, total=len(chunks)))
            chunk.export(chunk_path, format="mp3")
            
            print(get_string("transcription_chunk_process", current=i+1, total=len(chunks)))
            segments_generator, _ = model.transcribe(chunk_path, word_timestamps=True, language="en")
            
            for segment in segments_generator:
                segment.start += time_offset
                segment.end += time_offset
                all_segments.append(segment)
                progress = (segment.end / total_duration_sec) * 100
                print(get_string("transcribing", progress=progress), end='\r')

            time_offset += len(chunk) / 1000.0
            
    return all_segments


def extract_cover_art(input_path, temp_dir, get_string):
    """
    Extracts embedded cover art to a temporary file.
    """
    print(get_string("checking_cover_art"))
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        
        if video_stream:
            output_cover_path = os.path.join(temp_dir, "cover.jpg")
            ffmpeg.input(input_path).output(output_cover_path, vframes=1, **{'q:v': 2}).run(overwrite_output=True, quiet=True)
            print(get_string("cover_art_found", cover_path=output_cover_path))
            return output_cover_path
        else:
            print(get_string("no_cover_art_found"))
            return None
    except Exception as e:
        print(get_string("error_extracting_cover_art", error=e))
        return None

def extract_embedded_chapters(file_path, get_string):
    """
    Extracts chapter metadata directly from the audio file if it exists.
    """
    print(get_string("checking_embedded_chapters"))
    chapters = []
    try:
        probe = ffmpeg.probe(file_path, show_chapters=None)
        if 'chapters' in probe and probe['chapters']:
            for i, chap in enumerate(probe['chapters']):
                chapters.append({
                    "number": i + 1,
                    "start_time": float(chap['start_time']),
                    "title": chap.get('tags', {}).get('title', f'Chapter {i+1}')
                })
            print(get_string("found_embedded_chapters", count=len(chapters)))
            return chapters
    except Exception:
        pass
    print(get_string("no_embedded_chapters"))
    return []

def srt_time_to_seconds(time_str):
    """Converts SRT time format (HH:MM:SS,ms) to seconds."""
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

def roman_to_int(s):
    """Converts a Roman numeral string to an integer."""
    s = s.upper()
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    for i in range(len(s)):
        if i > 0 and roman_map[s[i]] > roman_map[s[i - 1]]:
            result += roman_map[s[i]] - 2 * roman_map[s[i - 1]]
        else:
            result += roman_map[s[i]]
    return result

def extract_title_from_text(text):
    """
    Extracts a title from a string, stopping at the first real sentence-ending punctuation.
    """
    ABBREVIATIONS = {'mr', 'mrs', 'ms', 'dr', 'prof', 'st', 'vol', 'no', 'etc', 'rev', 'capt'}
    
    if not text:
        return ""

    sentences = re.split(r'(?<=[.?!])\s+', text)
    
    title_parts = []
    for sentence in sentences:
        title_parts.append(sentence)
        words = sentence.rstrip('.?!').split()
        if not words: break
            
        last_word = words[-1].lower()
        if last_word in ABBREVIATIONS or (len(last_word) == 1 and last_word.isalpha()):
            continue
        else:
            break
            
    full_title = " ".join(title_parts).strip()
    return full_title.rstrip('.?!').strip()

def parse_srt_for_chapters(srt_path, extract_title, get_string):
    """Parses an SRT file to find chapter markers and optional titles."""
    print(get_string("parsing_srt", filename=srt_path.name))
    chapters = []
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        blocks = content.strip().split('\n\n')
        for block_index, block in enumerate(blocks):
            lines = block.strip().split('\n')
            if len(lines) < 3: continue

            text_content = " ".join(lines[2:])
            if 'chapter' in text_content.lower():
                words = text_content.split()
                for i, word in enumerate(words):
                    if word.lower().strip('.,?!') == 'chapter' and i + 1 < len(words):
                        next_word_cleaned = words[i+1].strip().lower().strip('.,?!')
                        
                        chapter_number = None
                        try:
                            chapter_number = int(next_word_cleaned)
                        except ValueError:
                            try:
                                chapter_number = w2n.word_to_num(next_word_cleaned)
                            except ValueError:
                                try:
                                    chapter_number = roman_to_int(next_word_cleaned)
                                except (KeyError, IndexError):
                                    continue

                        if chapter_number is None:
                            continue

                        start_time = srt_time_to_seconds(lines[1].split(' --> ')[0])
                        chapter_info = { "number": chapter_number, "start_time": start_time }

                        if extract_title:
                            title_text = " ".join(words[i+2:]).strip()
                            
                            if not title_text and (block_index + 1) < len(blocks):
                                next_block_lines = blocks[block_index + 1].strip().split('\n')
                                if len(next_block_lines) >= 3:
                                    title_text = " ".join(next_block_lines[2:]).strip()
                            
                            title = extract_title_from_text(title_text)
                            chapter_info["title"] = title
                            print(get_string("chapter_detected_with_title", number=chapter_number, title=title[:50].strip(), time=start_time))
                        else:
                            print(get_string("chapter_detected_no_title", number=chapter_number, time=start_time))

                        chapters.append(chapter_info)
                        break
    except Exception as e:
        print(get_string("error_parsing_srt", error=e))

    chapters.sort(key=lambda x: x["number"])
    return chapters

def format_srt_time(seconds):
    """Converts seconds to SRT time format (HH:MM:SS,ms)."""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)
    hours, minutes, seconds = milliseconds // 3600000, milliseconds % 3600000 // 60000, milliseconds % 60000 // 1000
    milliseconds %= 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def write_srt_file(segments, srt_path, get_string):
    """Writes transcription segments to a .srt file."""
    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments):
                f.write(f"{i + 1}\n")
                f.write(f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n")
                f.write(f"{segment.text.strip()}\n\n")
    except Exception as e:
        print(get_string("error_writing_srt", error=e))

def sanitize_filename(name):
    """Removes illegal characters and shortens a string to be a valid filename."""
    sanitized_name = re.sub(r'[\\/*?:"<>|]', "", name)
    sanitized_name = re.sub(r'\s+', '.', sanitized_name)
    return sanitized_name.strip('.')[:100]

def process_chapter_gaps(chapters):
    """
    Analyzes chapter list for gaps and generates number strings for filenames (e.g., '002-003').
    """
    if not chapters:
        return []

    processed_chapters = []
    
    for i, current_chap in enumerate(chapters):
        start_time = 0.0 if i == 0 else current_chap['start_time']
        
        is_last_chapter = (i == len(chapters) - 1)
        next_chap_number = chapters[i+1]['number'] if not is_last_chapter else None

        number_str = ""
        if is_last_chapter:
            number_str = f"{current_chap['number']:03}"
        elif next_chap_number > current_chap['number'] + 1:
            number_str = f"{current_chap['number']:03}-{(next_chap_number - 1):03}"
        else:
            number_str = f"{current_chap['number']:03}"

        processed_chapters.append({
            'start_time': start_time,
            'title': current_chap.get('title', ''),
            'number_str': number_str
        })
        
    return processed_chapters

def main():
    """Main execution function."""
    config = load_config()
    get_string = load_language_strings(config)

    print(get_string("program_start"))
    
    input_dir = config["input_dir"]
    output_dir = config["output_dir"]
    local_models_dir = config["local_models_dir"]
    done_dir = config["done_dir"]
    extract_title = config["extract_chapter_title"]
    device = config["device"]
    chunk_threshold_sec = config["chunking_threshold_seconds"]
    compute_type = "float16" if device == "cuda" else "int8"

    print(get_string("ffmpeg_path_info"))
    print(get_string("ffmpeg_path_ensure"))
    print(get_string("processing_start"))
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(local_models_dir, exist_ok=True)
    os.makedirs(done_dir, exist_ok=True)

    model = None

    print(get_string("scanning_folder", input_dir=input_dir))
    audio_files_to_process = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(SUPPORTED_EXTENSIONS):
                audio_files_to_process.append(os.path.join(root, file))

    if not audio_files_to_process:
        print(get_string("no_audio_files_found"))
        return
        
    for input_path in audio_files_to_process:
        relative_path = os.path.relpath(input_path, input_dir)
        relative_dir = os.path.dirname(relative_path)
        
        json_path = Path(input_path).with_suffix('.json')
        srt_path = Path(input_path).with_suffix('.srt')
        print(get_string("processing_file", filename=relative_path))

        output_sub_dir_name = Path(input_path).stem.strip()
        output_sub_dir = os.path.join(output_dir, relative_dir, output_sub_dir_name)
        os.makedirs(output_sub_dir, exist_ok=True)
        print(get_string("output_will_be_saved_to", output_sub_dir=output_sub_dir))
        
        total_duration_sec = get_audio_duration(input_path, get_string)
        if total_duration_sec is None:
            print(get_string("error_getting_duration", filename=relative_path))
            continue
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cover_art_path = extract_cover_art(input_path, temp_dir, get_string)

            chapters = []
            chapters = extract_embedded_chapters(input_path, get_string)
            
            if not chapters and json_path.is_file():
                print(get_string("found_chapter_cache", json_path_name=json_path.name))
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        chapters = json.load(f)
                    cache_has_title = chapters and 'title' in chapters[0]
                    if cache_has_title != extract_title:
                        print(get_string("cache_format_mismatch", extract_title=extract_title))
                        chapters = []
                    else:
                        print(get_string("cache_load_success", count=len(chapters)))
                except Exception as e:
                    print(get_string("cache_load_fail", error=e))
                    chapters = []

            if not chapters:
                if not srt_path.is_file():
                    print(get_string("srt_not_found"))
                    if model is None:
                        print(get_string("loading_model"))
                        model_path = prepare_model(config, get_string)
                        if not model_path:
                            print(get_string("model_prep_fail"))
                            break
                        try:
                            model = WhisperModel(model_path, device=device, compute_type=compute_type)
                            print(get_string("model_load_success"))
                        except Exception as e:
                            print(get_string("error_loading_model", error=e))
                            break
                    
                    try:
                        if total_duration_sec > chunk_threshold_sec:
                            segments = transcribe_in_chunks(model, input_path, total_duration_sec, get_string)
                        else:
                            print(get_string("transcription_direct"))
                            segments_generator, _ = model.transcribe(input_path, word_timestamps=True, language="en")
                            segments = []
                            for segment in segments_generator:
                                progress = (segment.end / total_duration_sec) * 100
                                print(get_string("transcribing", progress=progress), end='\r')
                                segments.append(segment)
                        
                        print(get_string("transcribing", progress=100.0) + " ") 
                        print(get_string("transcription_complete"))
                        
                        print(get_string("saving_srt", srt_path_name=srt_path.name))
                        write_srt_file(segments, srt_path, get_string)
                    except Exception as e:
                        print(get_string("error_transcribing", filename=relative_path, error=e))
                        continue
                else:
                    print(get_string("found_existing_srt", srt_path_name=srt_path.name))

                chapters = parse_srt_for_chapters(srt_path, extract_title, get_string)
            
            if chapters and not json_path.is_file():
                print(get_string("saving_chapters_to_cache", count=len(chapters), json_path_name=json_path.name))
                try:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(chapters, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    print(get_string("error_saving_json", error=e))
            
            if not chapters:
                print(get_string("no_chapters_found"))
                continue

            print(get_string("splitting_audio"))
            try:
                print(get_string("loading_full_audio"))
                audio = AudioSegment.from_file(input_path)
                
                processed_chapters = process_chapter_gaps(chapters)
                
                chapters_to_cut = processed_chapters.copy()
                chapters_to_cut.append({"number_str": "end", "start_time": total_duration_sec})

                for i in range(len(chapters_to_cut) - 1):
                    current_chapter = chapters_to_cut[i]
                    next_chapter = chapters_to_cut[i+1]
                    
                    start_ms = 0 if current_chapter['start_time'] == 0.0 else max(0, int(current_chapter["start_time"] * 1000) - 500)
                    end_ms = int(next_chapter["start_time"] * 1000)
                    
                    number_str = current_chapter["number_str"]
                    
                    if extract_title:
                        sanitized_title = sanitize_filename(current_chapter.get("title", ""))
                        output_filename = f"{number_str}.{sanitized_title}.mp3"
                    else:
                        output_filename = f"{number_str}.mp3"
                    
                    output_path = os.path.join(output_sub_dir, output_filename)
                    
                    print(get_string("exporting_file", output_filename=output_filename, start_sec=start_ms/1000, end_sec=end_ms/1000))
                    chapter_audio = audio[start_ms:end_ms]
                    
                    export_params = {"format": "mp3"}
                    if cover_art_path:
                        export_params["cover"] = cover_art_path
                    chapter_audio.export(output_path, **export_params)

                print(get_string("file_process_complete", filename=relative_path))
                
            except Exception as e:
                print(get_string("error_splitting_file", filename=relative_path, error=e))
                continue

        # Archive processed files
        print(get_string("archiving_files"))
        try:
            archive_dir = os.path.join(done_dir, relative_dir)
            os.makedirs(archive_dir, exist_ok=True)
            
            shutil.move(input_path, os.path.join(archive_dir, Path(input_path).name))
            print(get_string("moved_file", filename=relative_path))
            
            if srt_path.is_file():
                shutil.move(srt_path, os.path.join(archive_dir, srt_path.name))
                print(get_string("moved_file", filename=os.path.join(relative_dir, srt_path.name)))

            if json_path.is_file():
                shutil.move(json_path, os.path.join(archive_dir, json_path.name))
                print(get_string("moved_file", filename=os.path.join(relative_dir, json_path.name)))
        except Exception as e:
            print(get_string("error_archiving", error=e))
            
    print(get_string("all_files_processed"))


if __name__ == "__main__":
    main()

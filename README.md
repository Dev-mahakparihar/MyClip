# MyClip — Local AI YouTube Clipper

MyClip is a personal, local-first Streamlit application that turns a public
YouTube video and natural-language instructions into captioned short clips.
Speech transcription and clip selection run locally with faster-whisper and
Ollama. FFmpeg renders and FFprobe validates each exported video. There are no
accounts, paid AI APIs, subscriptions, clip quotas, or automatic output cleanup.

## Requirements

- macOS 13 or later and Python 3.10 or newer (Python 3.12 recommended).
- FFmpeg/FFprobe, yt-dlp (installed from Python requirements), Ollama, and a
  local Ollama model such as `qwen2.5:3b`.
- Enough local disk space for downloaded source videos, Whisper model files,
  and rendered clips. MyClip checks for 2 GB free before starting a download.
- First use downloads the selected faster-whisper model from its model host.
  Subsequent transcription runs locally.

MyClip only accepts public YouTube URLs and does not use cookies, sign-in,
authentication, DRM, or other access-control circumvention. Only process media
you are authorized to download and use, and comply with applicable platform
terms and copyright law.

## Setup

Install Homebrew from [brew.sh](https://brew.sh), install Ollama from
[ollama.com](https://ollama.com/download/mac), then run:

```bash
./setup-macos.sh
```

The setup script installs FFmpeg with Homebrew when needed, creates `.venv`,
installs Python dependencies, and pulls the default Ollama model if missing.
If your system Python is too old, or the native faster-whisper/CTranslate2
runtime is unavailable for it, install Python 3.12 and run:

```bash
PYTHON_BIN=python3.12 ./setup-macos.sh
```

Start the application:

```bash
ollama serve
```

In a second terminal, from this project folder:

```bash
.venv/bin/streamlit run app.py --server.address 127.0.0.1
```

Open the local URL Streamlit prints (normally <http://localhost:8501>).

## Use

1. Paste a public YouTube video URL and confirm you have permission to process it.
2. Describe the moments to find. The default instruction is tuned for gaming
   livestreams; clips are inferred from transcript evidence, not visual gameplay.
3. Set clip count, minimum and maximum duration, aspect ratio, and caption style.
4. Start processing. Progress, errors, completed clips, previews, and downloads
   appear in the page and remain in local job history.

The number-of-clips control has no artificial product cap. In practice, model
quality, source length, available disk, and processing time constrain results.
Identical in-flight submissions are deduplicated. Re-running a completed source
is allowed.

## Local storage and settings

- Default exports and retained source videos: `~/Movies/MyClip/<job-id>/`.
- Job database, transcript copies, and per-job logs:
  `~/Library/Application Support/MyClip/`.
- Change the output folder in the Streamlit sidebar. Jobs store their chosen
  folder in local SQLite metadata.
- Optional environment settings:
  `MYCLIP_OUTPUT_DIR`, `MYCLIP_DATA_DIR`, `MYCLIP_OLLAMA_MODEL`,
  `MYCLIP_WHISPER_MODEL`, `MYCLIP_WHISPER_DEVICE`,
  `MYCLIP_WHISPER_COMPUTE_TYPE`, and `OLLAMA_HOST`.

Example local configuration:

```bash
export MYCLIP_OLLAMA_MODEL=qwen2.5:3b
export MYCLIP_WHISPER_MODEL=small
export MYCLIP_OUTPUT_DIR="$HOME/Movies/MyClip"
```

## Processing details and limitations

- Candidate windows overlap; Ollama ranks timestamped transcript passages and
  returns structured JSON. Python rejects invalid, out-of-bounds, out-of-range,
  and overlapping selections before rendering.
- Before downloading source media, MyClip checks the public video metadata with
  yt-dlp under a 20-second process timeout and does not download the video during
  this validation stage. The required Ollama model is checked locally; missing
  models are reported rather than downloaded as a side effect of starting a job.
- Original audio is retained (re-encoded as AAC). Captions are aligned to
  faster-whisper segment timestamps. Bold and Standard burn captions into the
  video; None leaves captions off. Captions currently use segment-level timing;
  animated word-by-word/kinetic caption effects are **not implemented**.
- Vertical 9:16 and 16:9 exports use safe center cropping. True subject/gameplay
  tracking and automatic reframing are **not implemented**; OpenCV is included
  for future visual analysis. MyClip does not claim transcript-derived moments
  are visually verified.
- Speech transcription currently requires detected speech. Sources with no
  speech fail with an actionable message rather than creating speculative clips.
- Long jobs run in a local background worker while Streamlit polls for progress.
  Per-job logs are retained alongside the SQLite history.

## Tests

After setup, run:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The automated suite covers overlapping candidate windows, duration and overlap
selection, and FFprobe output validation. For an end-to-end smoke test, process
a short public video you are authorized to use from the local UI; the app then
performs real downloading, transcription, Ollama selection, FFmpeg rendering,
caption generation, and FFprobe validation.

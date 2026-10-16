# Weekly Spelling Practice

A child-friendly Streamlit application for practising weekly English and Chinese spelling lists (听写 / 默写). It provides AI-assisted word notes, audio playback, and an interactive one-word-at-a-time dictation quiz.

## Features

- Enter English words, Chinese characters/phrases, or a mixed list (one entry per line).
- English notes: syllables, child-friendly meaning, context sentence, and spelling/phonics tip.
- Chinese notes: tone-marked pinyin (locally generated with `pypinyin`), meaning, example, and AI-assisted stroke count, radical, structure, and stroke hints.
- gTTS audio for words and Chinese pinyin.
- Quiz mode with audio, meaning/spelling hint, typed answer, immediate feedback, and score.
- Gemini analysis is optional; the app remains usable without an API key. If Gemini is unavailable, Chinese pinyin still works locally.

> Chinese stroke-order and radical notes are generated as study hints and can vary by school curriculum or dictionary. Verify them against the child's textbook or teacher.

## Local setup

Requires Python 3.10 or later and an internet connection for Gemini and gTTS.

```bash
cd spelling-practice
python -m venv .venv
```

Activate the virtual environment:

- macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`

Install dependencies and start Streamlit:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print a local URL (usually <http://localhost:8501>).

## Configure Gemini (optional, recommended)

Create an API key in [Google AI Studio](https://aistudio.google.com/apikey). Supply it in either of these ways:

### Environment variable

```bash
# macOS/Linux
export GOOGLE_API_KEY="your-api-key"
streamlit run app.py
```

```powershell
# Windows PowerShell
$env:GOOGLE_API_KEY="your-api-key"
streamlit run app.py
```

The app also accepts `GEMINI_API_KEY`. Alternatively, enter the key in the app's sidebar; it is used for the current session.

### Streamlit secrets

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_API_KEY = "your-api-key"
```

Do not commit this file to a public repository.

The application calls `gemini-2.5-flash` to generate the word explanations. Generated details are not guaranteed to be perfect; check curriculum-specific Chinese stroke/radical notes.

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository containing `app.py`, `requirements.txt`, and this README.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) and create an app from the repository, selecting `app.py` as the entry point.
3. In the app settings, add a secret named `GOOGLE_API_KEY` (optional, but needed for Gemini explanations).
4. Deploy. The app uses gTTS, so the deployed app also needs internet access for audio playback.

## Usage

1. Enter the weekly list, one word or phrase per line, and click **Save my list**.
2. Expand a word in **Learn about each word** to see its notes and play audio.
3. In **Dictation quiz**, listen, use the hint if needed, type the answer, and check it.
4. Continue through the list to see the score, then try again.

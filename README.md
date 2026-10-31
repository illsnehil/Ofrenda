# Ofrenda

A local-first ofrenda builder for Día de los Muertos. You tell the stories of someone you miss (typed or spoken),
a local LLM asks gentle follow-up questions and writes a remembrance from *only* what you said, and you get a
candlelit ofrenda page you can keep as one HTML file. No cloud, no accounts, no API keys.

## Run it
```bash
# 1. Inference: https://ollama.com
ollama pull qwen2.5:7b          # fits 16 GB RAM; try llama3.1:8b or gemma2:9b too
# 2. Transcription (optional, enables the Record button)
pip install -r requirements.txt  # first run downloads Whisper "small" once
# 3. Go
python3 server.py                # open http://127.0.0.1:8765
```
Swap models: `OFRENDA_MODEL=llama3.1:8b python3 server.py`. Smaller Whisper: `OFRENDA_WHISPER=base`.

## Prove it's offline
After the one-time downloads, turn Wi-Fi off and run it again. The server binds to 127.0.0.1 only, the page loads
no fonts, scripts or images from the web, and photos are resized in your browser and embedded in the saved file.

## Design choices
- The guide never speaks *as* the person who died; it only asks questions.
- The remembrance prompt forbids invented facts, and the text is editable before the ofrenda is built.

# Multimodal Voice Task Extraction

Ingest and process voice notes and audio messages directly using Gemini's native multimodal capabilities.

## Rules

- **Combined API Request**: Perform audio transcription and structured task parsing in a single Gemini API call using `genai.upload_file` and prompt structures. Avoid running separate speech-to-text (e.g., Whisper) and NLP text-parsing models.
- **Dynamic Extension Resolution**: Determine the audio file format dynamically from the incoming WhatsApp `mime_type` and write the binary content to a temporary file matching that extension (e.g., `.ogg`, `.opus`, `.mp3`).
- **Resource Cleanup**: Always delete temporary audio files (`os.unlink(temp_path)`) within a `finally` block to prevent disk exhaustion.
- **Unified JSON Response**: Request the LLM to return a single JSON string containing both the full `transcription` and the list of extracted `tasks`.

## Code Example

```python
# Resolve audio file extension
extension = '.ogg'
if 'opus' in mime_type.lower():
    extension = '.opus'

# Save audio to temp file for upload
with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
    temp_file.write(audio_data)
    temp_path = temp_file.name

try:
    # Upload file and generate content
    audio_file = genai.upload_file(path=temp_path, mime_type=mime_type)
    response = model.generate_content([audio_prompt, audio_file])
    
    # Process tasks JSON output...
finally:
    # Always clean up temp files
    try:
        os.unlink(temp_path)
    except Exception:
        pass
```

## Rationale
- Using Gemini's native audio support provides faster execution and significantly lowers API token and computing costs.
- Mandatory file unlinking ensures temp folders do not overflow when many users send voice notes.

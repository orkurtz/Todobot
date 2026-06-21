# WhatsApp Integration & Webhook Handling

Standardize webhook lifecycles, background message processing, and Hebrew command string normalization.

## Rules

- **Immediate Webhook ACK**: Return a HTTP `200 OK` immediately (within 1-2 seconds) to prevent WhatsApp from retrying the request. Process the actual task logic asynchronously on a background daemon thread.
- **Deduplication Check**: Store and query incoming `whatsapp_message_id`s in the database, ignoring any retried payloads that have already been logged.
- **BiDi & Zero-Width Sanitization**: Strip hidden Right-to-Left (RTL) marks (`\u200f`), Left-to-Right (LTR) marks (`\u200e`), zero-width spaces, and trailing punctuation when parsing Hebrew commands.
- **Rate-Limiting**: Reject user traffic that exceeds a burst limit (e.g., 10 messages per minute) at the entry point to protect processing limits.

## Code Example

```python
# Sanitization utility for command matching
def clean_command(text: str) -> str:
    # Remove hidden BiDi control marks
    text = text.replace('\u200f', '').replace('\u200e', '')
    # Clean whitespace and strip punctuation
    text = re.sub(r'[?.!,;:]', '', text)
    return text.strip().lower()

# Threaded webhook dispatcher
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Perform lightweight validation
    # Dispatch processing asynchronously
    thread = Thread(target=process_message_async, args=(payload,))
    thread.daemon = True
    thread.start()
    
    return "OK", 200  # Return status fast
```

## Rationale
- WhatsApp retries payloads if the response takes longer than 5 seconds, causing redundant executions and duplicated tasks.
- Mobile WhatsApp inputs often inject hidden RTL control characters when typing mixed English and Hebrew commands, which breaks simple string matching.

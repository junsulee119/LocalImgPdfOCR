"""
Custom Streamer for Hugging Face Transformers
"""
from transformers import TextStreamer

class TextCallbackStreamer(TextStreamer):
    """
    Streamer that invokes a callback with decoded text chunks.
    """
    def __init__(self, tokenizer, callback, skip_prompt=False, **decode_kwargs):
        super().__init__(tokenizer, skip_prompt, **decode_kwargs)
        self.callback = callback

    def on_finalized_text(self, text: str, stream_end: bool = False):
        """
        Called when text is decoded.
        """
        # Invoke the callback with the new chunk of text
        self.callback(text)
        super().on_finalized_text(text, stream_end)

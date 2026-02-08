# MiniCPM-o 4.5 Integration Guide

This guide explains how to integrate **MiniCPM-o 4.5**, a state-of-the-art multimodal model, with the Autonomous Co-Regulator.

## Why MiniCPM-o 4.5?

MiniCPM-o 4.5 offers superior capabilities in:
- **Vision Understanding**: Better scene analysis and OCR.
- **Multimodal Interaction**: Native support for images and text.
- **Efficiency**: Runs efficiently on local consumer hardware (e.g., Apple Silicon, NVIDIA GPUs).

## Prerequisites

You need a way to serve the model with an OpenAI-compatible API. We recommend:
- **llama.cpp** (Server mode)
- **Ollama**

### Option 1: Using llama.cpp (Recommended)

1.  **Download the Model**:
    Download the GGUF quantized version of MiniCPM-o 4.5 from Hugging Face.
    [https://huggingface.co/openbmb/MiniCPM-o-4_5-gguf](https://huggingface.co/openbmb/MiniCPM-o-4_5-gguf)

2.  **Run the Server**:
    Assuming you have `llama-server` installed (part of llama.cpp):

    ```bash
    ./llama-server -m models/MiniCPM-o-4_5-Q4_K_M.gguf --port 8080 --host 0.0.0.0 --ctx-size 4096
    ```

    Ensure the server is running and accessible at `http://localhost:8080`.

### Option 2: Using Ollama

1.  **Pull the Model**:
    If available in the Ollama library:
    ```bash
    ollama pull openbmb/MiniCPM-o-4_5
    ```
    *(Note: Check the exact model tag on [Ollama Library](https://ollama.com/library))*

2.  **Serve**:
    Ollama runs on port 11434 by default.

## Configuration

Update your configuration to point to the local server.

### 1. Update `user_data/config.json` (Recommended)

Create or edit `user_data/config.json`:

```json
{
  "LOCAL_LLM_URL": "http://127.0.0.1:8080/v1/chat/completions",
  "LOCAL_LLM_MODEL_ID": "openbmb/MiniCPM-o-4_5"
}
```

*Note: For Ollama, the URL is typically `http://127.0.0.1:11434/v1/chat/completions` and model ID is the tag you pulled (e.g., `minicpm-v`).*

### 2. Verify Integration

1.  Start the application.
2.  Check the logs (`acr_app.log`) or console.
3.  You should see a debug message: `LMMInterface-DEBUG: Optimizing for MiniCPM-o...` when requests are made.

## Troubleshooting

- **400 Bad Request**: Ensure the `LOCAL_LLM_MODEL_ID` matches exactly what the server expects. `llama.cpp` often accepts any string or the filename, while Ollama is strict.
- **Slow Response**: MiniCPM-o is a large model (8B+). Ensure you are using a quantized version (Q4_K_M) if VRAM is limited.

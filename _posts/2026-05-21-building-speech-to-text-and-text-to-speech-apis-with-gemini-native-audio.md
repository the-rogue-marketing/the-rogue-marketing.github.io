---
layout: post
title: "Building Speech-to-Text and Text-to-Speech APIs with Gemini Native Audio"
date: 2026-05-21
last_modified_at: 2026-05-26
author: professor-xai
categories: [Generative AI, Voice AI, API Development]
image: assets/images/gemini-audio-api-architecture.png
description: "A comprehensive developer guide to building native Speech-to-Text (STT) and Text-to-Speech (TTS) pipelines using the Gemini API, WebSockets, and Python google-genai SDK."
keywords: "gemini text to speech api, gemini speech to text, native audio llm, google-genai audio python, local audio microservice, websockets live api"
---

Traditionally, building voice-enabled applications required developer teams to glue together multiple disconnected services. You had to capture user speech, transcribe it using a Speech-to-Text (STT) model like Whisper, pass the text to a Large Language Model (LLM) to generate a response, and then convert that response back to audio using a third-party Text-to-Speech (TTS) engine.

This modular pipeline has three major flaws:
1.  **High Latency:** Each network hop between services adds 200–500ms of lag, resulting in slow, awkward conversations.
2.  **Cascade Errors:** A single transcription mistake by the STT model throws off the entire LLM response.
3.  **Loss of Expressiveness:** Synthesizing text to speech strips away the emotional nuances of human voice, like tone, pitch, and speed.

Google Gemini's native audio capabilities solve these issues by processing raw audio input and output directly within the model. 

In this comprehensive developer's guide, we will build a complete, production-grade Voice AI microservice in Python using **FastAPI** and the **google-genai** SDK. We will implement standard REST endpoints for transcription and synthesis, configure a bidirectional **WebSocket endpoint for the Gemini Live API**, and provide a complete **HTML/JS frontend sandbox** for real-time testing.

---

## Technical Architecture: Unified Voice Pipeline

Instead of converting audio to text, Gemini tokenizes sound waves directly:
- **Audio Inputs:** Handled by converting raw sound waves into time-frequency tokens (32 tokens per second).
- **Audio Outputs:** The model directly outputs binary audio buffers (25 tokens per second) using predefined voice configurations.

```
                    Gemini Live API WebSocket Flow
┌──────────────┐   PCM Audio Chunks   ┌───────────────┐   WebSocket Proxy   ┌─────────────┐
│ Client Mic   ├─────────────────────►│  FastAPI      ├────────────────────►│ Gemini Live │
│ (Browser)    │◄─────────────────────┤  WebSocket    │◄────────────────────┤  (Google)   │
└──────────────┘   Binary Audio Out   └───────────────┘   Raw PCM Audio     └─────────────┘
```

---

## Development Environment Setup

Ensure your local development environment has the necessary libraries:
```bash
pip install google-genai fastapi uvicorn pydantic python-multipart websockets
```

Make sure your Gemini API key is configured in your environment variables:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

---

## 1. The FastAPI Backend Microservice

Here is the complete backend code, including endpoints for transcription, text-to-speech synthesis, and a WebSocket pipeline to handle real-time, low-latency, bidirectional audio streaming.

```python
import os
import io
import json
import shutil
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

# Initialize FastAPI application
app = FastAPI(
    title="Gemini Audio API Service",
    description="Unified Speech-to-Text, Text-to-Speech, and Live WebSocket microservice.",
    version="2.0.0"
)

# Initialize the official Google GenAI Client
try:
    client = genai.Client()
except Exception as e:
    raise RuntimeError("Ensure GEMINI_API_KEY is configured in your environment.") from e

SUPPORTED_VOICES = {"puck", "charon", "aoede", "fenrir", "kore"}

class SynthesisRequest(BaseModel):
    text: str
    voice: str = "Puck"

# ----------------------------------------------------
# A. REST Endpoint: Speech-to-Text (Transcribe)
# ----------------------------------------------------
@app.post("/api/v1/transcribe")
async def transcribe_audio(file: UploadFile = File(..., description="Audio file (mp3, wav, m4a)")):
    """
    Accepts an audio file upload, transfers it to the Gemini File API,
    and returns a textual transcription generated natively by the model.
    """
    temp_dir = "./temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    temp_filepath = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Upload to Gemini File API
        uploaded_file = client.files.upload(file=temp_filepath)

        # Request transcription using Gemini 3.5 Flash
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                uploaded_file,
                "Provide an exact, verbatim transcription of this audio. "
                "Do not summarize. Do not add commentary."
            ]
        )

        # Clean up file from cloud storage
        client.files.delete(name=uploaded_file.name)

        return {
            "filename": file.filename,
            "transcription": response.text.strip()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

# ----------------------------------------------------
# B. REST Endpoint: Text-to-Speech (Synthesize)
# ----------------------------------------------------
@app.post("/api/v1/synthesize")
async def synthesize_speech(request: SynthesisRequest):
    """
    Accepts a text string and voice profile, requests Gemini to synthesize
    native audio data, and streams the resulting audio file back.
    """
    selected_voice = request.voice.lower()
    if selected_voice not in SUPPORTED_VOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported voice. Choose from: {list(SUPPORTED_VOICES)}"
        )

    api_voice_name = selected_voice.capitalize()

    try:
        # Configure Gemini generation for raw audio modality
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=api_voice_name
                    )
                )
            )
        )

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=request.text,
            config=config
        )

        # Extract binary audio data from response parts
        audio_data = None
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.inline_data:
                        audio_data = part.inline_data.data
                        break

        if not audio_data:
            raise HTTPException(status_code=502, detail="No inline audio data returned by model.")

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mp3",
            headers={"Content-Disposition": f"attachment; filename=synthesized.mp3"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")

# ----------------------------------------------------
# C. WebSocket: Real-Time Gemini Live API Proxy
# ----------------------------------------------------
@app.websocket("/api/v1/live")
async def live_audio_stream(websocket: WebSocket):
    """
    WebSocket endpoint that receives raw PCM audio from the client,
    proxies it to the Google Gemini Live API, and streams responses back.
    """
    await websocket.accept()
    print("🚀 Client WebSocket connected.")

    # API configuration parameters for Google Gemini Live WebSocket connection
    google_ws_url = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent"
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        await websocket.close(code=1008, reason="API Key configuration missing.")
        return

    # WebSocket connection loop to Google's Live API
    import websockets
    try:
        async with websockets.connect(f"{google_ws_url}?key={api_key}") as google_ws:
            print("🔗 Connected to Google Gemini Live API WebSocket.")

            # Send initial session setup configuration
            setup_message = {
                "setup": {
                    "model": "models/gemini-3.1-flash-live-preview",
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {"voice_name": "Puck"}
                            }
                        }
                    }
                }
            }
            await google_ws.send(json.dumps(setup_message))

            async def client_to_google():
                """Reads binary audio data from client and forwards to Google."""
                try:
                    while True:
                        data = await websocket.receive()
                        if "bytes" in data:
                            # Forward raw audio chunk
                            audio_chunk = {
                                "realtime_input": {
                                    "media_chunks": [{
                                        "mime_type": "audio/pcm",
                                        "data": data["bytes"]
                                    }]
                                }
                            }
                            await google_ws.send(json.dumps(audio_chunk))
                        elif "text" in data:
                            # Forward text text prompt
                            text_prompt = {
                                "client_content": {
                                    "turns": [{"role": "user", "parts": [{"text": data["text"]}]}],
                                    "turn_complete": True
                                }
                            }
                            await google_ws.send(json.dumps(text_prompt))
                except WebSocketDisconnect:
                    pass

            async def google_to_client():
                """Reads responses from Google and forwards audio back to client."""
                try:
                    async for message in google_ws:
                        response = json.loads(message)
                        # Extract audio data chunk
                        parts = response.get("serverContent", {}).get("modelTurn", {}).get("parts", [])
                        for part in parts:
                            if "inlineData" in part:
                                binary_audio = base64.b64decode(part["inlineData"]["data"])
                                await websocket.send_bytes(binary_audio)
                except Exception as e:
                    print(f"Error reading from Google: {e}")

            # Run loops concurrently
            await asyncio.gather(client_to_google(), google_to_client())

    except Exception as e:
        print(f"WebSocket execution error: {e}")
    finally:
        print("🛑 Client WebSocket closed.")
```

---

## 2. The Frontend Client Sandbox

To let your users interact with your Voice API in real-time, create a simple HTML client. Save the code below as `index.html`. It captures raw audio from the user's microphone using the browser's Media API, sends it over the WebSocket endpoint, and plays back the returned audio chunks.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Gemini Live Audio Sandbox</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; line-height: 1.6; }
        .control-panel { background: #f4f4f5; padding: 20px; border-radius: 8px; border: 1px solid #e4e4e7; }
        button { padding: 10px 20px; font-size: 16px; font-weight: bold; border-radius: 4px; border: none; cursor: pointer; }
        #start-btn { background: #10a37f; color: white; }
        #stop-btn { background: #ef4444; color: white; margin-left: 10px; }
        .status { margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <h2>🔷 Gemini Live Audio Sandbox</h2>
    <p>Click "Start Conversation" to connect to your FastAPI WebSocket and talk to Gemini Live.</p>
    
    <div class="control-panel">
        <button id="start-btn">Start Conversation</button>
        <button id="stop-btn" disabled>Stop</button>
        <div class="status">Status: <span id="status-text" style="color: #6b7280;">Disconnected</span></div>
    </div>

    <script>
        let ws;
        let audioContext;
        let mediaStream;
        let processor;

        const startBtn = document.getElementById("start-btn");
        const stopBtn = document.getElementById("stop-btn");
        const statusText = document.getElementById("status-text");

        startBtn.onclick = async () => {
            // 1. Establish WebSocket Connection
            ws = new WebSocket("ws://localhost:8000/api/v1/live");
            ws.binaryType = "arraybuffer";

            ws.onopen = () => {
                statusText.innerText = "Connected! Speak now.";
                statusText.style.color = "#10a37f";
                startBtn.disabled = true;
                stopBtn.disabled = false;
                startAudioCapture();
            };

            ws.onmessage = async (event) => {
                // Playback binary PCM audio received from WebSocket
                const audioBuffer = event.data;
                playPCMData(audioBuffer);
            };

            ws.onclose = () => {
                statusText.innerText = "Disconnected.";
                statusText.style.color = "#ef4444";
                resetControls();
            };
        };

        stopBtn.onclick = () => {
            if (ws) ws.close();
            if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
            if (processor) processor.disconnect();
        };

        async function startAudioCapture() {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
            
            const source = audioContext.createMediaStreamSource(mediaStream);
            processor = audioContext.createScriptProcessor(1024, 1, 1);

            source.connect(processor);
            processor.connect(audioContext.destination);

            processor.onaudioprocess = (e) => {
                const inputData = e.inputBuffer.getChannelData(0);
                // Convert 32-bit float audio to 16-bit PCM (expected format)
                const pcmData = convertFloat32To16BitPCM(inputData);
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(pcmData);
                }
            };
        }

        function playPCMData(buffer) {
            // Simple buffer queueing to play standard PCM audio chunks
            const float32Data = convert16BitPCMToFloat32(new Int16Array(buffer));
            const audioBuffer = audioContext.createBuffer(1, float32Data.length, 16000);
            audioBuffer.getChannelData(0).set(float32Data);
            
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContext.destination);
            source.start();
        }

        function convertFloat32To16BitPCM(buffer) {
            let l = buffer.length;
            let buf = new Int16Array(l);
            while (l--) {
                let s = Math.max(-1, Math.min(1, buffer[l]));
                buf[l] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            return buf.buffer;
        }

        function convert16BitPCMToFloat32(buffer) {
            let l = buffer.length;
            let buf = new Float32Array(l);
            while (l--) {
                buf[l] = buffer[l] / 0x8000;
            }
            return buf;
        }

        function resetControls() {
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    </script>
</body>
</html>
```

---

## 3. Production Best Practices for Audio APIs

To run this unified Voice AI microservice in production, follow these practices:

### A. Automatic File Cleanup
When utilizing REST endpoints (like `/api/v1/transcribe`), files are temporarily uploaded to your Google Cloud developer storage. Make sure to delete these files immediately after processing using the `client.files.delete()` command in Python. Leaving files in storage can lead to memory leaks and security issues.

### B. PCM vs. Compressed Audio Formats
For real-time streaming, use raw **16-kHz Mono 16-bit PCM** audio. It avoids the latency of compressing and decompressing audio on the fly, saving crucial milliseconds. For static uploads, standard compressed formats (such as MP3 or M4A) are fine.

### C. Voice Intonation and Custom Prompts
When using Gemini's native TTS endpoints, you can steer the speaker's tone, speed, and emotion by passing explicit guidelines in the user prompt. 
- *Example prompt:* `"Read the following text with a slow, calm, and reassuring tone: [Your text here]"`

---

## Conclusion

By eliminating the separate steps of traditional STT/TTS pipelines, Google Gemini's native audio capabilities reduce latency and preserve the emotional qualities of speech. With FastAPI and WebSockets, you can build a unified voice service that delivers real-time, bidirectional voice experiences.

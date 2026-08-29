# Local Models Guide — GASSI

Covers hardware requirements, model recommendations, installation steps,
and quality tradeoffs for running AI inference locally via Ollama.

---

## Why Local?

Local inference has zero per-call cost, works offline, and keeps game
screenshots off external servers. The tradeoff is quality — local models
at the 2B–7B scale produce shorter, less nuanced advice than Gemini or
Claude, and response time depends entirely on your hardware.

If you have a mid-range or better GPU (6 GB+ VRAM), local models are a
viable primary backend. On weak GPUs or CPU-only machines, the free cloud
providers (Groq, Together AI, HuggingFace) give much better quality with
no hardware requirement.

---

## Prerequisites

1. Download and install Ollama: **https://ollama.com/download**
2. Start the Ollama server (it runs in the background automatically after install)
3. Pull a model (see table below)
4. In GASSI Settings → AI Backend, select **Ollama [Local]**
5. Confirm the URL is `http://localhost:11434` (default)
6. Select your pulled model from the dropdown

---

## Model Recommendations by Hardware

### GTX 1660 Super / RTX 2060 / RX 5700 (6 GB VRAM)

| Model | Pull Command | VRAM | Type | Quality |
|---|---|---|---|---|
| **moondream2** ⭐ | `ollama pull moondream2` | ~1.8 GB | Vision | Good for placement, fast |
| llama3.2:3b | `ollama pull llama3.2:3b` | ~2.0 GB | Text only | Good for OCR advisor |
| qwen2.5vl:7b | `ollama pull qwen2.5vl:7b` | ~6.1 GB | Vision | Best local quality, tight fit |

**Recommended setup for 6 GB cards:**
- Use `moondream2` for F1 (screenshot) and F2 (placement)
- Use `llama3.2:3b` for F1 (OCR mode) — set Default input to OCR in Settings

`qwen2.5vl:7b` fits if nothing else is running, but leaves ~0 MB headroom.
The game itself also uses VRAM — if you get OOM errors, fall back to `moondream2`.

---

### RTX 3070 / RTX 3080 / RX 6800 XT (8–10 GB VRAM)

| Model | Pull Command | VRAM | Type | Quality |
|---|---|---|---|---|
| **qwen2.5vl:7b** ⭐ | `ollama pull qwen2.5vl:7b` | ~6.1 GB | Vision | Strong spatial reasoning |
| llama3.2-vision | `ollama pull llama3.2-vision` | ~8.5 GB | Vision | Good general purpose |
| llama3.1:8b | `ollama pull llama3.1:8b` | ~5.5 GB | Text only | High quality OCR reasoning |

---

### RTX 3090 / RTX 4080 / RX 7900 XT (16–24 GB VRAM)

| Model | Pull Command | VRAM | Type | Quality |
|---|---|---|---|---|
| **qwen2.5vl:32b** ⭐ | `ollama pull qwen2.5vl:32b` | ~20 GB | Vision | Near-cloud quality |
| llama3.2-vision:90b | `ollama pull llama3.2-vision:90b` | ~55 GB (Q4) | Vision | RAM offload needed |
| llama3.3:70b | `ollama pull llama3.3:70b` | ~43 GB (Q4) | Text only | Excellent reasoning |

---

### CPU-only / Low VRAM (< 6 GB)

Local inference is slow but possible via RAM offload. Expect 30–120 seconds per response.

| Model | Pull Command | RAM needed | Notes |
|---|---|---|---|
| moondream2 | `ollama pull moondream2` | ~4 GB RAM | Fastest CPU option |
| llama3.2:3b | `ollama pull llama3.2:3b` | ~4 GB RAM | Text only, reasonable speed |

**Recommendation:** Use Groq instead — free tier, vision support, response in <2 seconds.
See [Cloud Free Tier Providers](#cloud-free-tier-providers) below.

---

## Text-only vs Vision Models

GASSI has two advisor paths:

- **OCR path (F1, default)** — extracts HUD text locally, sends text to AI. Works with
  text-only models. Cheaper in tokens, faster, but misses visual context.
- **Screenshot path (F1 Shift toggle / automatic fallback)** — sends a HUD image. Requires
  a vision-capable model. Richer context, more accurate advice.
- **Placement path (F2)** — always sends an image. Requires a vision-capable model.

If you select a text-only model (e.g. `llama3.2:3b`) and trigger F2 placement or screenshot
mode, Ollama will return an error. GASSI surfaces this as a red status message. Either:
- Switch to OCR mode (`Shift+F1`)
- Pull and select a vision model

---

## Remote Ollama Server

GASSI supports pointing at a remote Ollama instance — useful if you have a powerful
workstation on your LAN running Ollama while gaming on a weaker machine.

In Settings → AI Backend → Ollama URL, change from `http://localhost:11434` to your
server's IP: e.g. `http://192.168.1.100:11434`.

Ensure the Ollama server is started with `OLLAMA_HOST=0.0.0.0` to accept LAN connections:

```bash
# On the server machine (Windows)
set OLLAMA_HOST=0.0.0.0
ollama serve

# On the server machine (Linux/macOS)
OLLAMA_HOST=0.0.0.0 ollama serve
```

---

## Quality Comparison: Local vs Cloud

The table below reflects typical GASSI advice quality for Timberborn colony management.

| Provider | Model | Speed | Spatial Reasoning | Formula Detail | Cost |
|---|---|---|---|---|---|
| Gemini | gemini-2.5-flash | 3–8 s | ★★★★★ | ★★★★★ | Paid |
| Claude | claude-sonnet-4-6 | 4–10 s | ★★★★★ | ★★★★★ | Paid |
| Groq | llama-3.2-11b-vision | 1–3 s | ★★★☆☆ | ★★★☆☆ | Free |
| Together | Qwen2.5-VL-7B | 3–8 s | ★★★★☆ | ★★★☆☆ | Free/Cheap |
| HuggingFace | Qwen2.5-VL-7B | 5–30 s | ★★★☆☆ | ★★★☆☆ | Free (limited) |
| Ollama local | moondream2 | 2–10 s* | ★★★☆☆ | ★★☆☆☆ | Free |
| Ollama local | qwen2.5vl:7b | 5–30 s* | ★★★★☆ | ★★★☆☆ | Free |

*Depends heavily on GPU. Times shown for GTX 1660 Super GPU inference.

**Advice:** use Gemini (free tier: 1500 req/day) or Groq for best results.
Local Ollama is ideal when offline or for privacy-sensitive use.

---

## Cloud Free Tier Providers

If local inference is too slow or produces poor quality, these require no hardware:

| Provider | Sign-up | Free Tier | Best Model for GASSI |
|---|---|---|---|
| **Groq** | https://console.groq.com | 14,400 req/day | `llama-3.2-11b-vision-preview` |
| **Together AI** | https://api.together.xyz | $1 credit on signup | `Qwen2.5-VL-7B-Instruct` |
| **HuggingFace** | https://huggingface.co/settings/tokens | Rate-limited | `Qwen/Qwen2.5-VL-7B-Instruct` |

In GASSI Settings, select the provider, enter the API key in the masked field (stored in OS
keyring, never written to disk), and pick a model from the dropdown.

---

## GPU Detection (Future)

Automatic GPU detection to suggest the best model is tracked in the vFuture backlog.
Currently, the Ollama model picker fetches whatever models you have already pulled via
`ollama pull`. Pull the model that matches your hardware tier above, then select it in
Settings.

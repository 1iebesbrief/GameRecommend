import io
import math
import random
import wave
from array import array

_MODEL_CACHE = {}
_TRANSFORMERS_CACHE = {}


def _get_model(model_name, device):
    try:
        from audiocraft.models import MusicGen
    except Exception as exc:
        return None, f"audiocraft_not_available: {exc}"

    cache_key = (model_name, device or "")
    if cache_key in _MODEL_CACHE:
        return _MODEL_CACHE[cache_key], None

    try:
        model = MusicGen.get_pretrained(model_name)
        if device:
            model = model.to(device)
    except Exception as exc:
        return None, f"model_load_failed: {exc}"

    _MODEL_CACHE[cache_key] = model
    return model, None


def _resolve_transformers_model_id(model_name):
    if "/" in model_name:
        return model_name

    model_map = {
        "small": "facebook/musicgen-small",
        "medium": "facebook/musicgen-medium",
        "large": "facebook/musicgen-large",
        "melody": "facebook/musicgen-melody",
    }
    return model_map.get(model_name, f"facebook/musicgen-{model_name}")


def _get_transformers_model(model_id, device):
    cache_key = (model_id, device or "")
    if cache_key in _TRANSFORMERS_CACHE:
        return _TRANSFORMERS_CACHE[cache_key], None

    try:
        from transformers import AutoProcessor, AutoModelForTextToAudio
    except Exception as exc:
        return None, f"transformers_not_available: {exc}"

    try:
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForTextToAudio.from_pretrained(model_id)
        if device:
            model = model.to(device)
    except Exception as exc:
        return None, f"model_load_failed: {exc}"

    _TRANSFORMERS_CACHE[cache_key] = (processor, model)
    return (processor, model), None


def _tensor_to_pcm16(tensor):
    try:
        import torch
    except Exception as exc:
        return None, None, f"torch_not_available: {exc}"

    if tensor.dim() != 2:
        return None, None, "invalid_tensor_shape"

    pcm = (tensor * 32767.0).clamp(-32768, 32767).short().cpu()
    channels, samples = pcm.shape
    if channels == 1:
        return array("h", pcm[0].tolist()).tobytes(), channels, None

    interleaved = array("h")
    for idx in range(samples):
        for channel in range(channels):
            interleaved.append(int(pcm[channel, idx]))
    return interleaved.tobytes(), channels, None


def _generate_with_audiocraft(prompt, duration, model_name, device):
    model, error = _get_model(model_name, device)
    if not model:
        return None, error

    try:
        import torch
    except Exception as exc:
        return None, f"torch_not_available: {exc}"

    try:
        model.set_generation_params(duration=duration)
        with torch.no_grad():
            wav = model.generate([prompt])
    except Exception as exc:
        return None, f"generation_failed: {exc}"

    if wav is None or not hasattr(wav, "dim"):
        return None, "empty_output"

    if wav.dim() == 3:
        wav = wav[0]
    elif wav.dim() != 2:
        return None, "unexpected_output_shape"

    pcm_bytes, channels, error = _tensor_to_pcm16(wav)
    if not pcm_bytes:
        return None, error or "pcm_conversion_failed"

    sample_rate = int(getattr(model, "sample_rate", 32000))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue(), None


def _iter_transformers_model_ids(model_name):
    primary = _resolve_transformers_model_id(model_name)
    yield primary
    if "musicgen" in primary:
        yield "facebook/audiogen-small"


def _generate_with_transformers(prompt, duration, model_name, device):
    try:
        import torch
    except Exception as exc:
        return None, f"torch_not_available: {exc}"

    if not device:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    last_error = None
    for model_id in _iter_transformers_model_ids(model_name):
        cached, error = _get_transformers_model(model_id, device)
        if not cached:
            last_error = error
            continue

        processor, model = cached
        try:
            inputs = processor(text=[prompt], padding=True, return_tensors="pt")
            inputs = {key: value.to(device) for key, value in inputs.items()}
        except Exception as exc:
            last_error = f"input_prep_failed: {exc}"
            continue

        frame_rate = getattr(getattr(model.config, "audio_encoder", None), "frame_rate", None)
        if not frame_rate:
            frame_rate = 50
        max_new_tokens = max(1, int(duration * frame_rate))

        try:
            with torch.no_grad():
                audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)
        except Exception as exc:
            last_error = f"generation_failed: {exc}"
            continue

        if audio_values is None or not hasattr(audio_values, "dim"):
            last_error = "empty_output"
            continue

        if audio_values.dim() == 3:
            audio_values = audio_values[0]
        elif audio_values.dim() == 2:
            audio_values = audio_values[0].unsqueeze(0)
        else:
            last_error = "unexpected_output_shape"
            continue

        pcm_bytes, channels, error = _tensor_to_pcm16(audio_values)
        if not pcm_bytes:
            last_error = error or "pcm_conversion_failed"
            continue

        sample_rate = int(
            getattr(getattr(model.config, "audio_encoder", None), "sampling_rate", 32000)
        )
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        return buffer.getvalue(), None

    return None, last_error or "model_load_failed"


def _generate_procedural_audio(prompt, duration, sample_rate=32000):
    try:
        import numpy as np
    except Exception as exc:
        np = None

    seed = abs(hash(prompt)) % (2**32)
    rng = random.Random(seed)
    base_notes = rng.sample([110.0, 130.81, 146.83, 164.81, 196.0, 220.0], k=3)

    if np is not None:
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        signal = np.zeros_like(t)
        for idx, freq in enumerate(base_notes):
            lfo = 0.5 * (1.0 + np.sin(2 * math.pi * (0.05 + 0.02 * idx) * t))
            signal += (0.15 / (idx + 1)) * np.sin(2 * math.pi * freq * t) * lfo

        noise = np.random.default_rng(seed).normal(0, 0.02, size=t.shape)
        noise = np.convolve(noise, np.ones(200) / 200, mode="same")
        signal += noise

        signal = np.clip(signal, -1.0, 1.0)
        left = signal
        right = np.roll(signal, int(0.01 * sample_rate))
        stereo = np.stack([left, right], axis=0)
        pcm = (stereo * 32767.0).astype(np.int16)
        interleaved = np.empty(pcm.shape[1] * 2, dtype=np.int16)
        interleaved[0::2] = pcm[0]
        interleaved[1::2] = pcm[1]
        pcm_bytes = interleaved.tobytes()
        channels = 2
    else:
        samples = int(sample_rate * duration)
        interleaved = array("h")
        lfo_rates = [0.05, 0.07, 0.09]
        for idx in range(samples):
            t = idx / sample_rate
            value = 0.0
            for tone_idx, freq in enumerate(base_notes):
                lfo = 0.5 * (1.0 + math.sin(2 * math.pi * lfo_rates[tone_idx] * t))
                value += (0.15 / (tone_idx + 1)) * math.sin(2 * math.pi * freq * t) * lfo
            value += rng.uniform(-0.02, 0.02)
            value = max(-1.0, min(1.0, value))
            sample = int(value * 32767.0)
            interleaved.append(sample)
            interleaved.append(sample)

        pcm_bytes = interleaved.tobytes()
        channels = 2

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue(), None


def generate_local_music(prompt, duration=8, model_name="small", device=None):
    try:
        duration = max(1, int(duration))
    except (TypeError, ValueError):
        duration = 8

    audio_bytes, error = _generate_with_audiocraft(prompt, duration, model_name, device)
    if audio_bytes:
        return audio_bytes, None

    fallback_bytes, fallback_error = _generate_with_transformers(
        prompt, duration, model_name, device
    )
    if fallback_bytes:
        return fallback_bytes, None
    procedural_bytes, procedural_error = _generate_procedural_audio(prompt, duration)
    if procedural_bytes:
        print("Local MusicGen fallback: procedural audio")
        return procedural_bytes, None

    if error and fallback_error and procedural_error:
        return None, f"{error}; {fallback_error}; {procedural_error}"
    return None, error or fallback_error or procedural_error or "no_backend_available"

"""
Speech Processing Module
- STT: OpenAI Whisper (large-v3 for best Korean accuracy)
- TTS: MeloTTS-Korean (self-hosted)

Both models are self-hosted for:
1. Privacy (audio data stays internal)
2. Cost efficiency (no API calls)
3. Low latency
"""

import io
import base64
import logging
import numpy as np
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    OpenAI Whisper large-v3 for Korean STT
    
    Why Whisper large-v3:
    - Best accuracy for Korean (WER ~4%)
    - Multi-language support
    - Handles accents and noise well
    - Apache 2.0 license
    """
    
    def __init__(self, model_size: str = "large-v3"):
        try:
            import torch
            from faster_whisper import WhisperModel
            
            # Use faster-whisper for better performance (CTranslate2 backend)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(f"Loading Whisper {model_size} on {device}...")
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root="/model_cache/whisper"
            )
            self.sample_rate = 16000
            logger.info("Whisper loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            self.model = None
    
    def transcribe(
        self,
        audio_base64: str,
        language: str = "ko"
    ) -> dict:
        """
        Transcribe audio to text
        
        Args:
            audio_base64: Base64 encoded audio (WAV or MP3)
            language: Target language code (ko for Korean)
        
        Returns:
            {
                "text": "전체 텍스트",
                "segments": [
                    {"start": 0.0, "end": 1.5, "text": "세그먼트1"},
                    ...
                ],
                "language": "ko",
                "confidence": 0.95
            }
        """
        if self.model is None:
            raise RuntimeError("Whisper model not loaded")
        
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_base64)
            audio_buffer = io.BytesIO(audio_bytes)
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_buffer,
                language=language,
                beam_size=5,
                vad_filter=True,  # Remove silence
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )
            
            # Process segments
            result_segments = []
            full_text = []
            total_confidence = 0.0
            
            for segment in segments:
                result_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
                full_text.append(segment.text.strip())
                total_confidence += segment.avg_logprob
            
            avg_confidence = np.exp(total_confidence / max(len(result_segments), 1))
            
            return {
                "text": " ".join(full_text),
                "segments": result_segments,
                "language": info.language,
                "confidence": float(avg_confidence)
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "text": "",
                "segments": [],
                "language": language,
                "confidence": 0.0,
                "error": str(e)
            }
    
    def transcribe_stream(self, audio_chunks: list) -> str:
        """
        Process audio stream for real-time transcription
        Useful for avatar conversation
        """
        combined_audio = b"".join(
            base64.b64decode(chunk) for chunk in audio_chunks
        )
        audio_base64 = base64.b64encode(combined_audio).decode()
        result = self.transcribe(audio_base64)
        return result.get("text", "")


class TextToSpeech:
    """
    CosyVoice2 for Korean Text-to-Speech
    
    Why CosyVoice2-0.5B (2025 benchmark):
    - Ultra-low latency: 150ms streaming
    - High-quality Korean voice synthesis
    - Supports Korean, Chinese, English, Japanese
    - Fine-grained emotion and dialect control
    - Open source (Apache 2.0)
    
    Fallback: edge-tts (Microsoft) if CosyVoice2 unavailable
    
    Previous: MeloTTS (replaced due to lower quality)
    """
    
    def __init__(self):
        self.model = None
        self.sample_rate = 22050
        self._use_edge_tts = False
        
        try:
            # Try CosyVoice2 first (best quality)
            from cosyvoice import CosyVoice
            
            logger.info("Loading CosyVoice2 Korean...")
            self.model = CosyVoice('CosyVoice-300M-SFT')
            self.model_type = "cosyvoice2"
            self.sample_rate = 22050
            logger.info("CosyVoice2 loaded successfully")
            
        except ImportError:
            logger.warning("CosyVoice2 not available, trying MeloTTS...")
            try:
                from melo.api import TTS
                
                self.model = TTS(language="KR", device="auto")
                self.model_type = "melo"
                self.sample_rate = 24000
                logger.info("MeloTTS loaded as fallback")
                
            except ImportError:
                logger.warning("MeloTTS not available, using edge-tts fallback")
                self.model = None
                self._use_edge_tts = True
        except Exception as e:
            logger.error(f"Failed to load TTS: {e}")
            self.model = None
            self._use_edge_tts = True
    
    def synthesize(
        self,
        text: str,
        speed: float = 1.0,
        emotion: str = "neutral"
    ) -> dict:
        """
        Convert text to speech
        
        Args:
            text: Korean text to synthesize
            speed: Speech speed (0.5 - 2.0)
            emotion: Emotion style (neutral, happy, sad, angry)
        
        Returns:
            {
                "audio": "base64_encoded_wav",
                "duration_seconds": 3.5,
                "sample_rate": 22050
            }
        """
        if self.model is None:
            if self._use_edge_tts:
                return self._synthesize_edge_tts(text, speed)
            raise RuntimeError("TTS model not loaded")
        
        try:
            import soundfile as sf
            
            if self.model_type == "cosyvoice2":
                return self._synthesize_cosyvoice2(text, speed, emotion)
            else:
                return self._synthesize_melo(text, speed)
            
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            # Try edge-tts as last resort
            if self._use_edge_tts or True:
                return self._synthesize_edge_tts(text, speed)
            return {
                "audio": "",
                "duration_seconds": 0,
                "sample_rate": self.sample_rate,
                "error": str(e)
            }
    
    def _synthesize_cosyvoice2(self, text: str, speed: float, emotion: str) -> dict:
        """Synthesize using CosyVoice2 (best quality)"""
        import soundfile as sf
        
        # Map emotion to CosyVoice2 style
        emotion_prompt = {
            "neutral": "",
            "happy": "기쁜 목소리로",
            "sad": "슬픈 목소리로",
            "angry": "화난 목소리로"
        }.get(emotion, "")
        
        prompt_text = f"{emotion_prompt} {text}" if emotion_prompt else text
        
        # Generate audio
        audio_output = self.model.inference_sft(prompt_text, 'Korean')
        audio_array = audio_output['tts_speech'].numpy()
        
        # Apply speed adjustment
        if speed != 1.0:
            import librosa
            audio_array = librosa.effects.time_stretch(audio_array, rate=speed)
        
        # Convert to base64
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_array, self.sample_rate, format='WAV')
        audio_base64 = base64.b64encode(audio_buffer.getvalue()).decode()
        
        duration = len(audio_array) / self.sample_rate
        
        return {
            "audio": audio_base64,
            "duration_seconds": duration,
            "sample_rate": self.sample_rate,
            "model": "cosyvoice2"
        }
    
    def _synthesize_melo(self, text: str, speed: float) -> dict:
        """Synthesize using MeloTTS (fallback)"""
        import soundfile as sf
        
        audio_array = self.model.tts_to_file(
            text=text,
            speaker_id="KR",
            speed=speed,
            output_path=None
        )
        
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_array, self.sample_rate, format='WAV')
        audio_base64 = base64.b64encode(audio_buffer.getvalue()).decode()
        
        duration = len(audio_array) / self.sample_rate
        
        return {
            "audio": audio_base64,
            "duration_seconds": duration,
            "sample_rate": self.sample_rate,
            "model": "melo"
        }
    
    def _synthesize_edge_tts(self, text: str, speed: float) -> dict:
        """Fallback using Microsoft Edge TTS (requires internet)"""
        import asyncio
        import edge_tts
        
        async def generate():
            voice = "ko-KR-SunHiNeural"  # Korean female voice
            rate_str = f"+{int((speed-1)*100)}%" if speed >= 1 else f"{int((speed-1)*100)}%"
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            return audio_data
        
        try:
            audio_data = asyncio.run(generate())
            audio_base64 = base64.b64encode(audio_data).decode()
            
            return {
                "audio": audio_base64,
                "duration_seconds": len(audio_data) / 48000,
                "sample_rate": 48000,
                "model": "edge-tts"
            }
        except Exception as e:
            return {"audio": "", "duration_seconds": 0, "error": str(e)}


class SpeechProcessor:
    """
    Combined Speech Processor for Avatar conversations
    
    Usage:
        processor = SpeechProcessor()
        
        # User speaks -> Text
        text = processor.speech_to_text(audio_base64)
        
        # AI response -> Audio
        audio = processor.text_to_speech("안녕하세요!")
    """
    
    def __init__(self, whisper_size: str = "large-v3"):
        self.stt = SpeechToText(model_size=whisper_size)
        self.tts = TextToSpeech()
    
    def speech_to_text(self, audio_base64: str, language: str = "ko") -> dict:
        """Convert user speech to text"""
        return self.stt.transcribe(audio_base64, language)
    
    def text_to_speech(
        self,
        text: str,
        speed: float = 1.0,
        emotion: str = "neutral"
    ) -> dict:
        """Convert AI response to speech"""
        return self.tts.synthesize(text, speed, emotion)
    
    def process_conversation_turn(
        self,
        user_audio_base64: str,
        response_generator: callable
    ) -> Tuple[str, dict]:
        """
        Process one turn of conversation
        
        Args:
            user_audio_base64: User's speech in base64
            response_generator: Function that takes text and returns AI response
        
        Returns:
            (user_text, ai_audio_response)
        """
        # STT: User audio -> text
        user_result = self.speech_to_text(user_audio_base64)
        user_text = user_result.get("text", "")
        
        if not user_text:
            return "", {
                "audio": "",
                "error": "Could not understand speech"
            }
        
        # Generate AI response
        ai_response_text = response_generator(user_text)
        
        # TTS: AI text -> audio
        ai_audio = self.text_to_speech(ai_response_text)
        ai_audio["text"] = ai_response_text
        
        return user_text, ai_audio

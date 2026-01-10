# Voice Integration Example

## Simple Integration into Questions Screen

Add these imports to your existing questions.tsx:

```typescript
// Add these imports
import { voiceAccessibilityService } from '../../services/voiceAccessibilityService';
import { VoiceButton, SpeakButton } from '../../components/VoiceButton';
import { VoiceSettingsComponent } from '../../components/VoiceSettings';
```

## Add Voice State (in your existing component)

```typescript
export default function QuestionsScreen() {
  // Your existing state...
  const [currentAnswer, setCurrentAnswer] = useState('');
  
  // Add voice state
  const [voiceEnabled, setVoiceEnabled] = useState(false);

  // Initialize voice service
  useEffect(() => {
    const initVoice = async () => {
      try {
        await voiceAccessibilityService.initialize();
        const isScreenReader = await AccessibilityInfo.isScreenReaderEnabled();
        if (isScreenReader) {
          setVoiceEnabled(true);
          voiceAccessibilityService.updateSettings({ enabled: true });
        }
      } catch (error) {
        console.log('Voice not available:', error);
      }
    };
    initVoice();
  }, []);

  // Auto-read questions when they change
  useEffect(() => {
    if (voiceEnabled && currentQuestion) {
      voiceAccessibilityService.readQuestion(currentQuestion.text);
    }
  }, [currentQuestion, voiceEnabled]);
}
```

## Add Voice Buttons to Your UI

```typescript
// In your existing render, add voice buttons:

<View style={styles.questionContainer}>
  {/* Your existing question text */}
  <Text style={styles.questionText}>{currentQuestion.text}</Text>
  
  {/* Add voice read button */}
  {voiceEnabled && (
    <SpeakButton 
      text={currentQuestion.text}
      disabled={false}
    />
  )}
</View>

{/* Your existing text input */}
<TextInput
  style={styles.textInput}
  value={currentAnswer}
  onChangeText={setCurrentAnswer}
  placeholder="답변을 입력하세요"
/>

{/* Add voice input button */}
{voiceEnabled && (
  <VoiceButton
    onTranscription={(text) => setCurrentAnswer(text)}
    disabled={false}
    placeholder="음성으로 답변하기"
  />
)}
```

## Add Settings Toggle

```typescript
// Add this somewhere in your screen (maybe in header or settings)
<TouchableOpacity 
  style={styles.voiceToggle}
  onPress={() => setVoiceEnabled(!voiceEnabled)}
>
  <Text>음성 기능 {voiceEnabled ? '끄기' : '켜기'}</Text>
</TouchableOpacity>

{/* Voice settings panel */}
{voiceEnabled && <VoiceSettingsComponent />}
```

## Backend Voice Transcription Endpoint

Add this to your FastAPI backend:

```python
# app/routers/voice.py
from fastapi import APIRouter, File, UploadFile
import openai
import tempfile
import os

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Transcribe with OpenAI Whisper
        with open(temp_file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file,
                language="ko"
            )

        # Clean up temp file
        os.unlink(temp_file_path)
        
        return {"text": transcript.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
```

## Package.json Dependencies

Add these to your package.json:

```json
{
  "expo-av": "~14.0.0",
  "expo-speech": "~12.0.0",
  "expo-file-system": "~17.0.0"
}
```

## Simple Usage Flow

1. User opens questions screen
2. If screen reader detected, voice mode auto-enables
3. Question is read aloud automatically
4. User can tap "읽기" to hear question again
5. User can tap "음성 입력" to speak their answer
6. Voice gets transcribed to text
7. User submits answer normally (your existing code)

**Clean, simple, non-breaking integration that helps blind users while keeping your current design intact.**
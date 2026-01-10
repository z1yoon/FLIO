# FLIO Accessibility Implementation Roadmap

## 🎯 **Non-Breaking Implementation Strategy**

This roadmap ensures **zero disruption** to existing code while adding powerful accessibility features.

---

## 📋 **Phase 1: Whisper Voice Input (2-3 weeks)**
*Additive only - no existing code changes*

### **1.1 Voice Input Service** 
**New file:** `/services/voiceInputService.ts`
```typescript
// Standalone service that integrates with existing aiQuestionService
class VoiceInputService {
  async transcribeAudio(audioUri: string): Promise<string>
  async startRecording(): Promise<string>
  async stopRecording(): Promise<string>
}
```

### **1.2 Voice-Enabled Components**
**Add optional voice buttons** to existing forms:

**Reshuffle Dialog Enhancement:**
- Add microphone button next to text input in `matches.tsx:140-143`
- Voice transcription fills existing `reshufflePreference` state
- **Zero changes** to existing handleReshuffle logic

**Question Answering Enhancement:**
- Add voice button to text answer fields
- Transcribed text populates existing answer inputs
- **Zero changes** to existing submitAnswer flow

### **1.3 Dependencies to Add**
```json
// package.json additions only
{
  "expo-av": "~14.0.0",
  "expo-file-system": "~17.0.0", 
  "@react-native-async-storage/async-storage": "~1.23.0"
}
```

### **1.4 Backend Integration**
**New endpoint:** `/api/v1/voice/transcribe`
- Uses OpenAI Whisper API
- **No changes** to existing AI question endpoints
- Parallel service to current text processing

---

## 📋 **Phase 2: Basic Screen Reader Support (1 week)**
*Additive accessibility props only*

### **2.1 Accessibility Props Addition**
**Add to existing components without changing logic:**

**Matches Screen (`matches.tsx`):**
```typescript
// Add these props to existing TouchableOpacity components
accessibilityLabel="좋아요 버튼"
accessibilityHint="이 분에게 좋아요를 보냅니다"
accessibilityRole="button"
```

**Questions Screen:**
```typescript
// Add to existing form inputs
accessibilityLabel="질문 답변"
accessibilityHint="음성으로도 답변할 수 있습니다"
```

### **2.2 Dynamic Announcements**
**New utility:** `/utils/accessibilityAnnouncer.ts`
```typescript
// Announces loading states and results
const announceMatchResults = (count: number) => {
  AccessibilityInfo.announceForAccessibility(
    `${count}명의 매칭 결과를 찾았습니다`
  );
};
```

---

## 📋 **Phase 3: Enhanced Voice Features (2 weeks)**
*Build on Phase 1 foundation*

### **3.1 Voice Commands**
**New service:** `/services/voiceCommandService.ts`
```typescript
// Voice commands for match actions
const voiceCommands = {
  "좋아요": () => handleLikeMatch(currentMatch),
  "패스": () => handlePassMatch(currentMatch),
  "설명 들어": () => speakMatchExplanation()
};
```

### **3.2 AI Explanation Audio**
**Enhance existing explanation modal:**
- Add "듣기" button to match explanation modal
- Use existing `expo-speech` (already installed)
- **No changes** to explanation fetching logic

---

## 📋 **Phase 4: Advanced Features (3-4 weeks)**
*Optional enhancements*

### **4.1 Voice Profile Creation**
- Voice introductions alongside text answers
- Audio compatibility summaries
- Voice-guided onboarding

### **4.2 Smart Voice Shortcuts**
- Voice search: "키가 큰 사람 찾아줘"
- Voice preferences: "운동 좋아하는 사람들로 다시 매칭해줘"
- Voice navigation: "프로필 보기", "다음 매칭"

---

## 🛠 **Implementation Order**

### **Week 1-2: Quick Wins**
1. **Voice input for reshuffle preference** (matches.tsx:141)
   - Add microphone icon button
   - Transcribe to existing text input
   - **Impact:** Immediate accessibility improvement

2. **Voice input for question answers**
   - Add to text answer fields only
   - Keep multiple choice as-is initially

### **Week 3: Polish**
3. **Basic accessibility labels**
   - Add to all TouchableOpacity components
   - Add to TextInput components
   - Add loading announcements

### **Week 4: Voice Commands**
4. **Match action voice commands**
   - "좋아요", "패스", "설명 들어"
   - Uses existing handler functions

---

## 🔧 **Technical Implementation**

### **Non-Breaking Architecture**
```
Current Code (unchanged)
├── matches.tsx (add voice button only)
├── aiQuestionService.ts (unchanged)
└── existing handlers (unchanged)

New Accessibility Layer
├── voiceInputService.ts
├── voiceCommandService.ts  
├── accessibilityAnnouncer.ts
└── voiceButton component
```

### **Integration Pattern**
```typescript
// Existing code stays the same:
const handleReshuffle = async () => {
  // ... existing logic unchanged
};

// New voice feature adds to it:
const handleVoiceInput = async () => {
  const transcribed = await voiceInputService.transcribe();
  setReshufflePreference(transcribed); // Uses existing state
  // Existing handleReshuffle() works as-is
};
```

---

## 🎯 **Success Metrics**

### **Phase 1 Success:**
- ✅ Voice input works in reshuffle dialog
- ✅ Voice input works for text questions  
- ✅ Zero existing functionality broken
- ✅ Korean language transcription working

### **Phase 2 Success:**
- ✅ Screen readers announce all buttons and inputs
- ✅ Match results properly announced
- ✅ Loading states communicated to users

### **Phase 3 Success:**
- ✅ Voice commands control match actions
- ✅ AI explanations can be spoken aloud
- ✅ Voice shortcuts working

---

## 💝 **Benefits Without Disruption**

1. **Current users:** Zero impact, everything works exactly the same
2. **Accessibility users:** Major improvements in usability
3. **All users:** Optional voice features enhance convenience
4. **Development:** Incremental, low-risk implementation
5. **Maintenance:** New features are isolated and testable

**This approach lets you implement powerful accessibility features while preserving your current workflow and design that you love!**
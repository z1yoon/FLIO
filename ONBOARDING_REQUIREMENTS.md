# FLIO Onboarding Requirements

## MANDATORY VERIFICATION FOR ACCOUNT CREATION

### ⚠️ CRITICAL: Two Verifications Required Before App Access

Users **MUST** complete both verifications to finish onboarding:

1. **📱 Phone Verification** (REQUIRED)
   - SMS verification code sent to phone number
   - Validates real Korean phone number
   - One phone number per account
   - Must be completed during signup

2. **📸 Photo Verification** (REQUIRED)
   - Live selfie with challenge pose
   - Face liveness detection (not a photo-of-photo)
   - Face matching with profile photos
   - Must be completed before accessing matches
   - Required for baseline security

### Onboarding Flow

```
1. Create Account (Email/Password)
   ↓
2. Basic Profile (Name, Gender, Birth Date) ✅
   ↓
3. 📱 Phone Verification ← REQUIRED (Cannot skip)
   ↓
4. Extended Profile (Height, Education, etc.) ✅
   ↓
5. 📸 Photo Verification ← REQUIRED (Cannot skip)
   ↓
6. Answer 40 Questions ✅
   ↓
7. Complete Onboarding ✅
   ↓
8. Access App & Start Matching
```

### Why Both Are Required

**Phone Verification:**
- Prevents multi-account abuse
- Validates real Korean user
- Enables account recovery
- Required by Korean regulations

**Photo Verification:**
- Prevents fake profiles
- Ensures profile photos match real person
- Baseline security for all users
- 20% weight in trust score
- Required for matching access

### Database Implementation

#### Phone Verification Check
```sql
-- Check if user completed phone verification
SELECT is_verified
FROM phone_verifications
WHERE user_id = ? AND is_verified = true;
```

#### Photo Verification Check
```sql
-- Check if user completed photo verification
SELECT photo_verified, photo_verified_at
FROM profiles
WHERE user_id = ? AND photo_verified = true;
```

#### Can Access App Check
```sql
-- Combined check: phone AND photo verified
SELECT
    (SELECT COUNT(*) FROM phone_verifications
     WHERE user_id = ? AND is_verified = true) > 0 AS phone_verified,
    photo_verified,
    (photo_verified AND
     EXISTS(SELECT 1 FROM phone_verifications
            WHERE user_id = ? AND is_verified = true)) AS can_access_app
FROM profiles
WHERE user_id = ?;
```

### Backend Implementation

#### FastAPI Middleware
```python
async def check_onboarding_complete(user_id: str) -> dict:
    """
    Check if user completed mandatory onboarding verifications
    Returns: {
        'phone_verified': bool,
        'photo_verified': bool,
        'can_access_app': bool,
        'missing_steps': list
    }
    """
    phone_verified = await check_phone_verification(user_id)
    photo_verified = await check_photo_verification(user_id)

    missing_steps = []
    if not phone_verified:
        missing_steps.append('phone_verification')
    if not photo_verified:
        missing_steps.append('photo_verification')

    return {
        'phone_verified': phone_verified,
        'photo_verified': photo_verified,
        'can_access_app': phone_verified and photo_verified,
        'missing_steps': missing_steps
    }
```

### Frontend Implementation

#### React Native Onboarding Guard
```typescript
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { supabase } from '@/services/supabase/client';

export function useOnboardingGuard() {
  const router = useRouter();
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkOnboarding();
  }, []);

  async function checkOnboarding() {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        router.replace('/(auth)/login');
        return;
      }

      // Check phone verification
      const { data: phoneData } = await supabase
        .from('phone_verifications')
        .select('is_verified')
        .eq('user_id', user.id)
        .eq('is_verified', true)
        .single();

      // Check photo verification
      const { data: profileData } = await supabase
        .from('profiles')
        .select('photo_verified')
        .eq('user_id', user.id)
        .single();

      const phoneVerified = !!phoneData;
      const photoVerified = profileData?.photo_verified || false;

      if (!phoneVerified) {
        router.replace('/(onboarding)/phone-verification');
        return;
      }

      if (!photoVerified) {
        router.replace('/(onboarding)/face-verification');
        return;
      }

      setOnboardingComplete(true);
    } catch (error) {
      console.error('Onboarding check failed:', error);
      router.replace('/(auth)/login');
    } finally {
      setLoading(false);
    }
  }

  return { onboardingComplete, loading };
}
```

### User Experience

#### Blocked Access Message
When users try to access app without completing verification:

**Phone Not Verified:**
```
🚫 전화번호 인증 필요

FLIO를 이용하려면 전화번호 인증이 필요합니다.
한국 휴대폰 번호로 인증해주세요.

[전화번호 인증하기]
```

**Photo Not Verified:**
```
🚫 사진 인증 필요

매칭 기능을 사용하려면 얼굴 인증이 필요합니다.
프로필 사진과 일치하는지 확인합니다.

[얼굴 인증하기]
```

### API Endpoints

#### Check Onboarding Status
```
GET /api/onboarding/status/{user_id}

Response:
{
  "phone_verified": true,
  "photo_verified": false,
  "can_access_app": false,
  "missing_steps": ["photo_verification"],
  "next_step": {
    "name": "photo_verification",
    "title": "얼굴 인증",
    "description": "프로필 사진과 얼굴이 일치하는지 확인합니다",
    "required": true
  }
}
```

#### Complete Verification Step
```
POST /api/onboarding/complete/{step}

Body:
{
  "user_id": "uuid",
  "verification_data": {...}
}

Response:
{
  "success": true,
  "step_completed": "phone_verification",
  "remaining_steps": ["photo_verification"],
  "can_access_app": false
}
```

### Migration Changes

The following migrations enforce these requirements:

**001_core_schema.sql:**
- `profiles.photo_verified` - Boolean flag (default: false)
- `profiles.photo_verified_at` - Timestamp when completed

**004_verification_system.sql:**
- `phone_verifications` table - Stores phone verification records
- `photo_verifications` table - Stores photo verification records

**005_trust_score_system.sql:**
- `can_user_access_matches()` function - Checks photo verification
- Blocks match access if not photo verified

### Testing Checklist

- [ ] Cannot access matches without phone verification
- [ ] Cannot access matches without photo verification
- [ ] Onboarding flow redirects to missing steps
- [ ] API endpoints return correct verification status
- [ ] Database functions enforce verification requirements
- [ ] User sees clear messages when blocked
- [ ] Can complete verifications and access app

### Security Benefits

1. **Prevents Fake Accounts**: Phone verification validates real users
2. **Prevents Catfishing**: Photo verification ensures profile photos are real
3. **Baseline Trust**: All users start with verified identity
4. **Reduces Scams**: Harder to create multiple fake accounts
5. **Better Matches**: Users know they're talking to verified people

### Compliance

- ✅ Korean Phone Number Validation (통신사 인증)
- ✅ Live Face Verification (실명 확인)
- ✅ Data Privacy (개인정보 보호)
- ✅ GDPR Compliant (EU users)

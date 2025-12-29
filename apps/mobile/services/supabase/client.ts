import { createClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';
import 'react-native-url-polyfill/auto';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY!;

// Custom storage adapter for Expo SecureStore
const ExpoSecureStoreAdapter = {
  getItem: async (key: string) => {
    return SecureStore.getItemAsync(key);
  },
  setItem: async (key: string, value: string) => {
    await SecureStore.setItemAsync(key, value);
  },
  removeItem: async (key: string) => {
    await SecureStore.deleteItemAsync(key);
  },
};

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: ExpoSecureStoreAdapter,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

// Database types
export interface Profile {
  id: string;
  user_id: string;
  nickname: string;
  birth_date: string;
  gender: 'male' | 'female' | 'other';
  bio: string | null;
  photos: string[];
  answers: Record<string, string>;
  profile_embedding: number[] | null;
  face_embedding: number[] | null;
  face_verified: boolean;
  height_cm: number | null;
  height_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface Verification {
  id: string;
  user_id: string;
  type: 'face' | 'height' | 'education' | 'job' | 'income';
  status: 'pending' | 'verified' | 'rejected';
  data: Record<string, any>;
  verified_at: string | null;
  created_at: string;
}

export interface Match {
  id: string;
  user_a_id: string;
  user_b_id: string;
  score: number;
  explanation: string | null;
  user_a_liked: boolean | null;
  user_b_liked: boolean | null;
  matched_at: string | null;
  created_at: string;
}

export interface Message {
  id: string;
  match_id: string;
  sender_id: string;
  content: string;
  encrypted: boolean;
  read_at: string | null;
  created_at: string;
}

export default supabase;

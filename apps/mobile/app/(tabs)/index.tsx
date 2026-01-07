import { useEffect } from 'react';
import { router } from 'expo-router';

/**
 * Tabs index - redirects to matches tab by default
 */
export default function TabsIndex() {
  useEffect(() => {
    // Redirect to matches tab
    router.replace('/(tabs)/matches');
  }, []);

  return null;
}

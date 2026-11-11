import '@/lib/background' // defines the background task in global scope (required by expo-task-manager)
import { Stack } from 'expo-router'
import * as SplashScreen from 'expo-splash-screen'
import { StatusBar } from 'expo-status-bar'
import { useEffect } from 'react'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { SessionProvider, useSession } from '@/lib/session'
import { C } from '@/lib/theme'

SplashScreen.preventAutoHideAsync().catch(() => {})

function Root() {
  const { status } = useSession()
  useEffect(() => { if (status !== 'loading') SplashScreen.hideAsync().catch(() => {}) }, [status])
  if (status === 'loading') return null
  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.page } }}>
        <Stack.Screen name="entry/[id]" options={{ headerShown: true, title: 'Entry', headerTintColor: C.navy700, headerStyle: { backgroundColor: C.white } }} />
      </Stack>
    </>
  )
}

export default function Layout() {
  return (
    <SafeAreaProvider>
      <SessionProvider>
        <Root />
      </SessionProvider>
    </SafeAreaProvider>
  )
}

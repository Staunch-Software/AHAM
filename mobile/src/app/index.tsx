import { Redirect } from 'expo-router'
import { useSession } from '@/lib/session'

export default function Index() {
  const { status, me } = useSession()
  if (status !== 'signedIn' || !me) return <Redirect href="/login" />
  if (me.must_change_password) return <Redirect href="/change-password" />
  return <Redirect href="/home" />
}

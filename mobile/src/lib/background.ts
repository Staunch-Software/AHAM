import * as BackgroundTask from 'expo-background-task'
import * as TaskManager from 'expo-task-manager'
import { kvGet } from './db'
import type { Me } from './session'
import { runSync } from './sync'

/**
 * Background delivery (Android WorkManager, at most every 15 minutes, when the system allows). Opening the app, the
 * network coming back and the minute timer are the main triggers; this only helps when the app stays closed.
 */
const TASK = 'sankalp-background-sync'

TaskManager.defineTask(TASK, async () => {
  try {
    const me = await kvGet<Me>('me')
    if (me) await runSync(me.id)
    return BackgroundTask.BackgroundTaskResult.Success
  } catch {
    return BackgroundTask.BackgroundTaskResult.Failed
  }
})

export async function registerBackgroundSync() {
  try {
    if (!(await TaskManager.isTaskRegisteredAsync(TASK))) await BackgroundTask.registerTaskAsync(TASK, { minimumInterval: 15 })
  } catch { /* not available (e.g. web): foreground sync still runs */ }
}

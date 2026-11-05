import 'package:flutter/foundation.dart' show debugPrint;
import 'package:workmanager/workmanager.dart';

import '../../core/api_client.dart';
import '../../core/session.dart';
import '../../database/database.dart';
import 'dio_sync_api.dart';
import 'drift_sync_store.dart';
import 'sync_engine.dart';

SyncEngine buildEngine(AppDatabase db, ApiClient api, SessionStore session) => SyncEngine(
      store: DriftSyncStore(db),
      api: DioSyncApi(api),
      userId: () => session.userId,
    );

const backgroundSyncTask = 'fieldsync.background_sync';

/// Entry point for OS-scheduled background work. The OS decides when (and whether) this runs —
/// Android batches periodic work (>= 15 min), iOS runs it opportunistically — so foreground
/// triggers (start, login, connectivity, resume, manual) remain the primary path.
@pragma('vm:entry-point')
void backgroundDispatcher() {
  Workmanager().executeTask((task, input) async {
    final db = AppDatabase.open();
    try {
      final session = SessionStore();
      await buildEngine(db, ApiClient(session), session).run();
      // Signed out (or session expired) means there is nothing a retry could fix: report success so the OS
      // does not keep rescheduling with backoff. The engine keeps its own per-submission retry schedule.
      return true;
    } catch (e, st) {
      debugPrint('background sync failed: $e\n$st');
      return false; // unexpected error: ask the OS to retry later
    } finally {
      await db.close();
    }
  });
}

Future<void> registerBackgroundSync() async {
  await Workmanager().initialize(backgroundDispatcher);
  await Workmanager().registerPeriodicTask(
    backgroundSyncTask,
    backgroundSyncTask,
    frequency: const Duration(minutes: 15),
    constraints: Constraints(networkType: NetworkType.connected),
    existingWorkPolicy: ExistingPeriodicWorkPolicy.keep,
  );
}

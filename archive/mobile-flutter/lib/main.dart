import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'app/providers.dart';
import 'database/database.dart';
import 'features/synchronization/sync_wiring.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final db = AppDatabase.open();
  if (Platform.isAndroid || Platform.isIOS) {
    // OS-scheduled sync is a bonus; failures to register must never stop the app.
    registerBackgroundSync().catchError((_) {});
  }
  runApp(ProviderScope(
    overrides: [databaseProvider.overrideWithValue(db)],
    child: const FieldSyncApp(),
  ));
}

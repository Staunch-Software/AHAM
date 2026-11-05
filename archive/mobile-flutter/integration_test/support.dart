// ignore_for_file: avoid_print
// Helpers shared by the emulator end-to-end scenarios: boot/shutdown the app, wait for things, drive the form, and a
// fake image picker (the OS camera UI cannot be automated) that returns a real JPEG.
import 'dart:convert';
import 'dart:io';

import 'package:fieldsync_mobile/app/app.dart';
import 'package:fieldsync_mobile/app/providers.dart';
import 'package:fieldsync_mobile/core/config.dart';
import 'package:fieldsync_mobile/database/database.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker_platform_interface/image_picker_platform_interface.dart';
import 'package:path_provider/path_provider.dart';

// 64x48 JPEG generated with Pillow.
const jpegB64 =
    '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/2wBDAQoLCw4NDhwQEBw7KCIoOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozv/wAARCAAwAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwCWiiivkT6YKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigD/2Q==';

class FakePicker extends ImagePickerPlatform {
  @override
  Future<XFile?> getImageFromSource({required ImageSource source, ImagePickerOptions options = const ImagePickerOptions()}) async {
    final f = File('${(await getTemporaryDirectory()).path}/e2e_${DateTime.now().microsecondsSinceEpoch}.jpg');
    await f.writeAsBytes(base64Decode(jpegB64));
    return XFile(f.path);
  }
}

void mark(String m) => print('E2E:$m');

Future<bool> apiReachable() async {
  final c = HttpClient()..connectionTimeout = const Duration(seconds: 2);
  try {
    final r = await (await c.getUrl(Uri.parse('${AppConfig.apiBaseUrl}/ready'))).close().timeout(const Duration(seconds: 3));
    await r.drain<void>();
    return r.statusCode == 200;
  } catch (_) {
    return false;
  } finally {
    c.close(force: true);
  }
}

bool has(Finder f) => f.evaluate().isNotEmpty;

Future<void> pumpUntil(WidgetTester t, bool Function() cond, {Duration timeout = const Duration(seconds: 60), required String what}) async {
  final end = DateTime.now().add(timeout);
  while (!cond()) {
    if (DateTime.now().isAfter(end)) fail('Timed out waiting for: $what');
    await t.pump(const Duration(milliseconds: 100));
    await Future<void>.delayed(const Duration(milliseconds: 100));
  }
}

Future<void> waitForReal(WidgetTester t, Future<bool> Function() cond, {required Duration timeout, required String what}) async {
  final end = DateTime.now().add(timeout);
  while (!await cond()) {
    if (DateTime.now().isAfter(end)) fail('Timed out waiting for: $what');
    await t.pump(const Duration(milliseconds: 100));
    await Future<void>.delayed(const Duration(seconds: 1));
  }
}

Future<AppDatabase> boot(WidgetTester t) async {
  final db = AppDatabase.open();
  await t.pumpWidget(ProviderScope(overrides: [databaseProvider.overrideWithValue(db)], child: const FieldSyncApp()));
  return db;
}

Future<void> shutdown(WidgetTester t, AppDatabase db) async {
  await t.pumpWidget(const SizedBox()); // disposes providers, timers and listeners ("app closed")
  await t.pump(const Duration(milliseconds: 300));
  await db.close();
}

/// Brings a widget into view even if the lazy ListView has not built it yet.
Future<void> reveal(WidgetTester t, Finder f) async {
  if (!has(f)) {
    await t.scrollUntilVisible(f, 200, scrollable: find.byType(Scrollable).first, maxScrolls: 30);
  }
  // Centre it: ensureVisible alone can leave the target at the top edge, under the app bar.
  await Scrollable.ensureVisible(t.element(f), alignment: 0.5);
  await t.pump(const Duration(milliseconds: 400));
}

Future<void> hideKeyboard(WidgetTester t) async {
  FocusManager.instance.primaryFocus?.unfocus();
  await SystemChannels.textInput.invokeMethod<void>('TextInput.hide');
  await t.pump(const Duration(milliseconds: 500));
}

/// Taps the button/inkwell that contains [f] (not just the text), after hiding the keyboard and centring it.
Future<void> tapText(WidgetTester t, Finder f) async {
  await hideKeyboard(t);
  await reveal(t, f);
  final ancestors = find.ancestor(of: f, matching: find.byWidgetPredicate((w) => w is ButtonStyleButton || w is InkWell));
  final target = ancestors.evaluate().isNotEmpty ? ancestors.first : f;
  final rect = t.getRect(target);
  final view = t.view;
  print('E2E:TAP ${f.describeMatch(Plurality.one)} rect=$rect screen=${view.physicalSize / view.devicePixelRatio} insets=${view.viewInsets.bottom / view.devicePixelRatio}');
  await t.tap(target);
  await t.pump(const Duration(milliseconds: 300));
}

Future<void> fill(WidgetTester t, String label, String text) async {
  final f = find.widgetWithText(TextFormField, label);
  await reveal(t, f);
  await t.enterText(f, text);
  await t.pump(const Duration(milliseconds: 600)); // autosave debounce
}


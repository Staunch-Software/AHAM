// ignore_for_file: avoid_print
// Scenario B (offline end to end) on a real emulator/device against a real backend.
//
// Drives the real UI, real SQLite, real network and the real sync engine. Only the system camera app is
// replaced by a fake image picker that returns a real JPEG (the OS camera UI cannot be automated).
// The test cooperates with a host-side driver (see docs/mobile-setup.md) that toggles connectivity and the
// emulated GPS position when it sees the `E2E:` markers in the log.
//
//   flutter test integration_test/offline_scenario_test.dart -d emulator-5554 \
//     --dart-define=E2E_EMAIL=agent@fieldsync-demo.com --dart-define=E2E_PASSWORD=... \
//     --dart-define=API_BASE_URL=http://10.0.2.2:8000
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker_platform_interface/image_picker_platform_interface.dart';
import 'package:integration_test/integration_test.dart';

import 'support.dart';

const _email = String.fromEnvironment('E2E_EMAIL');
const _password = String.fromEnvironment('E2E_PASSWORD');
void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  testWidgets('Scenario B: offline report with photo survives restart and syncs automatically', (t) async {
    expect(_email, isNotEmpty, reason: 'pass --dart-define=E2E_EMAIL / E2E_PASSWORD');
    ImagePickerPlatform.instance = FakePicker();
    var db = await boot(t);

    mark('READY_FOR_GRANT'); // host grants camera/location permissions and sets GPS position A
    await Future<void>.delayed(const Duration(seconds: 12));
    await t.pump();

    // --- sign in (needs network once) and download the form ---
    await pumpUntil(t, () => has(find.widgetWithText(TextFormField, 'Email')), what: 'login screen');
    await t.enterText(find.widgetWithText(TextFormField, 'Email'), _email);
    await t.enterText(find.widgetWithText(TextFormField, 'Password'), _password);
    await t.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await pumpUntil(t, () => has(find.text('Pending sync')), what: 'dashboard after login', timeout: const Duration(seconds: 30));
    mark('LOGGED_IN');
    await Future<void>.delayed(const Duration(seconds: 3)); // the host driver may capture the Home screen here
    await tapText(t, find.text('Forms'));
    await pumpUntil(t, () => has(find.text('New report')), what: 'form downloaded (New report button)', timeout: const Duration(seconds: 30));
    expect((await db.select(db.cachedForms).get()).isNotEmpty, isTrue, reason: 'schema cached for offline use');

    // --- go offline (host disables wifi + data) ---
    mark('WAIT_OFFLINE');
    await waitForReal(t, () async => !await apiReachable(), timeout: const Duration(minutes: 3), what: 'device to go offline');
    mark('OFFLINE_CONFIRMED');
    await Future<void>.delayed(const Duration(seconds: 3));

    // --- fill the report offline ---
    await tapText(t, find.text('New report'));
    await pumpUntil(t, () => has(find.byType(DropdownButtonFormField<String>)), what: 'form screen');
    mark('FORM_OPEN'); // the host driver may capture a screenshot here
    await Future<void>.delayed(const Duration(seconds: 3));
    // type of person comes from the managed list; the date is pre-filled with today
    await t.tap(find.byType(DropdownButtonFormField<String>).first);
    await t.pump(const Duration(milliseconds: 500));
    await t.tap(find.text('Dealer').last);
    await t.pump(const Duration(milliseconds: 500));
    await fill(t, 'Name of the person met *', 'Offline Ravi');
    await fill(t, 'Short description of the meeting *', 'Filled in with no connectivity');

    // --- photo at location A / time T1 ---
    await tapText(t, find.text('Take photo'));
    await pumpUntil(t, () => has(find.text('Add another photo')), what: 'photo captured', timeout: const Duration(seconds: 30));
    final photoRows = await db.select(db.localPhotos).get();
    expect(photoRows.length, 1);
    mark('PHOTO_TAKEN'); // host moves the emulated GPS to position B during this pause
    await Future<void>.delayed(const Duration(seconds: 15));

    // --- submit at location B / time T2 ---
    await tapText(t, find.widgetWithText(FilledButton, 'Submit'));
    await pumpUntil(t, () => has(find.text('Submissions')), what: 'history screen after submit', timeout: const Duration(seconds: 40));
    expect(has(find.textContaining('Field Meeting Report')), isTrue);
    mark('SUBMITTED_OFFLINE');

    var subs = await db.select(db.localSubmissions).get();
    expect(subs.length, 1);
    var s = subs.single;
    expect(s.state, isNot('accepted'), reason: 'must not claim server acceptance while offline');
    expect(s.serverId, isNull);
    expect(await db.select(db.drafts).get(), isEmpty, reason: 'draft consumed by the submit transaction');
    final photo = (await db.select(db.localPhotos).get()).single;
    expect(photo.submissionLocalId, s.localId);
    expect(photo.uploadState, 'pending');
    expect(File(photo.filePath).existsSync(), isTrue);
    print('E2E:DATA photo(lat=${photo.latitude},lon=${photo.longitude},status=${photo.locationStatus},capturedAt=${photo.capturedAtDevice.toIso8601String()}) '
        'submission(lat=${s.subLatitude},lon=${s.subLongitude},status=${s.subLocationStatus},submittedAt=${s.submittedAtDevice.toIso8601String()},state=${s.state})');
    expect(photo.capturedAtDevice.isBefore(s.submittedAtDevice), isTrue, reason: 'photo time precedes submit time');

    // --- close and reopen the app (still offline) ---
    await shutdown(t, db);
    db = await boot(t);
    await pumpUntil(t, () => has(find.text('Pending sync')), what: 'dashboard after restart (offline session restore)', timeout: const Duration(seconds: 30));
    subs = await db.select(db.localSubmissions).get();
    expect(subs.length, 1, reason: 'submission survived restart');
    expect(File((await db.select(db.localPhotos).get()).single.filePath).existsSync(), isTrue, reason: 'photo survived restart');
    await tapText(t, find.text('History'));
    await pumpUntil(t, () => has(find.textContaining('Field Meeting Report')), what: 'history after restart');
    expect(has(find.descendant(of: find.byType(ListTile), matching: find.textContaining('Accepted by server'))), isFalse);
    mark('RESTARTED_STILL_OFFLINE');

    // --- connectivity returns; sync must start by itself ---
    mark('WAIT_ONLINE');
    await waitForReal(t, apiReachable, timeout: const Duration(minutes: 5), what: 'device to come back online');
    final back = DateTime.now();
    mark('ONLINE_CONFIRMED');
    await pumpUntil(t, () => has(find.descendant(of: find.byType(ListTile), matching: find.textContaining('Accepted by server'))), what: 'automatic sync to accepted (history tile)', timeout: const Duration(minutes: 3));
    final secs = DateTime.now().difference(back).inSeconds;
    s = (await db.select(db.localSubmissions).get()).single;
    expect(s.state, 'accepted');
    expect(s.serverId, isNotNull);
    expect(s.receivedAtServer, isNotNull);
    expect((await db.select(db.localPhotos).get()).single.uploadState, 'uploaded');
    print('E2E:ACCEPTED serverId=${s.serverId} attempts=${s.attempts} secondsAfterOnline=$secs '
        'submittedAtDevice=${s.submittedAtDevice.toIso8601String()} acceptedAtServer=${s.acceptedAtServer?.toIso8601String()}');
    await shutdown(t, db);
  }, timeout: const Timeout(Duration(minutes: 20)));
}

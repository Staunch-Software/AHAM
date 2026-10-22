// ignore_for_file: avoid_print
// Review workflow end to end on an emulator, against the real backend:
//   agent submits (managed "Type of person" dropdown, 2 photos) -> the reviewer sends it back with a reason and a flag
//   (the test calls the admin API) -> the phone shows the feedback after a sync -> the agent corrects it, adds a photo
//   and resubmits -> the server holds revision 2 of the same report and the earlier version as history.
//
//   flutter test integration_test/correction_scenario_test.dart -d emulator-5554 \
//     --dart-define=E2E_EMAIL=agent@... --dart-define=E2E_PASSWORD=... \
//     --dart-define=E2E_ADMIN_EMAIL=admin@... --dart-define=E2E_ADMIN_PASSWORD=...
import 'package:dio/dio.dart';
import 'package:fieldsync_mobile/core/config.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker_platform_interface/image_picker_platform_interface.dart';
import 'package:integration_test/integration_test.dart';

import 'support.dart';

const _email = String.fromEnvironment('E2E_EMAIL');
const _password = String.fromEnvironment('E2E_PASSWORD');
const _adminEmail = String.fromEnvironment('E2E_ADMIN_EMAIL');
const _adminPassword = String.fromEnvironment('E2E_ADMIN_PASSWORD');

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  testWidgets('Reviewer sends a report back; agent corrects it; the server keeps both versions', (t) async {
    expect(_email, isNotEmpty, reason: 'pass --dart-define=E2E_EMAIL / E2E_PASSWORD / E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD');
    ImagePickerPlatform.instance = FakePicker();
    final db = await boot(t);
    mark('READY_FOR_GRANT');
    await Future<void>.delayed(const Duration(seconds: 12));
    await t.pump();

    // ---- agent signs in, opens the form
    await pumpUntil(t, () => has(find.widgetWithText(TextFormField, 'Email')), what: 'login screen');
    await t.enterText(find.widgetWithText(TextFormField, 'Email'), _email);
    await t.enterText(find.widgetWithText(TextFormField, 'Password'), _password);
    await t.tap(find.widgetWithText(FilledButton, 'Sign in'));
    await pumpUntil(t, () => has(find.text('Pending sync')), what: 'dashboard', timeout: const Duration(seconds: 30));
    await tapText(t, find.text('Forms'));
    await pumpUntil(t, () => has(find.text('New report')), what: 'form downloaded', timeout: const Duration(seconds: 30));
    expect(find.textContaining('Version 4'), findsOneWidget, reason: 'the current form version is offered');
    await tapText(t, find.text('New report'));
    await pumpUntil(t, () => has(find.byType(DropdownButtonFormField<String>)), what: 'form with the type dropdown');

    // ---- fill: type of person comes from the managed list
    await t.tap(find.byType(DropdownButtonFormField<String>).first);
    await t.pump(const Duration(milliseconds: 500));
    expect(find.text('Dealer'), findsWidgets);
    await t.tap(find.text('Dealer').last);
    await t.pump(const Duration(milliseconds: 500));
    await fill(t, 'Name of the person met *', 'Correction Test Dealer');
    await fill(t, 'Short description of the meeting *', 'First version of the description');
    await tapText(t, find.text('Take photo'));
    await pumpUntil(t, () => has(find.text('Add another photo')), what: 'first photo', timeout: const Duration(seconds: 40));
    await tapText(t, find.text('Add another photo'));
    await pumpUntil(t, () => has(find.text('2 of 5 photos')), what: 'second photo', timeout: const Duration(seconds: 40));
    await tapText(t, find.widgetWithText(FilledButton, 'Submit'));
    await pumpUntil(t, () => has(find.text('Submissions')), what: 'history after submit', timeout: const Duration(seconds: 60));

    // ---- the server accepts it
    await waitForReal(t, () async => (await db.select(db.localSubmissions).get()).any((s) => s.state == 'accepted'), timeout: const Duration(minutes: 2), what: 'first version accepted');
    var first = (await db.select(db.localSubmissions).get()).single;
    expect(first.reference, startsWith('FS-'));
    expect(first.revision, 1);
    mark('FIRST_ACCEPTED ${first.reference}');

    // ---- the reviewer (admin API) sends it back with a reason, a message and a flag on the photos
    final api = Dio(BaseOptions(baseUrl: '${AppConfig.apiBaseUrl}/api/v1', validateStatus: (s) => s != null && s < 500));
    final tok = (await api.post('/auth/login', data: {'email': _adminEmail, 'password': _adminPassword})).data['access_token'];
    api.options.headers['Authorization'] = 'Bearer $tok';
    final rej = await api.post('/submissions/${first.serverId}/reviews', data: {
      'decision': 'rejected', 'reason_code': 'unclear_photo', 'comment': 'Upload a clearer photo of the meeting.',
      'flags': [{'path': 'meeting_details[0].meeting_photos', 'note': 'Photo is blurry'}],
    });
    expect(rej.statusCode, 200, reason: '${rej.data}');
    mark('REJECTED_BY_REVIEWER');

    // ---- the phone learns about it on the next sync (the button, as an agent would)
    await tapText(t, find.text('Home'));
    await pumpUntil(t, () => has(find.text('Sync now')), what: 'home');
    await tapText(t, find.text('Sync now'));
    await waitForReal(t, () async => (await db.select(db.localSubmissions).get()).any((s) => s.reviewStatus == 'rejected'), timeout: const Duration(minutes: 1), what: 'feedback pulled');
    await pumpUntil(t, () => has(find.text('Reports that need your correction')), what: 'home banner for reports needing correction');
    mark('HOME_BANNER'); // the host driver may capture a screenshot here
    await Future<void>.delayed(const Duration(seconds: 3));
    await tapText(t, find.text(first.reference!).first);
    await pumpUntil(t, () => has(find.text('Report needs correction')), what: 'feedback card');
    expect(find.text('Unclear photo'), findsWidgets); // the feedback card (and the Home banner underneath)
    expect(find.text('Upload a clearer photo of the meeting.'), findsOneWidget);
    expect(find.textContaining('Photo is blurry'), findsOneWidget);
    mark('FEEDBACK_SHOWN');
    await Future<void>.delayed(const Duration(seconds: 3)); // time for a screenshot of the feedback card

    // ---- correct it: pre-filled with the submitted answers, the flagged item is marked, add a third photo, resubmit
    await tapText(t, find.text('Correct this report'));
    await pumpUntil(t, () => has(find.textContaining("Reviewer's feedback")), what: 'correction form');
    mark('CORRECTION_FORM'); // the host driver may capture a screenshot here
    await Future<void>.delayed(const Duration(seconds: 3));
    expect(find.textContaining('Reviewer: Photo is blurry'), findsWidgets);
    expect(find.text('2 of 5 photos'), findsOneWidget, reason: 'photos already uploaded are kept');
    expect(find.text('Resubmit'), findsOneWidget);
    await fill(t, 'Short description of the meeting *', 'Second, corrected description');
    await tapText(t, find.text('Add another photo'));
    await pumpUntil(t, () => has(find.text('3 of 5 photos')), what: 'third photo', timeout: const Duration(seconds: 40));
    await tapText(t, find.widgetWithText(FilledButton, 'Resubmit'));
    await pumpUntil(t, () => has(find.text('Submissions')), what: 'history after resubmit', timeout: const Duration(seconds: 60));
    await waitForReal(t, () async {
      final rows = await db.select(db.localSubmissions).get();
      return rows.any((s) => s.correctsServerId == first.serverId && s.state == 'accepted');
    }, timeout: const Duration(minutes: 2), what: 'correction accepted');
    final rows = await db.select(db.localSubmissions).get();
    final second = rows.firstWhere((s) => s.correctsServerId == first.serverId);
    expect(second.revision, 2);
    expect(second.reference, first.reference, reason: 'the report keeps its reference');
    first = rows.firstWhere((s) => s.localId == first.localId);
    expect(first.isLatest, isFalse, reason: 'the first version is now history');
    expect(second.reviewStatus, 'pending');
    mark('CORRECTION_ACCEPTED ${second.reference} revision ${second.revision}');

    // ---- the server: one report, two versions, review history preserved, 3 photos on the new one
    final d2 = (await api.get('/submissions/${second.serverId}')).data as Map;
    expect(d2['revision'], 2);
    expect(d2['is_latest'], isTrue);
    expect(d2['review_status'], 'pending');
    expect((d2['photos'] as List).length, 3);
    expect(d2['person_types'], ['Dealer']);
    expect(((d2['answers'] as Map)['meeting_details'] as List).first['meeting_description'], 'Second, corrected description');
    expect((d2['revisions'] as List).map((r) => r['revision']), [1, 2]);
    expect((d2['reviews'] as List).single['reason_label'], 'Unclear photo');
    final d1 = (await api.get('/submissions/${first.serverId}')).data as Map;
    expect(d1['is_latest'], isFalse);
    expect(d1['review_status'], 'rejected');
    expect(((d1['answers'] as Map)['meeting_details'] as List).first['meeting_description'], 'First version of the description');
    expect((d1['photos'] as List).length, 2, reason: 'the earlier version is not rewritten');

    // ---- the phone's history shows one row for the report
    await tapText(t, find.text('History'));
    await pumpUntil(t, () => has(find.text('Accepted by server, awaiting review')), what: 'history row for the corrected report');
    expect(find.textContaining(first.reference!), findsOneWidget, reason: 'one row per report, not one per version');
  }, timeout: const Timeout(Duration(minutes: 15)));
}

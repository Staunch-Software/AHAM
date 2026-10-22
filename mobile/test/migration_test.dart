// Upgrade safety: a phone that already has the version-1 database must keep every report, draft and photo when the app
// updates to the version that adds review feedback and corrections.
import 'package:drift/drift.dart' hide isNull, isNotNull;
import 'package:drift/native.dart';
import 'package:fieldsync_mobile/database/database.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqlite3/sqlite3.dart' as sqlite;

// The version-1 tables exactly as the shipped v1 app created them (columns added in v2 are absent).
const _v1 = [
  '''CREATE TABLE cached_forms (form_id TEXT NOT NULL, version INTEGER NOT NULL, title TEXT NOT NULL, schema_json TEXT NOT NULL,
     fetched_at INTEGER NOT NULL, PRIMARY KEY (form_id, version))''',
  '''CREATE TABLE drafts (id TEXT NOT NULL PRIMARY KEY, user_id TEXT NOT NULL, form_id TEXT NOT NULL, form_version INTEGER NOT NULL,
     answers_json TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)''',
  '''CREATE TABLE local_submissions (local_id TEXT NOT NULL PRIMARY KEY, user_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
     form_id TEXT NOT NULL, form_version INTEGER NOT NULL, form_title TEXT NOT NULL, answers_json TEXT NOT NULL,
     submitted_at_device INTEGER NOT NULL, tz_offset_min INTEGER NOT NULL, sub_latitude REAL, sub_longitude REAL,
     sub_accuracy_m REAL, sub_fix_at_device INTEGER, sub_location_status TEXT NOT NULL, state TEXT NOT NULL,
     attempts INTEGER NOT NULL DEFAULT 0, next_attempt_at INTEGER NOT NULL, last_error TEXT, server_id TEXT,
     received_at_server INTEGER, accepted_at_server INTEGER, created_at INTEGER NOT NULL)''',
  '''CREATE TABLE local_photos (id TEXT NOT NULL PRIMARY KEY, draft_id TEXT, submission_local_id TEXT, file_path TEXT NOT NULL,
     sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, mime_type TEXT NOT NULL, captured_at_device INTEGER NOT NULL,
     latitude REAL, longitude REAL, accuracy_m REAL, location_fix_at_device INTEGER, location_status TEXT NOT NULL,
     location_source TEXT, upload_state TEXT NOT NULL DEFAULT 'pending')''',
  'CREATE TABLE key_values (key TEXT NOT NULL PRIMARY KEY, value TEXT NOT NULL)',
];

void main() {
  test('version 1 data survives the upgrade and the new columns get safe defaults', () async {
    final raw = sqlite.sqlite3.openInMemory();
    for (final ddl in _v1) {
      raw.execute(ddl);
    }
    raw.execute("INSERT INTO local_submissions VALUES ('L1','u1','k1','field_meeting_report',3,'Field Meeting Report','{}',1760000000,330,"
        "14.4,79.9,5.0,1760000001,'obtained','accepted',1,1760000000,NULL,'srv-1',1760000100,1760000101,1760000000)");
    raw.execute("INSERT INTO local_submissions VALUES ('L2','u1','k2','field_meeting_report',3,'Field Meeting Report','{}',1760000200,330,"
        "NULL,NULL,NULL,NULL,'timeout','queued',0,1760000200,NULL,NULL,NULL,NULL,1760000200)");
    raw.execute("INSERT INTO drafts VALUES ('D1','u1','field_meeting_report',3,'{\"a\":1}',1760000300,1760000300)");
    raw.execute("INSERT INTO local_photos VALUES ('P1',NULL,'L1','/p/1.jpg','abc',10,'image/jpeg',1760000000,14.4,79.9,5.0,1760000001,'obtained','gps','uploaded')");
    raw.execute("INSERT INTO key_values VALUES ('last_sync_at','2026-10-17T00:00:00Z')");
    raw.execute('PRAGMA user_version = 1');

    final db = AppDatabase(NativeDatabase.opened(raw));
    final subs = await db.select(db.localSubmissions).get();
    expect(subs.map((s) => s.localId).toSet(), {'L1', 'L2'}, reason: 'no report lost');
    final l1 = subs.firstWhere((s) => s.localId == 'L1');
    expect(l1.serverId, 'srv-1');
    expect(l1.state, 'accepted');
    expect(l1.subLatitude, 14.4);
    expect(l1.revision, 1);
    expect(l1.isLatest, isTrue);
    expect(l1.reviewStatus, isNull);
    expect(l1.correctsServerId, isNull);
    final l2 = subs.firstWhere((s) => s.localId == 'L2');
    expect(l2.state, 'queued', reason: 'an unsent report is still queued after the upgrade');
    expect((await db.select(db.drafts).get()).single.answersJson, '{"a":1}');
    expect((await db.select(db.drafts).get()).single.correctsServerId, isNull);
    expect((await db.select(db.localPhotos).get()).single.uploadState, 'uploaded');
    expect(await db.getValue('last_sync_at'), '2026-10-17T00:00:00Z');

    // the new columns are usable straight away
    await (db.update(db.localSubmissions)..where((t) => t.localId.equals('L1'))).write(
        const LocalSubmissionsCompanion(reviewStatus: Value('rejected'), reference: Value('FS-2026-0001'), isLatest: Value(false)));
    final after = await (db.select(db.localSubmissions)..where((t) => t.localId.equals('L1'))).getSingle();
    expect((after.reviewStatus, after.reference, after.isLatest), ('rejected', 'FS-2026-0001', false));
    await db.close();
  });
}

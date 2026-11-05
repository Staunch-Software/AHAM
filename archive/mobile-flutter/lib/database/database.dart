import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

part 'database.g.dart'; // generated: dart run build_runner build --delete-conflicting-outputs

class CachedForms extends Table {
  TextColumn get formId => text()();
  IntColumn get version => integer()();
  TextColumn get title => text()();
  TextColumn get schemaJson => text()();
  DateTimeColumn get fetchedAt => dateTime()();
  @override
  Set<Column> get primaryKey => {formId, version};
}

class Drafts extends Table {
  TextColumn get id => text()();
  TextColumn get userId => text()();
  TextColumn get formId => text()();
  IntColumn get formVersion => integer()();
  TextColumn get answersJson => text()();
  DateTimeColumn get createdAt => dateTime()();
  DateTimeColumn get updatedAt => dateTime()();
  // Set when this draft corrects a report that was sent back by the reviewer.
  TextColumn get correctsServerId => text().nullable()(); // server id of the revision being corrected
  IntColumn get baseRevision => integer().nullable()(); // revision the agent saw (server rejects stale corrections)
  TextColumn get correctsLocalId => text().nullable()(); // the local submission it came from (feedback, photos)
  TextColumn get reference => text().nullable()(); // FS-2026-0042
  @override
  Set<Column> get primaryKey => {id};
}

/// A submitted report. This table is also the durable sync outbox: `state` + `nextAttemptAt`
/// + `attempts` + `lastError` drive the sync engine. Written in the same transaction as the
/// submission itself, so a crash after "Saved offline" can never lose the queue entry.
///
/// state: queued | uploading | sync_pending | accepted | failed | conflict
class LocalSubmissions extends Table {
  TextColumn get localId => text()(); // also sent as client_submission_id
  TextColumn get userId => text()(); // only this user's rows are ever synced
  TextColumn get idempotencyKey => text()();
  TextColumn get formId => text()();
  IntColumn get formVersion => integer()();
  TextColumn get formTitle => text()();
  TextColumn get answersJson => text()();
  // Submission event (device clock). Immutable after creation.
  DateTimeColumn get submittedAtDevice => dateTime()(); // stored UTC
  IntColumn get tzOffsetMin => integer()();
  RealColumn get subLatitude => real().nullable()();
  RealColumn get subLongitude => real().nullable()();
  RealColumn get subAccuracyM => real().nullable()();
  DateTimeColumn get subFixAtDevice => dateTime().nullable()();
  TextColumn get subLocationStatus => text()();
  // Sync bookkeeping.
  TextColumn get state => text()();
  IntColumn get attempts => integer().withDefault(const Constant(0))();
  DateTimeColumn get nextAttemptAt => dateTime()();
  TextColumn get lastError => text().nullable()();
  // Server acknowledgement.
  TextColumn get serverId => text().nullable()();
  DateTimeColumn get receivedAtServer => dateTime().nullable()();
  DateTimeColumn get acceptedAtServer => dateTime().nullable()();
  DateTimeColumn get createdAt => dateTime()();
  // Revision chain: a correction is a NEW submission pointing at the revision it corrects.
  TextColumn get reference => text().nullable()();
  IntColumn get revision => integer().withDefault(const Constant(1))();
  BoolColumn get isLatest => boolean().withDefault(const Constant(true))(); // false once a newer revision exists
  TextColumn get correctsServerId => text().nullable()();
  IntColumn get baseRevision => integer().nullable()();
  // Latest review decision, pulled from the server on every sync.
  TextColumn get reviewStatus => text().nullable()(); // pending | approved | rejected
  TextColumn get reviewReason => text().nullable()();
  TextColumn get reviewComment => text().nullable()();
  TextColumn get reviewFlagsJson => text().nullable()(); // [{path, note}]
  DateTimeColumn get reviewedAt => dateTime().nullable()();
  @override
  Set<Column> get primaryKey => {localId};
}

class LocalPhotos extends Table {
  TextColumn get id => text()(); // stable photo UUID, reused on every retry
  TextColumn get draftId => text().nullable()();
  TextColumn get submissionLocalId => text().nullable()();
  TextColumn get filePath => text()();
  TextColumn get sha256 => text()();
  IntColumn get sizeBytes => integer()();
  TextColumn get mimeType => text()();
  // Capture event — recorded when the photo is taken, never overwritten at submit/sync time.
  DateTimeColumn get capturedAtDevice => dateTime()();
  RealColumn get latitude => real().nullable()();
  RealColumn get longitude => real().nullable()();
  RealColumn get accuracyM => real().nullable()();
  DateTimeColumn get locationFixAtDevice => dateTime().nullable()();
  TextColumn get locationStatus => text()();
  TextColumn get locationSource => text().nullable()();
  /// pending | uploaded
  TextColumn get uploadState => text().withDefault(const Constant('pending'))();
  @override
  Set<Column> get primaryKey => {id};
}

class KeyValues extends Table {
  TextColumn get key => text()();
  TextColumn get value => text()();
  @override
  Set<Column> get primaryKey => {key};
}

@DriftDatabase(tables: [CachedForms, Drafts, LocalSubmissions, LocalPhotos, KeyValues])
class AppDatabase extends _$AppDatabase {
  AppDatabase(super.e);

  /// Opens the on-device SQLite file. Safe to call from a background isolate too.
  factory AppDatabase.open() => AppDatabase(driftDatabase(name: 'fieldsync'));

  @override
  int get schemaVersion => 2;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onUpgrade: (m, from, to) async {
          if (from < 2) {
            // v2: review feedback and corrections. Existing reports are kept as they are (revision 1, latest).
            for (final c in [drafts.correctsServerId, drafts.baseRevision, drafts.correctsLocalId, drafts.reference]) {
              await m.addColumn(drafts, c);
            }
            for (final c in [
              localSubmissions.reference, localSubmissions.revision, localSubmissions.isLatest, localSubmissions.correctsServerId,
              localSubmissions.baseRevision, localSubmissions.reviewStatus, localSubmissions.reviewReason,
              localSubmissions.reviewComment, localSubmissions.reviewFlagsJson, localSubmissions.reviewedAt,
            ]) {
              await m.addColumn(localSubmissions, c);
            }
          }
        },
      );

  Future<String?> getValue(String key) async =>
      (await (select(keyValues)..where((t) => t.key.equals(key))).getSingleOrNull())?.value;

  Future<void> setValue(String key, String value) =>
      into(keyValues).insertOnConflictUpdate(KeyValuesCompanion.insert(key: key, value: value));
}

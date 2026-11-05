import 'package:drift/drift.dart';

import '../../database/database.dart';
import 'sync_engine.dart';

class DriftSyncStore implements SyncStore {
  DriftSyncStore(this.db);
  final AppDatabase db;

  Expression<bool> _inFlight($LocalSubmissionsTable t) => t.state.isIn(SubState.inFlight);

  @override
  Future<List<PendingSubmission>> due(String userId, DateTime now) async {
    final rows = await (db.select(db.localSubmissions)
          ..where((t) => t.userId.equals(userId) & _inFlight(t) & t.nextAttemptAt.isSmallerOrEqualValue(now))
          ..orderBy([(t) => OrderingTerm.asc(t.createdAt)]))
        .get();
    final out = <PendingSubmission>[];
    for (final r in rows) {
      final photos = await (db.select(db.localPhotos)..where((p) => p.submissionLocalId.equals(r.localId))).get();
      out.add(PendingSubmission(
        localId: r.localId, idempotencyKey: r.idempotencyKey, formId: r.formId, formVersion: r.formVersion,
        answersJson: r.answersJson, submittedAtUtc: r.submittedAtDevice, tzOffsetMin: r.tzOffsetMin,
        latitude: r.subLatitude, longitude: r.subLongitude, accuracyM: r.subAccuracyM, fixAt: r.subFixAtDevice,
        locationStatus: r.subLocationStatus, attempts: r.attempts,
        correctsServerId: r.correctsServerId, baseRevision: r.baseRevision,
        photos: [
          for (final p in photos)
            PendingPhoto(
              id: p.id, filePath: p.filePath, sha256: p.sha256, sizeBytes: p.sizeBytes, mimeType: p.mimeType,
              capturedAt: p.capturedAtDevice, latitude: p.latitude, longitude: p.longitude, accuracyM: p.accuracyM,
              fixAt: p.locationFixAtDevice, locationStatus: p.locationStatus, locationSource: p.locationSource,
              uploaded: p.uploadState == 'uploaded',
            ),
        ],
      ));
    }
    return out;
  }

  @override
  Future<DateTime?> nextWake(String userId) async {
    final t = db.localSubmissions;
    final q = db.selectOnly(t)
      ..addColumns([t.nextAttemptAt.min()])
      ..where(t.userId.equals(userId) & t.state.isIn(SubState.inFlight));
    return (await q.getSingle()).read(t.nextAttemptAt.min());
  }

  @override
  Future<void> update(String localId,
      {String? state, int? attempts, DateTime? nextAttemptAt, String? lastError, bool clearError = false}) {
    return (db.update(db.localSubmissions)..where((t) => t.localId.equals(localId))).write(
      LocalSubmissionsCompanion(
        state: state == null ? const Value.absent() : Value(state),
        attempts: attempts == null ? const Value.absent() : Value(attempts),
        nextAttemptAt: nextAttemptAt == null ? const Value.absent() : Value(nextAttemptAt),
        lastError: clearError ? const Value(null) : (lastError == null ? const Value.absent() : Value(lastError)),
      ),
    );
  }

  @override
  Future<void> markPhotoUploaded(String photoId) =>
      (db.update(db.localPhotos)..where((p) => p.id.equals(photoId))).write(const LocalPhotosCompanion(uploadState: Value('uploaded')));

  @override
  Future<void> markAccepted(String localId, Receipt r) async {
    await db.transaction(() async {
      final row = await (db.select(db.localSubmissions)..where((t) => t.localId.equals(localId))).getSingle();
      await (db.update(db.localSubmissions)..where((t) => t.localId.equals(localId))).write(LocalSubmissionsCompanion(
        state: const Value(SubState.accepted),
        serverId: Value(r.serverId),
        receivedAtServer: Value(r.receivedAt),
        acceptedAtServer: Value(r.acceptedAt),
        lastError: const Value(null),
        reference: Value(r.reference),
        revision: Value(r.revision),
        isLatest: const Value(true),
        reviewStatus: const Value('pending'), // a new revision is waiting for the reviewer
        reviewReason: const Value(null),
        reviewComment: const Value(null),
        reviewFlagsJson: const Value(null),
      ));
      // The report this one corrects is now history; the app must stop offering to correct it.
      if (row.correctsServerId != null) {
        await (db.update(db.localSubmissions)..where((t) => t.serverId.equals(row.correctsServerId!)))
            .write(const LocalSubmissionsCompanion(isLatest: Value(false)));
      }
    });
  }
}

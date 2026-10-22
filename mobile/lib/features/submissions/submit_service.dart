import 'dart:convert';
import 'dart:io';

import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../../database/database.dart';
import '../dynamic_form_renderer/form_schema.dart';
import '../location_capture/location_service.dart';
import '../synchronization/sync_engine.dart';

class SubmitOutcome {
  SubmitOutcome.errors(this.errors) : localId = null;
  SubmitOutcome.saved(this.localId) : errors = const [];
  final String? localId;
  final List<FieldError> errors;
  bool get ok => localId != null;
}

class SubmitService {
  SubmitService(this.db, this.location, {DateTime Function()? now}) : _now = now ?? DateTime.now;
  final AppDatabase db;
  final LocationService location;
  final DateTime Function() _now;
  static const _uuid = Uuid();

  /// 1 validate -> 2 stamp submission time -> 3 fresh GPS fix (bounded wait, never blocks submit)
  /// -> 4 ONE local transaction: save submission+outbox state, attach photos, delete draft.
  /// Nothing here needs the network; success means "Saved offline", not "accepted by server".
  Future<SubmitOutcome> submit({required String userId, required String draftId, required FormSchema schema, required Map<String, dynamic> answers}) async {
    final errors = validateAnswers(schema, answers);
    if (errors.isNotEmpty) return SubmitOutcome.errors(errors);

    final submittedAt = _now(); // the instant Submit was pressed (device clock), taken before the GPS wait
    final fix = await location.currentFix();

    final localId = _uuid.v4();
    final referenced = photoIdsIn(schema, answers);
    final orphanFiles = <String>[];
    await db.transaction(() async {
      final draft = await (db.select(db.drafts)..where((d) => d.id.equals(draftId))).getSingle();
      await db.into(db.localSubmissions).insert(LocalSubmissionsCompanion.insert(
            localId: localId,
            userId: userId,
            idempotencyKey: _uuid.v4(),
            formId: schema.formId,
            formVersion: schema.version,
            formTitle: schema.title,
            answersJson: jsonEncode(answers),
            submittedAtDevice: submittedAt.toUtc(),
            tzOffsetMin: submittedAt.timeZoneOffset.inMinutes,
            subLatitude: Value(fix.latitude),
            subLongitude: Value(fix.longitude),
            subAccuracyM: Value(fix.accuracyM),
            subFixAtDevice: Value(fix.fixAt),
            subLocationStatus: fix.hasFix ? LocationStatus.obtained : fix.status,
            state: SubState.queued,
            nextAttemptAt: submittedAt.toUtc(),
            createdAt: submittedAt.toUtc(),
            // a correction is a NEW submission that names the revision it replaces
            correctsServerId: Value(draft.correctsServerId),
            baseRevision: Value(draft.baseRevision),
            reference: Value(draft.reference),
          ));
      // Photos of this draft, plus (for a correction) the photos the original report already uploaded: kept ones move
      // to the new submission and are not uploaded again.
      final photos = await (db.select(db.localPhotos)
            ..where((p) => p.draftId.equals(draftId) | (draft.correctsLocalId == null ? const Constant(false) : p.submissionLocalId.equals(draft.correctsLocalId!))))
          .get();
      for (final p in photos) {
        if (referenced.contains(p.id)) {
          await (db.update(db.localPhotos)..where((t) => t.id.equals(p.id)))
              .write(LocalPhotosCompanion(submissionLocalId: Value(localId), draftId: const Value(null)));
        } else if (p.draftId == draftId) {
          orphanFiles.add(p.filePath); // retaken / removed photo that is no longer referenced
          await (db.delete(db.localPhotos)..where((t) => t.id.equals(p.id))).go();
        } // an earlier report's photo that was removed in the correction stays with that earlier report
      }
      await (db.delete(db.drafts)..where((d) => d.id.equals(draftId))).go();
    });
    for (final path in orphanFiles) {
      try {
        await File(path).delete();
      } catch (_) {}
    }
    return SubmitOutcome.saved(localId);
  }

  /// Manual retry of a failed/conflicted submission (e.g. after the agent fixed connectivity).
  Future<void> retry(String localId) => (db.update(db.localSubmissions)..where((t) => t.localId.equals(localId))).write(
        LocalSubmissionsCompanion(state: const Value(SubState.queued), attempts: const Value(0), nextAttemptAt: Value(_now().toUtc()), lastError: const Value(null)),
      );
}

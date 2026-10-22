import 'dart:convert';

import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../../core/api_client.dart';
import '../../database/database.dart';
import '../dynamic_form_renderer/form_schema.dart';

class AssignedForm {
  AssignedForm(this.formId, this.title, this.version, this.schema);
  final String formId, title;
  final int version;
  final FormSchema schema;
}

class FormsRepository {
  FormsRepository(this.db, this.api);
  final AppDatabase db;
  final ApiClient api;

  /// Downloads the agent's assigned forms. Each schema is validated before it is cached;
  /// an invalid one is skipped (the previous cached version stays usable). Offline -> no-op.
  Future<String?> refresh() async {
    try {
      final r = await api.dio.get('/agent/forms/sync');
      var skipped = 0;
      for (final f in r.data as List) {
        try {
          final schema = FormSchema.fromJson(f['schema']);
          await db.into(db.cachedForms).insertOnConflictUpdate(CachedFormsCompanion.insert(
                formId: schema.formId, version: schema.version, title: schema.title,
                schemaJson: jsonEncode(f['schema']), fetchedAt: DateTime.now().toUtc()));
        } on SchemaException {
          skipped++;
        }
      }
      return skipped == 0 ? null : '$skipped form(s) could not be loaded (unsupported schema)';
    } catch (e) {
      return null; // offline or server down: keep using the cache
    }
  }

  /// Latest cached version of each form.
  Stream<List<AssignedForm>> watch() => db.select(db.cachedForms).watch().map((rows) {
        final latest = <String, CachedForm>{};
        for (final r in rows) {
          if (!latest.containsKey(r.formId) || latest[r.formId]!.version < r.version) latest[r.formId] = r;
        }
        final out = <AssignedForm>[];
        for (final r in latest.values) {
          try {
            out.add(AssignedForm(r.formId, r.title, r.version, FormSchema.parse(r.schemaJson)));
          } on SchemaException {
            // never render a schema that fails validation
          }
        }
        return out..sort((a, b) => a.title.compareTo(b.title));
      });

  Future<FormSchema?> schemaFor(String formId, int version) async {
    final r = await (db.select(db.cachedForms)..where((t) => t.formId.equals(formId) & t.version.equals(version))).getSingleOrNull();
    return r == null ? null : FormSchema.parse(r.schemaJson);
  }

  Future<String> newDraft(String userId, AssignedForm f) async {
    final id = const Uuid().v4();
    final now = DateTime.now().toUtc();
    await db.into(db.drafts).insert(DraftsCompanion.insert(
          id: id, userId: userId, formId: f.formId, formVersion: f.version,
          answersJson: jsonEncode(emptyAnswers(f.schema)), createdAt: now, updatedAt: now));
    return id;
  }

  /// A draft that corrects a report the reviewer sent back: starts from the submitted answers. One per report.
  Future<String> newCorrectionDraft(String userId, LocalSubmission s) async {
    final existing = await (db.select(db.drafts)..where((d) => d.correctsServerId.equals(s.serverId!))).getSingleOrNull();
    if (existing != null) return existing.id;
    final id = const Uuid().v4();
    final now = DateTime.now().toUtc();
    await db.into(db.drafts).insert(DraftsCompanion.insert(
          id: id, userId: userId, formId: s.formId, formVersion: s.formVersion, answersJson: s.answersJson, createdAt: now, updatedAt: now,
          correctsServerId: Value(s.serverId), baseRevision: Value(s.revision), correctsLocalId: Value(s.localId), reference: Value(s.reference)));
    return id;
  }

  Future<void> saveDraft(String id, Map<String, dynamic> answers) =>
      (db.update(db.drafts)..where((d) => d.id.equals(id))).write(
        DraftsCompanion(answersJson: Value(jsonEncode(answers)), updatedAt: Value(DateTime.now().toUtc())),
      );

  Future<void> deleteDraft(String id) async {
    await (db.delete(db.localPhotos)..where((p) => p.draftId.equals(id))).go();
    await (db.delete(db.drafts)..where((d) => d.id.equals(id))).go();
  }
}

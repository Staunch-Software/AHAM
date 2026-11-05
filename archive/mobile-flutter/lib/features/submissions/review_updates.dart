import 'dart:convert';

import 'package:drift/drift.dart';

import '../../core/api_client.dart';
import '../../database/database.dart';

/// Pulls the reviewer's decisions for this agent's reports and stores them next to the local copies.
/// Runs after every sync, so "needs correction" appears as soon as the phone is online.
class ReviewUpdates {
  ReviewUpdates(this.db, this.api);
  final AppDatabase db;
  final ApiClient api;
  static const _sinceKey = 'review_pull_since';

  /// Returns how many local reports were updated. Network errors propagate; the caller ignores them.
  Future<int> pull() async {
    final since = await db.getValue(_sinceKey);
    final r = await api.dio.get('/agent/reports/updates', queryParameters: {if (since != null) 'since': since});
    final items = ((r.data as Map)['items'] as List).cast<Map>();
    return apply(items.map((e) => Map<String, dynamic>.from(e)).toList(), since);
  }

  Future<int> apply(List<Map<String, dynamic>> items, String? since) async {
    var changed = 0;
    String? newest = since;
    for (final it in items) {
      final id = it['id'] as String;
      final n = await (db.update(db.localSubmissions)..where((t) => t.serverId.equals(id))).write(LocalSubmissionsCompanion(
        reference: Value(it['reference'] as String?),
        revision: Value((it['revision'] as num?)?.toInt() ?? 1),
        isLatest: Value(it['is_latest'] != false),
        reviewStatus: Value(it['review_status'] as String?),
        reviewReason: Value((it['reason_label'] ?? it['reason_code']) as String?),
        reviewComment: Value(it['comment'] as String?),
        reviewFlagsJson: Value(jsonEncode(it['flags'] ?? const [])),
        reviewedAt: Value(DateTime.tryParse('${it['reviewed_at']}')),
      ));
      changed += n;
      final at = it['reviewed_at'] as String?;
      if (at != null && (newest == null || DateTime.parse(at).isAfter(DateTime.parse(newest)))) newest = at;
    }
    if (newest != null && newest != since) await db.setValue(_sinceKey, newest);
    return changed;
  }
}

/// The reviewer's flags as a path -> note map (path like meeting_details[1] or meeting_details[1].meeting_photos).
Map<String, String> flagsOf(String? json) {
  if (json == null || json.isEmpty) return {};
  try {
    return {for (final f in (jsonDecode(json) as List)) (f['path'] as String): f['note'] as String};
  } catch (_) {
    return {};
  }
}

/// What the agent sees for a report. Never says "accepted" for something the server has not acknowledged.
({String label, String tone}) displayStatus(LocalSubmission s, {required String Function(String state, int attempts) stateLabel}) {
  if (s.state != 'accepted') return (label: stateLabel(s.state, s.attempts), tone: s.state == 'failed' || s.state == 'conflict' ? 'bad' : 'wait');
  if (!s.isLatest) return (label: 'Corrected: replaced by a newer version', tone: 'done');
  return switch (s.reviewStatus) {
    'rejected' => (label: 'Needs correction', tone: 'bad'),
    'approved' => (label: 'Approved', tone: 'good'),
    _ => (label: 'Accepted by server, awaiting review', tone: 'good'),
  };
}

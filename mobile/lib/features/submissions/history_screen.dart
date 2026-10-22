import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../../database/database.dart';
import '../synchronization/sync_engine.dart';
import 'review_updates.dart';

Color toneColor(BuildContext c, String tone) => toneColors(tone).fg;

/// "meeting_details[1].meeting_photos" -> "Meeting 2 · meeting photos". Flags point at a meeting or one of its fields.
String flagTarget(String path) {
  final m = RegExp(r'^[a-z_0-9]+\[(\d+)\](?:\.([a-z_0-9]+))?$').firstMatch(path);
  if (m == null) return path;
  final meeting = 'Meeting ${int.parse(m.group(1)!) + 1}';
  return m.group(2) == null ? meeting : '$meeting · ${m.group(2)!.replaceAll('_', ' ')}';
}

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Superseded versions are history; the list shows one row per report (its newest version).
    final subs = (ref.watch(submissionsProvider).valueOrNull ?? const <LocalSubmission>[]).where((s) => s.isLatest || s.state != SubState.accepted).toList();
    final fmt = DateFormat.yMd().add_jm();
    return Scaffold(
      appBar: AppBar(title: const Text('Submissions')),
      body: subs.isEmpty
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  IconTile(icon: Icons.inbox_outlined, size: 60),
                  SizedBox(height: 16),
                  Text('No submissions yet.', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16, color: Brand.navy900)),
                  SizedBox(height: 4),
                  Text('Reports you submit appear here, even before they reach the server.', textAlign: TextAlign.center, style: TextStyle(color: Brand.muted, height: 1.4)),
                ]),
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: subs.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (c, i) {
                final s = subs[i];
                final st = displayStatus(s, stateLabel: stateLabel);
                final tc = toneColors(st.tone);
                return Card(
                  child: ListTile(
                    contentPadding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
                    leading: IconTile(icon: toneIcon(st.tone), fg: tc.fg, bg: tc.bg, size: 42),
                    title: Text(s.reference == null ? '${s.formTitle} v${s.formVersion}' : '${s.reference} · ${s.formTitle}', style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('Submitted ${fmt.format(s.submittedAtDevice.toLocal())}${s.revision > 1 ? ' · revision ${s.revision}' : ''}', style: const TextStyle(color: Brand.muted, fontSize: 13)),
                        const SizedBox(height: 8),
                        StatusPill(label: st.label, tone: st.tone),
                      ]),
                    ),
                    trailing: const Icon(Icons.chevron_right_rounded, color: Brand.muted),
                    onTap: () => context.push('/submission/${s.localId}'),
                  ),
                );
              },
            ),
    );
  }
}

class SubmissionDetailScreen extends ConsumerWidget {
  const SubmissionDetailScreen({super.key, required this.localId});
  final String localId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final db = ref.watch(databaseProvider);
    final fmt = DateFormat.yMd().add_jms();
    final all = ref.watch(submissionsProvider).valueOrNull ?? const <LocalSubmission>[];
    final drafts = ref.watch(draftsProvider).valueOrNull ?? const <Draft>[];
    return Scaffold(
      appBar: AppBar(title: const Text('Submission')),
      body: StreamBuilder<LocalSubmission?>(
        stream: (db.select(db.localSubmissions)..where((t) => t.localId.equals(localId))).watchSingleOrNull(),
        builder: (c, snap) {
          final s = snap.data;
          if (s == null) return const Center(child: CircularProgressIndicator());
          final st = displayStatus(s, stateLabel: stateLabel);
          Widget row(String k, String v) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 7),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SizedBox(width: 132, child: Text(k, style: const TextStyle(color: Brand.muted, fontSize: 13.5))),
                  Expanded(child: Text(v, style: const TextStyle(color: Brand.ink, fontSize: 13.5, height: 1.3))),
                ]),
              );
          final needsFix = s.state == SubState.accepted && s.isLatest && s.reviewStatus == 'rejected';
          final correctionDraft = s.serverId == null ? null : drafts.where((d) => d.correctsServerId == s.serverId).firstOrNull;
          final correctionSent = s.serverId == null ? null : all.where((x) => x.correctsServerId == s.serverId).firstOrNull;
          final flags = flagsOf(s.reviewFlagsJson);
          return ListView(padding: const EdgeInsets.all(16), children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(s.reference ?? '${s.formTitle} v${s.formVersion}', style: Theme.of(c).textTheme.titleLarge),
                  if (s.reference != null) Padding(padding: const EdgeInsets.only(top: 2), child: Text('${s.formTitle} v${s.formVersion}${s.revision > 1 ? ' · revision ${s.revision}' : ''}', style: const TextStyle(color: Brand.muted))),
                  const SizedBox(height: 12),
                  StatusPill(label: st.label, tone: st.tone),
                ]),
              ),
            ),
            if (needsFix)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Brand.roof50, borderRadius: BorderRadius.circular(16), border: Border.all(color: Brand.roof200)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Row(children: [
                      Icon(Icons.error_outline_rounded, color: Brand.roof700),
                      SizedBox(width: 8),
                      Text('Report needs correction', style: TextStyle(fontWeight: FontWeight.w700, color: Brand.roof700, fontSize: 15.5)),
                    ]),
                    const SizedBox(height: 12),
                    Text('Reviewer\'s feedback', style: Theme.of(c).textTheme.labelLarge?.copyWith(color: Brand.roof700)),
                    const SizedBox(height: 2),
                    if (s.reviewReason != null) Text(s.reviewReason!, style: const TextStyle(fontWeight: FontWeight.w700, color: Brand.navy900)),
                    if (s.reviewComment != null) Padding(padding: const EdgeInsets.only(top: 2), child: Text(s.reviewComment!, style: const TextStyle(color: Brand.ink, height: 1.4))),
                    if (flags.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Text('Flagged items', style: Theme.of(c).textTheme.labelLarge?.copyWith(color: Brand.roof700)),
                      for (final e in flags.entries) Padding(padding: const EdgeInsets.only(top: 3), child: Text('• ${flagTarget(e.key)}: ${e.value}', style: const TextStyle(color: Brand.ink, height: 1.35))),
                    ],
                    const SizedBox(height: 14),
                    if (correctionSent != null)
                      Text('Your correction is saved (${stateLabel(correctionSent.state, correctionSent.attempts)}). It will be reviewed once it reaches the server.', style: const TextStyle(color: Brand.ink, height: 1.4))
                    else
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          icon: const Icon(Icons.edit_note_rounded),
                          label: Text(correctionDraft == null ? 'Correct this report' : 'Continue correction'),
                          onPressed: () async {
                            final id = await ref.read(formsRepositoryProvider).newCorrectionDraft(ref.read(authProvider).userId, s);
                            if (c.mounted) c.push('/form/$id');
                          },
                        ),
                      ),
                  ]),
                ),
              ),
            if (s.state == SubState.accepted && s.isLatest && s.reviewStatus == 'approved')
              const Padding(padding: EdgeInsets.only(top: 12), child: Notice(tone: 'warn', icon: Icons.verified_rounded, child: Text('This report was approved. No further action is needed.'))),
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                child: Column(children: [
                  row('Local ID', s.localId),
                  row('Receipt (server ID)', s.serverId ?? 'Not yet acknowledged'),
                  row('Created', fmt.format(s.createdAt.toLocal())),
                  row('Submitted (device)', fmt.format(s.submittedAtDevice.toLocal())),
                  row('Submission location', s.subLatitude == null ? 'Unavailable (${s.subLocationStatus.replaceAll('_', ' ')})' : '${s.subLatitude!.toStringAsFixed(5)}, ${s.subLongitude!.toStringAsFixed(5)} ±${s.subAccuracyM?.round() ?? '?'} m'),
                  row('Server received', s.receivedAtServer == null ? '—' : fmt.format(s.receivedAtServer!.toLocal())),
                  row('Server accepted', s.acceptedAtServer == null ? '—' : fmt.format(s.acceptedAtServer!.toLocal())),
                  row('Attempts', '${s.attempts}'),
                  if (s.reviewedAt != null) row('Last review', fmt.format(s.reviewedAt!.toLocal())),
                  if (s.lastError != null) row('Last error', s.lastError!),
                ]),
              ),
            ),
            const SizedBox(height: 16),
            if (s.state == SubState.failed || s.state == SubState.conflict || s.state == SubState.queued && s.attempts > 0)
              FilledButton.icon(
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Retry now'),
                onPressed: () async {
                  await ref.read(submitServiceProvider).retry(s.localId);
                  ref.read(syncProvider.notifier).trigger('manual');
                },
              ),
            if (s.state == SubState.conflict)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Notice(
                  tone: 'bad',
                  child: Text(s.correctsServerId != null
                      ? 'The server could not accept this correction (see the error above). Your corrected data is kept on this device. If the report was changed or already corrected, open the original report again to see its latest state.'
                      : 'The server rejected this report. Your data is preserved on this device. Retrying only helps if the cause was temporary (for example a branch assignment that has been restored). Contact your administrator otherwise.'),
                ),
              ),
          ]);
        },
      ),
    );
  }
}

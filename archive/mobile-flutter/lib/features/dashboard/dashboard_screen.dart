import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../app/widgets.dart';
import '../synchronization/sync_engine.dart';

String _greeting() {
  final h = DateTime.now().hour;
  return h < 12 ? 'Good morning' : (h < 17 ? 'Good afternoon' : 'Good evening');
}

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final subs = ref.watch(submissionsProvider).valueOrNull ?? const [];
    final drafts = ref.watch(draftsProvider).valueOrNull ?? const [];
    final forms = ref.watch(assignedFormsProvider).valueOrNull ?? const [];
    final sync = ref.watch(syncProvider);
    // Counts are derived from real local rows; nothing here is fabricated.
    final pending = subs
        .where((s) => SubState.inFlight.contains(s.state))
        .length;
    final accepted = subs.where((s) => s.state == SubState.accepted).length;
    final problems = subs
        .where(
          (s) => s.state == SubState.failed || s.state == SubState.conflict,
        )
        .length;
    // reports the reviewer sent back that the agent has not corrected yet
    final needFix = subs
        .where(
          (s) =>
              s.state == SubState.accepted &&
              s.isLatest &&
              s.reviewStatus == 'rejected' &&
              !subs.any((x) => x.correctsServerId == s.serverId),
        )
        .toList();
    final fmt = DateFormat.yMd().add_jm();
    final firstName = auth.name.trim().split(RegExp(r'\s+')).first;

    // Two tiles per row; each tile is as tall as its content (fixed-ratio grids overflow with large system fonts).
    final tileWidth = (MediaQuery.of(context).size.width - 32 - 12) / 2;
    Widget tile(
      String label,
      int n,
      IconData icon, {
      Color fg = Brand.navy700,
      Color bg = Brand.navy50,
    }) => SizedBox(
      width: tileWidth,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              IconTile(icon: icon, fg: fg, bg: bg, size: 38),
              const SizedBox(height: 12),
              Text(
                '$n',
                style: Theme.of(
                  context,
                ).textTheme.headlineSmall?.copyWith(fontSize: 28),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: const TextStyle(
                  color: Brand.muted,
                  fontSize: 13,
                  height: 1.25,
                ),
              ),
            ],
          ),
        ),
      ),
    );

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: lightStatusBar,
      child: Scaffold(
        body: RefreshIndicator(
          onRefresh: () async =>
              ref.read(syncProvider.notifier).trigger('manual'),
          child: ListView(
            padding: EdgeInsets.zero,
            children: [
              Container(
                padding: EdgeInsets.fromLTRB(
                  20,
                  MediaQuery.of(context).padding.top + 14,
                  20,
                  22,
                ),
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Brand.navy800, Brand.navy900],
                  ),
                  borderRadius: BorderRadius.vertical(
                    bottom: Radius.circular(28),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const BrandLogo(size: 40),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'FieldSync',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 17,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                'AHAM HOUSING FINANCE',
                                style: TextStyle(
                                  color: Brand.gold400,
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1.2,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          tooltip: 'Sign out',
                          icon: const Icon(
                            Icons.logout_rounded,
                            color: Colors.white70,
                          ),
                          onPressed: () =>
                              ref.read(authProvider.notifier).logout(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 22),
                    Text(
                      _greeting(),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.75),
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      firstName.isEmpty ? 'Welcome' : firstName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.6,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.fromLTRB(14, 10, 10, 10),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            sync.running
                                ? Icons.sync_rounded
                                : Icons.cloud_done_outlined,
                            color: Brand.gold400,
                            size: 22,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              sync.lastSyncAt == null
                                  ? 'Never synced'
                                  : 'Last synced ${fmt.format(sync.lastSyncAt!)}',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 13.5,
                              ),
                            ),
                          ),
                          FilledButton.tonalIcon(
                            style: FilledButton.styleFrom(
                              minimumSize: const Size(0, 40),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                              ),
                              backgroundColor: Brand.gold500,
                              foregroundColor: Brand.navy900,
                            ),
                            icon: sync.running
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Brand.navy900,
                                    ),
                                  )
                                : const Icon(Icons.sync_rounded, size: 18),
                            label: Text(sync.running ? 'Syncing…' : 'Sync now'),
                            onPressed: sync.running
                                ? null
                                : () => ref
                                      .read(syncProvider.notifier)
                                      .trigger('manual'),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (sync.lastMessage != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Notice(
                          tone: 'bad',
                          child: Text(sync.lastMessage!),
                        ),
                      ),
                    Card(
                      child: InkWell(
                        borderRadius: BorderRadius.circular(16),
                        onTap: () => context.go('/forms'),
                        child: const Padding(
                          padding: EdgeInsets.all(16),
                          child: Row(
                            children: [
                              IconTile(
                                icon: Icons.add_a_photo_rounded,
                                fg: Brand.navy900,
                                bg: Brand.gold100,
                                size: 48,
                              ),
                              SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Start a new report',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w700,
                                        fontSize: 16,
                                        color: Brand.navy900,
                                      ),
                                    ),
                                    SizedBox(height: 2),
                                    Text(
                                      'Time and place are recorded for you.',
                                      style: TextStyle(
                                        color: Brand.muted,
                                        fontSize: 13,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              Icon(
                                Icons.arrow_forward_rounded,
                                color: Brand.navy700,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: [
                        tile('Drafts', drafts.length, Icons.edit_note_rounded),
                        tile(
                          'Pending sync',
                          pending,
                          Icons.schedule_rounded,
                          fg: pending > 0
                              ? const Color(0xFF92400E)
                              : Brand.navy700,
                          bg: pending > 0
                              ? const Color(0xFFFEF3C7)
                              : Brand.navy50,
                        ),
                        tile(
                          'Needs correction',
                          needFix.length,
                          Icons.rule_rounded,
                          fg: needFix.isNotEmpty
                              ? Brand.roof700
                              : Brand.navy700,
                          bg: needFix.isNotEmpty ? Brand.roof50 : Brand.navy50,
                        ),
                        tile(
                          'Accepted by server',
                          accepted,
                          Icons.check_circle_rounded,
                          fg: const Color(0xFF047857),
                          bg: Brand.green50,
                        ),
                        tile(
                          'Failed / needs attention',
                          problems,
                          Icons.error_outline_rounded,
                          fg: problems > 0 ? Brand.roof700 : Brand.navy700,
                          bg: problems > 0 ? Brand.roof50 : Brand.navy50,
                        ),
                      ],
                    ),
                    if (needFix.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      // Material (not a decorated Container) so the list tiles inside can show their ink ripples
                      Material(
                        color: Brand.roof50,
                        clipBehavior: Clip.antiAlias,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                          side: const BorderSide(color: Brand.roof200),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Padding(
                              padding: EdgeInsets.fromLTRB(16, 14, 16, 4),
                              child: Text(
                                'Reports that need your correction',
                                style: TextStyle(
                                  fontWeight: FontWeight.w700,
                                  color: Brand.roof700,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            for (final s in needFix)
                              ListTile(
                                dense: true,
                                title: Text(
                                  s.reference ?? s.formTitle,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                subtitle: Text(
                                  s.reviewReason ?? 'Sent back by the reviewer',
                                ),
                                trailing: const Icon(
                                  Icons.chevron_right_rounded,
                                ),
                                onTap: () =>
                                    context.push('/submission/${s.localId}'),
                              ),
                            const SizedBox(height: 6),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 20),
                    Text(
                      'Your forms',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    forms.isEmpty
                        ? const Text(
                            'None downloaded yet. Open Forms while online to get them.',
                            style: TextStyle(color: Brand.muted),
                          )
                        : Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              for (final f in forms)
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 8,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Brand.navy100,
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: Text(
                                    '${f.title} v${f.version}',
                                    style: const TextStyle(
                                      color: Brand.navy700,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                            ],
                          ),
                    const SizedBox(height: 12),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

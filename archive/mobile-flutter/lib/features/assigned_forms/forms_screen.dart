import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../app/widgets.dart';

class FormsScreen extends ConsumerWidget {
  const FormsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final forms = ref.watch(assignedFormsProvider).valueOrNull ?? const [];
    final drafts = ref.watch(draftsProvider).valueOrNull ?? const [];
    final repo = ref.read(formsRepositoryProvider);
    final fmt = DateFormat.MMMd().add_jm();
    return Scaffold(
      appBar: AppBar(title: const Text('Forms'), actions: [
        IconButton(
          tooltip: 'Refresh forms',
          icon: const Icon(Icons.refresh_rounded),
          onPressed: () async {
            final msg = await repo.refresh();
            if (context.mounted && msg != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
          },
        ),
      ]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (forms.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 40),
            child: Column(children: [
              IconTile(icon: Icons.cloud_download_outlined, size: 56),
              SizedBox(height: 14),
              Text('No forms downloaded yet. Connect to the internet and tap refresh.', textAlign: TextAlign.center, style: TextStyle(color: Brand.muted, height: 1.4)),
            ]),
          ),
        for (final f in forms)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Row(children: [
                    const IconTile(icon: Icons.assignment_rounded, size: 46),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(f.title, style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 2),
                        Text('Version ${f.version} · available offline', style: const TextStyle(color: Brand.muted, fontSize: 13)),
                      ]),
                    ),
                  ]),
                  const SizedBox(height: 14),
                  FilledButton.icon(
                    icon: const Icon(Icons.add_rounded),
                    label: const Text('New report'),
                    onPressed: () async {
                      final id = await repo.newDraft(ref.read(authProvider).userId, f);
                      if (context.mounted) context.push('/form/$id');
                    },
                  ),
                ]),
              ),
            ),
          ),
        if (drafts.isNotEmpty) ...[
          const SizedBox(height: 12),
          Padding(padding: const EdgeInsets.only(bottom: 8), child: Text('Drafts', style: Theme.of(context).textTheme.titleMedium)),
          for (final d in drafts)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Card(
                child: ListTile(
                  leading: const IconTile(icon: Icons.edit_note_rounded, size: 42),
                  title: Text(d.correctsServerId == null ? d.formId.replaceAll('_', ' ') : 'Correction of ${d.reference ?? 'a report'}', style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text('v${d.formVersion} · edited ${fmt.format(d.updatedAt.toLocal())}'),
                  onTap: () => context.push('/form/${d.id}'),
                  trailing: IconButton(
                    tooltip: 'Discard draft',
                    icon: const Icon(Icons.delete_outline_rounded),
                    onPressed: () async {
                      final ok = await showDialog<bool>(
                        context: context,
                        builder: (c) => AlertDialog(
                          title: const Text('Discard draft?'),
                          content: const Text('The draft and its photos will be deleted from this device.'),
                          actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Discard'))],
                        ),
                      );
                      if (ok == true) await repo.deleteDraft(d.id);
                    },
                  ),
                ),
              ),
            ),
        ],
      ]),
    );
  }
}

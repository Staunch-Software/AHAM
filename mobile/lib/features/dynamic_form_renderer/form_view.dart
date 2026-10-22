import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../location_capture/location_service.dart';
import 'form_schema.dart';

typedef PhotoCapture = Future<String?> Function(FieldDef field, {bool fromGallery});

/// Renders a validated [FormSchema] with native widgets. Stateless about storage: the parent owns
/// [answers] and persists them (draft autosave) in [onChanged].
class DynamicFormView extends ConsumerStatefulWidget {
  const DynamicFormView({super.key, required this.schema, required this.answers, required this.errors, required this.onChanged, required this.onCapturePhoto, required this.onDiscardPhoto, this.notes = const {}});
  final FormSchema schema;
  final Map<String, dynamic> answers;
  final Map<String, String> errors; // path -> message
  final Map<String, String> notes; // path -> reviewer's flag, shown while correcting a report that was sent back
  final VoidCallback onChanged;
  final PhotoCapture onCapturePhoto;
  final Future<void> Function(String photoId) onDiscardPhoto;

  @override
  ConsumerState<DynamicFormView> createState() => _State();
}

class _State extends ConsumerState<DynamicFormView> {
  // Stable widget identity per repeatable entry so removing entry 1 doesn't shift typed text.
  final Map<String, List<int>> _ids = {};
  int _next = 0;

  List<int> _entryIds(SectionDef s, int count) {
    final list = _ids.putIfAbsent(s.id, () => []);
    while (list.length < count) {
      list.add(_next++);
    }
    while (list.length > count) {
      list.removeLast();
    }
    return list;
  }

  void _changed(VoidCallback mutate) {
    setState(mutate);
    widget.onChanged();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 32), children: [for (final s in widget.schema.sections) _section(context, s)]);
  }

  Widget _section(BuildContext context, SectionDef s) {
    final theme = Theme.of(context);
    if (!s.repeatable) {
      final entry = widget.answers[s.id] as Map<String, dynamic>;
      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(s.title, style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        ..._fields(s, s.id, entry, 'static'),
      ]);
    }
    final entries = (widget.answers[s.id] as List).cast<Map<String, dynamic>>();
    final ids = _entryIds(s, entries.length);
    final listErr = widget.errors[s.id];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(s.title, style: theme.textTheme.titleMedium),
      if (listErr != null) Text(listErr, style: TextStyle(color: theme.colorScheme.error)),
      for (var i = 0; i < entries.length; i++)
        Card(
          key: ValueKey('${s.id}-${ids[i]}'),
          margin: const EdgeInsets.symmetric(vertical: 8),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (widget.notes['${s.id}[$i]'] != null) _Flag(widget.notes['${s.id}[$i]']!),
              Row(children: [
                Container(
                  width: 26,
                  height: 26,
                  alignment: Alignment.center,
                  decoration: const BoxDecoration(color: Brand.navy100, shape: BoxShape.circle),
                  child: Text('${i + 1}', style: const TextStyle(color: Brand.navy700, fontWeight: FontWeight.w700, fontSize: 12.5)),
                ),
                const SizedBox(width: 10),
                Text('Entry ${i + 1}', style: theme.textTheme.titleSmall),
                const Spacer(),
                if (entries.length > s.minItems)
                  IconButton(
                    tooltip: 'Remove entry ${i + 1}',
                    icon: const Icon(Icons.delete_outline),
                    onPressed: () => _confirmRemove(s, entries, i),
                  ),
              ]),
              ..._fields(s, '${s.id}[$i]', entries[i], '${s.id}-${ids[i]}'),
            ]),
          ),
        ),
      if (entries.length < s.maxItems)
        OutlinedButton.icon(
          icon: const Icon(Icons.add),
          label: Text('Add ${s.title.toLowerCase()} entry'),
          onPressed: () => _changed(() => entries.add(newEntry(s))),
        ),
      const SizedBox(height: 16),
    ]);
  }

  Future<void> _confirmRemove(SectionDef s, List<Map<String, dynamic>> entries, int i) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Remove entry?'),
        content: const Text('Its answers and photos will be discarded.'),
        actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Remove'))],
      ),
    );
    if (ok != true) return;
    final removed = entries[i];
    for (final f in s.fields) {
      final v = removed[f.key];
      if (f.type == 'photo' && v is String) await widget.onDiscardPhoto(v);
      if (f.type == 'photos' && v is List) {
        for (final id in v.whereType<String>()) {
          await widget.onDiscardPhoto(id);
        }
      }
    }
    _ids[s.id]?.removeAt(i);
    _changed(() => entries.removeAt(i));
  }

  List<Widget> _fields(SectionDef s, String path, Map<String, dynamic> entry, String idPrefix) => [
        for (final f in s.fields)
          if (isVisible(f, entry))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: _field(f, entry, '$path.${f.key}', '$idPrefix-${f.key}'),
            ),
      ];

  Widget _field(FieldDef f, Map<String, dynamic> entry, String path, String id) {
    final err = widget.errors[path];
    final label = f.required ? '${f.label} *' : f.label; // required indicator
    void set(dynamic v) => _changed(() => isEmptyValue(v) ? entry.remove(f.key) : entry[f.key] = v);
    final deco = InputDecoration(labelText: label, errorText: err, helperText: widget.notes[path] == null ? null : 'Reviewer: ${widget.notes[path]}', helperMaxLines: 3);

    switch (f.type) {
      case 'heading':
        return Text(f.label, style: Theme.of(context).textTheme.titleSmall);
      case 'readonly_text':
        return Text(f.label);
      case 'text' || 'phone' || 'email' || 'multiline_text' || 'integer' || 'decimal':
        final numeric = f.type == 'integer' || f.type == 'decimal';
        return TextFormField(
          key: ValueKey(id),
          initialValue: entry[f.key]?.toString() ?? '',
          decoration: deco,
          maxLines: f.type == 'multiline_text' ? 4 : 1,
          maxLength: (f.validation['max_length'] as int?),
          keyboardType: f.type == 'phone'
              ? TextInputType.phone
              : f.type == 'email'
                  ? TextInputType.emailAddress
                  : numeric
                      ? const TextInputType.numberWithOptions(decimal: true, signed: true)
                      : f.type == 'multiline_text'
                          ? TextInputType.multiline
                          : TextInputType.text,
          onChanged: (t) {
            final v = t.trim();
            if (numeric) {
              set(v.isEmpty ? null : (f.type == 'integer' ? (int.tryParse(v) ?? v) : (num.tryParse(v) ?? v)));
            } else {
              set(v);
            }
          },
        );
      case 'date':
        return _picker(f, entry, deco, id, () async {
          final now = DateTime.now();
          final d = await showDatePicker(context: context, initialDate: now, firstDate: DateTime(2000), lastDate: DateTime(now.year + 1));
          return d == null ? null : '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
        });
      case 'time':
        return _picker(f, entry, deco, id, () async {
          final t = await showTimePicker(context: context, initialTime: TimeOfDay.now());
          return t == null ? null : '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
        });
      case 'datetime':
        return _picker(f, entry, deco, id, () async {
          final now = DateTime.now();
          final d = await showDatePicker(context: context, initialDate: now, firstDate: DateTime(2000), lastDate: DateTime(now.year + 1));
          if (d == null || !mounted) return null;
          final t = await showTimePicker(context: context, initialTime: TimeOfDay.now());
          return t == null ? null : DateTime(d.year, d.month, d.day, t.hour, t.minute).toIso8601String();
        });
      case 'dropdown':
        final cur = entry[f.key] as String?;
        final isOther = cur != null && cur.startsWith(otherPrefix);
        final listed = cur != null && f.options.any((o) => o.value == cur);
        // an option that was retired after this answer was chosen stays selectable so a correction does not lose it
        final stale = cur != null && !isOther && !listed;
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          DropdownButtonFormField<String>(
            key: ValueKey('$id-dd-$isOther-$stale'),
            initialValue: isOther ? _otherKey : (listed || stale ? cur : null),
            decoration: deco.copyWith(helperText: widget.notes[path]),
            isExpanded: true,
            items: [
              for (final o in f.options) DropdownMenuItem(value: o.value, child: Text(o.label)),
              if (stale) DropdownMenuItem(value: cur, child: const Text('Previous choice (no longer listed)')),
              if (f.allowOther) const DropdownMenuItem(value: _otherKey, child: Text('Other…')),
            ],
            onChanged: (v) => v == _otherKey ? set(otherPrefix) : set(v),
          ),
          if (isOther)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: TextFormField(
                key: ValueKey('$id-other'),
                initialValue: cur.substring(otherPrefix.length),
                maxLength: 100,
                decoration: InputDecoration(labelText: 'Specify the type *', errorText: err),
                onChanged: (t) => set('$otherPrefix${t.trim()}'),
              ),
            ),
        ]);
      case 'radio':
        return InputDecorator(
          decoration: deco,
          child: RadioGroup<String>(
            groupValue: entry[f.key] as String?,
            onChanged: set,
            child: Column(children: [
              for (final o in f.options) RadioListTile<String>(title: Text(o.label), value: o.value, dense: true),
            ]),
          ),
        );
      case 'checkbox':
        return CheckboxListTile(
          key: ValueKey(id),
          contentPadding: EdgeInsets.zero,
          title: Text(label),
          subtitle: err == null ? null : Text(err, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          value: entry[f.key] == true,
          onChanged: (v) => _changed(() => entry[f.key] = v == true),
        );
      case 'multi_select':
        final sel = ((entry[f.key] as List?) ?? const []).cast<String>();
        return InputDecorator(
          decoration: deco,
          child: Wrap(spacing: 8, children: [
            for (final o in f.options)
              FilterChip(label: Text(o.label), selected: sel.contains(o.value), onSelected: (on) => set(on ? [...sel, o.value] : sel.where((x) => x != o.value).toList())),
          ]),
        );
      case 'photo' || 'photos':
        return _PhotoField(
          field: f,
          label: label,
          error: err,
          note: widget.notes[path],
          ids: f.type == 'photo' ? [if (entry[f.key] is String) entry[f.key] as String] : ((entry[f.key] as List?) ?? const []).cast<String>(),
          multiple: f.type == 'photos',
          onCapture: (gallery) async {
            final id = await widget.onCapturePhoto(f, fromGallery: gallery);
            if (id == null) return;
            if (f.type == 'photo') {
              final old = entry[f.key];
              if (old is String) await widget.onDiscardPhoto(old); // retake replaces
              set(id);
            } else {
              set([...((entry[f.key] as List?) ?? const []).cast<String>(), id]);
            }
          },
          onRemove: (pid) async {
            await widget.onDiscardPhoto(pid);
            f.type == 'photo' ? set(null) : set(((entry[f.key] as List).cast<String>()).where((x) => x != pid).toList());
          },
        );
      case 'location':
        final v = entry[f.key] as Map?;
        return InputDecorator(
          decoration: deco,
          child: Row(children: [
            Expanded(child: Text(v == null ? 'Not captured' : '${(v['latitude'] as num).toStringAsFixed(6)}, ${(v['longitude'] as num).toStringAsFixed(6)}')),
            TextButton.icon(
              icon: const Icon(Icons.my_location),
              label: const Text('Capture'),
              onPressed: () async {
                final fix = await ref.read(locationServiceProvider).currentFix();
                if (!mounted) return;
                if (fix.hasFix) {
                  set({'latitude': fix.latitude, 'longitude': fix.longitude});
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Location unavailable (${fix.status.replaceAll('_', ' ')})')));
                }
              },
            ),
          ]),
        );
      default:
        // Unreachable for validated schemas; fail safe rather than render something wrong.
        return Text('Unsupported field "${f.label}"', style: TextStyle(color: Theme.of(context).colorScheme.error));
    }
  }

  Widget _picker(FieldDef f, Map<String, dynamic> entry, InputDecoration deco, String id, Future<String?> Function() pick) {
    final v = entry[f.key] as String?;
    return InkWell(
      key: ValueKey(id),
      onTap: () async {
        final r = await pick();
        if (r != null) _changed(() => entry[f.key] = r);
      },
      child: InputDecorator(decoration: deco.copyWith(suffixIcon: const Icon(Icons.calendar_today)), child: Text(v ?? 'Select')),
    );
  }
}

const _otherKey = '__other__';

class _Flag extends StatelessWidget {
  const _Flag(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(color: Brand.roof50, borderRadius: BorderRadius.circular(10), border: Border.all(color: Brand.roof200)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.flag_rounded, size: 18, color: Brand.roof700),
          const SizedBox(width: 6),
          Expanded(child: Text('Reviewer: $text', style: const TextStyle(color: Brand.roof700, fontWeight: FontWeight.w500))),
        ]),
      );
}

class _PhotoField extends ConsumerWidget {
  const _PhotoField({required this.field, required this.label, required this.error, this.note, required this.ids, required this.multiple, required this.onCapture, required this.onRemove});
  final FieldDef field;
  final String label;
  final String? error;
  final String? note;
  final List<String> ids;
  final bool multiple;
  final Future<void> Function(bool gallery) onCapture;
  final Future<void> Function(String id) onRemove;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // For photo lists, validation.max is the maximum photo count.
    final maxPhotos = multiple ? (field.validation['max'] as num?)?.toInt() : 1;
    final canAdd = maxPhotos == null || ids.length < maxPhotos;
    return InputDecorator(
      decoration: InputDecoration(labelText: label, errorText: error, contentPadding: const EdgeInsets.fromLTRB(14, 18, 14, 14)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (note != null) _Flag(note!),
        if (ids.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Wrap(spacing: 10, runSpacing: 10, children: [
              for (final id in ids)
                SizedBox(
                  width: 96,
                  height: 96,
                  child: Stack(fit: StackFit.expand, children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: ref.watch(photoPathProvider(id)).maybeWhen(
                            data: (p) => p == null
                                ? const ColoredBox(color: Brand.navy50, child: Icon(Icons.broken_image_outlined, color: Brand.muted))
                                : Image.file(File(p), width: 96, height: 96, fit: BoxFit.cover),
                            orElse: () => const ColoredBox(color: Brand.navy50),
                          ),
                    ),
                    Positioned(
                      right: 4,
                      top: 4,
                      child: IconButton.filled(
                        tooltip: 'Remove photo',
                        iconSize: 14,
                        visualDensity: VisualDensity.compact,
                        style: IconButton.styleFrom(backgroundColor: Brand.navy900.withValues(alpha: 0.75), foregroundColor: Colors.white, minimumSize: const Size(26, 26), padding: EdgeInsets.zero),
                        icon: const Icon(Icons.close_rounded),
                        onPressed: () => onRemove(id),
                      ),
                    ),
                  ]),
                ),
            ]),
          ),
        Wrap(spacing: 8, runSpacing: 8, children: [
          if (canAdd)
            OutlinedButton.icon(icon: const Icon(Icons.photo_camera_outlined), label: Text(multiple && ids.isNotEmpty ? 'Add another photo' : 'Take photo'), onPressed: () => onCapture(false)),
          if (ids.isNotEmpty && !multiple) OutlinedButton.icon(icon: const Icon(Icons.refresh_rounded), label: const Text('Retake'), onPressed: () => onCapture(false)),
          if (field.allowGallery && canAdd) OutlinedButton.icon(icon: const Icon(Icons.photo_library_outlined), label: const Text('Gallery'), onPressed: () => onCapture(true)),
        ]),
        if (multiple && maxPhotos != null)
          Padding(padding: const EdgeInsets.only(top: 8), child: Text('${ids.length} of $maxPhotos photos', style: const TextStyle(color: Brand.muted, fontSize: 12.5))),
      ]),
    );
  }
}

String locationLabel(LocationFix f) => f.hasFix ? '${f.latitude!.toStringAsFixed(5)}, ${f.longitude!.toStringAsFixed(5)}' : 'unavailable';

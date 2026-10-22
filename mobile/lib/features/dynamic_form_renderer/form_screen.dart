import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/providers.dart';
import '../../app/theme.dart';
import '../../database/database.dart';
import '../submissions/review_updates.dart';
import 'form_schema.dart';
import 'form_view.dart';

/// Loads a draft, autosaves edits (restored after an app restart), validates and submits locally.
class FormScreen extends ConsumerStatefulWidget {
  const FormScreen({super.key, required this.draftId});
  final String draftId;
  @override
  ConsumerState<FormScreen> createState() => _FormScreenState();
}

class _FormScreenState extends ConsumerState<FormScreen> {
  Draft? _draft;
  LocalSubmission? _original; // set when this draft corrects a report that was sent back
  Map<String, String> _notes = {};
  FormSchema? _schema;
  Map<String, dynamic> _answers = {};
  Map<String, String> _errors = {};
  String? _loadError;
  bool _submitting = false;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final db = ref.read(databaseProvider);
    final d = await (db.select(db.drafts)..where((t) => t.id.equals(widget.draftId))).getSingleOrNull();
    if (d == null) return setState(() => _loadError = 'This draft no longer exists.');
    final schema = await ref.read(formsRepositoryProvider).schemaFor(d.formId, d.formVersion);
    if (schema == null) return setState(() => _loadError = 'This form version is not available offline.');
    LocalSubmission? original;
    if (d.correctsLocalId != null) {
      original = await (db.select(db.localSubmissions)..where((t) => t.localId.equals(d.correctsLocalId!))).getSingleOrNull();
    }
    setState(() {
      _draft = d;
      _original = original;
      _notes = flagsOf(original?.reviewFlagsJson);
      _schema = schema;
      _answers = Map<String, dynamic>.from(jsonDecode(d.answersJson) as Map);
    });
  }

  void _autosave() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 500), _saveNow);
  }

  Future<void> _saveNow() => ref.read(formsRepositoryProvider).saveDraft(widget.draftId, _answers);

  @override
  void dispose() {
    _debounce?.cancel();
    if (_draft != null) _saveNow(); // flush pending edits
    super.dispose();
  }

  Future<void> _submit() async {
    final auth = ref.read(authProvider);
    setState(() => _submitting = true);
    try {
      await _saveNow();
      final outcome = await ref.read(submitServiceProvider).submit(userId: auth.userId, draftId: widget.draftId, schema: _schema!, answers: _answers);
      if (!mounted) return;
      if (!outcome.ok) {
        setState(() => _errors = {for (final e in outcome.errors) e.path: e.message});
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Please fix ${outcome.errors.length} highlighted field(s)')));
        return;
      }
      _draft = null; // draft was consumed by the submit transaction
      ref.read(syncProvider.notifier).trigger('submit');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_original == null ? 'Saved on this device. It will sync automatically.' : 'Correction saved on this device. It will be sent automatically.')));
      context.go('/history');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loadError != null) return Scaffold(appBar: AppBar(), body: Center(child: Text(_loadError!)));
    final schema = _schema;
    if (schema == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      appBar: AppBar(title: Text(_original == null ? '${schema.title} v${schema.version}' : 'Correct ${_original!.reference ?? 'report'}'), actions: [
        TextButton(onPressed: _submitting ? null : () async { await _saveNow(); if (context.mounted) context.pop(); }, child: const Text('Save draft')),
      ]),
      body: Column(children: [
        if (_original != null)
          Container(
            width: double.infinity,
            decoration: const BoxDecoration(color: Brand.roof50, border: Border(bottom: BorderSide(color: Brand.roof200))),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Reviewer\'s feedback${_original!.reviewReason == null ? '' : ': ${_original!.reviewReason}'}', style: const TextStyle(fontWeight: FontWeight.w700, color: Brand.roof700)),
              if (_original!.reviewComment != null) Padding(padding: const EdgeInsets.only(top: 2), child: Text(_original!.reviewComment!, style: const TextStyle(color: Brand.ink))),
              const SizedBox(height: 6),
              const Text('Fix the flagged items, then tap Resubmit. Your corrected version is saved on this phone first and sent when you are online. The earlier version stays in the history.', style: TextStyle(fontSize: 12, color: Brand.muted, height: 1.35)),
            ]),
          ),
        Expanded(
          child: DynamicFormView(
            schema: schema,
            answers: _answers,
            errors: _errors,
            notes: _notes,
            onChanged: () {
              if (_errors.isNotEmpty) setState(() => _errors = {});
              _autosave();
            },
            onCapturePhoto: (field, {bool fromGallery = false}) => ref.read(photoServiceProvider).capture(draftId: widget.draftId, fromGallery: fromGallery && field.allowGallery),
            onDiscardPhoto: (id) => ref.read(photoServiceProvider).discard(id),
          ),
        ),
        Container(
          decoration: BoxDecoration(
            color: Colors.white,
            border: const Border(top: BorderSide(color: Brand.line)),
            boxShadow: [BoxShadow(color: Brand.navy900.withValues(alpha: 0.06), blurRadius: 12, offset: const Offset(0, -4))],
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const Row(children: [
                  Icon(Icons.schedule_rounded, size: 15, color: Brand.muted),
                  SizedBox(width: 6),
                  Expanded(child: Text('Time and location are recorded automatically when you submit.', style: TextStyle(fontSize: 12, color: Brand.muted))),
                ]),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(onPressed: _submitting ? null : _submit, child: Text(_submitting ? 'Saving…' : (_original == null ? 'Submit' : 'Resubmit'))),
                ),
              ]),
            ),
          ),
        ),
      ]),
    );
  }
}

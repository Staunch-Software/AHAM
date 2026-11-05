/// Pure-Dart model + validation for the server-defined form schema.
/// Mirrors backend/app/services/form_schema.py. Schemas are validated on download and
/// anything unsupported is rejected (fail safe) instead of being rendered incorrectly.
library;

import 'dart:convert';

const supportedFieldTypes = {
  'text', 'multiline_text', 'integer', 'decimal', 'date', 'time', 'datetime',
  'dropdown', 'radio', 'checkbox', 'multi_select', 'phone', 'email',
  'photo', 'photos', 'location', 'readonly_text', 'heading',
};
const displayOnlyTypes = {'readonly_text', 'heading'};
const _optionTypes = {'dropdown', 'radio', 'multi_select'};
const _optionSources = {'person_types'};
const otherPrefix = 'other:';
const _conditionOps = {'eq', 'neq', 'in', 'not_empty'};
const _ruleKeys = {'min_length', 'max_length', 'min', 'max', 'pattern'};
const _maxEntries = 50;
const _defaultMaxText = 5000;
final _idRe = RegExp(r'^[a-z][a-z0-9_]{0,63}$');
final _phoneRe = RegExp(r'^\+?[0-9][0-9 \-()]{6,19}$');
final _emailRe = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
final _dateRe = RegExp(r'^\d{4}-\d{2}-\d{2}$');
final _timeRe = RegExp(r'^\d{2}:\d{2}(:\d{2})?$');

class SchemaException implements Exception {
  SchemaException(this.errors);
  final List<String> errors;
  @override
  String toString() => 'SchemaException: ${errors.join('; ')}';
}

class OptionDef {
  const OptionDef(this.value, this.label);
  final String value;
  final String label;
}

class FieldDef {
  FieldDef({
    required this.key,
    required this.label,
    required this.type,
    this.required = false,
    this.options = const [],
    this.validation = const {},
    this.visibleIf,
    this.allowGallery = false,
    this.defaultValue,
    this.optionsSource,
    this.allowOther = false,
  });
  /// Name of a managed list (e.g. person_types) whose current options the server injects into the downloaded form.
  final String? optionsSource;
  /// A dropdown may let the agent type a custom value; it is stored as `other:` followed by the text.
  final bool allowOther;
  final String key, label, type;
  final bool required;
  final List<OptionDef> options;
  final Map<String, dynamic> validation;
  final Map<String, dynamic>? visibleIf;
  final bool allowGallery; // gallery picking only when the form policy says so
  final dynamic defaultValue;
}

class SectionDef {
  SectionDef({required this.id, required this.title, required this.repeatable, required this.minItems, required this.maxItems, required this.fields});
  final String id, title;
  final bool repeatable;
  final int minItems, maxItems;
  final List<FieldDef> fields;
}

class FormSchema {
  FormSchema({required this.formId, required this.version, required this.title, required this.sections});
  final String formId, title;
  final int version;
  final List<SectionDef> sections;

  factory FormSchema.parse(String json) => FormSchema.fromJson(jsonDecode(json));

  factory FormSchema.fromJson(dynamic j) {
    final errs = <String>[];
    if (j is! Map) throw SchemaException(['schema must be an object']);
    if (j['form_id'] is! String || (j['form_id'] as String).isEmpty) errs.add('form_id required');
    if (j['title'] is! String) errs.add('title required');
    if (j['version'] is! int || (j['version'] as int) < 1) errs.add('version must be a positive integer');
    final rawSections = j['sections'];
    if (rawSections is! List || rawSections.isEmpty || rawSections.length > 30) {
      throw SchemaException([...errs, 'sections must be a list of 1..30']);
    }
    final sections = <SectionDef>[];
    final seen = <String>{};
    for (var si = 0; si < rawSections.length; si++) {
      final s = rawSections[si];
      final p = 'sections[$si]';
      if (s is! Map || s['id'] is! String || !_idRe.hasMatch(s['id'] as String)) {
        errs.add('$p.id invalid');
        continue;
      }
      if (!seen.add(s['id'] as String)) errs.add('$p.id duplicate');
      final repeatable = s['repeatable'] == true;
      final lo = (s['min_items'] ?? 0), hi = (s['max_items'] ?? _maxEntries);
      if (repeatable && !(lo is int && hi is int && lo >= 0 && lo <= hi && hi <= _maxEntries)) {
        errs.add('$p min_items/max_items invalid');
      }
      final rawFields = s['fields'];
      if (rawFields is! List || rawFields.isEmpty || rawFields.length > 100) {
        errs.add('$p.fields must be a list of 1..100');
        continue;
      }
      final keys = <String>{};
      final fields = <FieldDef>[];
      for (var fi = 0; fi < rawFields.length; fi++) {
        final f = _parseField(rawFields[fi], '$p.fields[$fi]', keys, errs);
        if (f != null) fields.add(f);
      }
      sections.add(SectionDef(
        id: s['id'] as String,
        title: (s['title'] as String?) ?? s['id'] as String,
        repeatable: repeatable,
        minItems: repeatable && lo is int ? lo : 0,
        maxItems: repeatable && hi is int ? hi : 1,
        fields: fields,
      ));
    }
    if (errs.isNotEmpty) throw SchemaException(errs);
    return FormSchema(formId: j['form_id'] as String, version: j['version'] as int, title: j['title'] as String, sections: sections);
  }

  static FieldDef? _parseField(dynamic f, String p, Set<String> keys, List<String> errs) {
    if (f is! Map) {
      errs.add('$p must be an object');
      return null;
    }
    final key = f['key'];
    if (key is! String || !_idRe.hasMatch(key)) {
      errs.add('$p.key invalid');
      return null;
    }
    if (!keys.add(key)) errs.add('$p.key duplicate');
    final type = f['type'];
    if (type is! String || !supportedFieldTypes.contains(type)) {
      errs.add('$p.type unsupported: $type');
      return null;
    }
    if (f['label'] is! String) errs.add('$p.label required');
    var options = <OptionDef>[];
    final source = f['options_source'];
    if (source != null && (!_optionSources.contains(source) || type != 'dropdown')) {
      errs.add('$p.options_source unsupported: $source');
    }
    if (_optionTypes.contains(type)) {
      final o = f['options'];
      final listOk = o is List && o.every((x) => x is Map && x['value'] is String && x['label'] is String);
      // a managed list may be empty (nothing configured yet); a fixed list may not
      if (!listOk && !(source != null && o == null)) {
        errs.add('$p.options must be a list of {value,label}');
      } else if (listOk && o.isEmpty && source == null) {
        errs.add('$p.options must not be empty');
      } else if (listOk) {
        options = [for (final x in o) OptionDef(x['value'] as String, x['label'] as String)];
      }
    }
    final rules = f['validation'] ?? <String, dynamic>{};
    if (rules is! Map || rules.keys.any((k) => !_ruleKeys.contains(k))) {
      errs.add('$p.validation has unsupported rules');
    } else if (rules['pattern'] != null) {
      try {
        if ((rules['pattern'] as String).length > 200) throw const FormatException();
        RegExp(rules['pattern'] as String);
      } catch (_) {
        errs.add('$p.validation.pattern invalid');
      }
    }
    final cond = f['visible_if'];
    if (cond != null && !(cond is Map && _conditionOps.contains(cond['op']) && cond['field'] is String)) {
      errs.add('$p.visible_if malformed');
    }
    return FieldDef(
      key: key,
      label: (f['label'] as String?) ?? key,
      type: type,
      required: f['required'] == true,
      options: options,
      validation: rules is Map ? Map<String, dynamic>.from(rules) : const {},
      visibleIf: cond is Map ? Map<String, dynamic>.from(cond) : null,
      allowGallery: f['allow_gallery'] == true,
      defaultValue: f['default'],
      optionsSource: source is String ? source : null,
      allowOther: f['allow_other'] == true,
    );
  }
}

class FieldError {
  const FieldError(this.path, this.fieldKey, this.message);
  final String path; // e.g. meeting_details[0].contact_name
  final String? fieldKey;
  final String message;
  @override
  String toString() => '$path: $message';
}

bool isEmptyValue(dynamic v) => v == null || v == '' || (v is List && v.isEmpty) || (v is Map && v.isEmpty);

bool isVisible(FieldDef f, Map<String, dynamic> entry) {
  final c = f.visibleIf;
  if (c == null) return true;
  final v = entry[c['field']];
  switch (c['op']) {
    case 'eq':
      return v == c['value'];
    case 'neq':
      return v != c['value'];
    case 'in':
      return (c['value'] as List?)?.contains(v) ?? false;
    default:
      return !isEmptyValue(v);
  }
}

/// Answers shape: non-repeatable section -> Map, repeatable section -> List<Map>.
Map<String, dynamic> emptyAnswers(FormSchema s) => {
      for (final sec in s.sections)
        sec.id: sec.repeatable
            ? [for (var i = 0; i < (sec.minItems < 1 ? 1 : sec.minItems); i++) newEntry(sec)]
            : newEntry(sec),
    };

/// A fresh entry with defaults applied. A date field with `"default": "today"` is pre-filled with the
/// device's current date (the agent can still change it); the time of a photo or submission is never typed:
/// it is captured by the app at the moment it happens.
Map<String, dynamic> newEntry(SectionDef sec, {DateTime? now}) {
  final today = now ?? DateTime.now();
  String iso(DateTime d) => '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  return {
    for (final f in sec.fields)
      if (f.defaultValue != null) f.key: (f.type == 'date' && f.defaultValue == 'today') ? iso(today) : f.defaultValue,
  };
}

List<FieldError> validateAnswers(FormSchema schema, Map<String, dynamic> answers) {
  final errors = <FieldError>[];
  for (final sec in schema.sections) {
    final data = answers[sec.id];
    final List entries;
    if (sec.repeatable) {
      entries = data is List ? data : const [];
      if (entries.length < sec.minItems || entries.length > sec.maxItems) {
        errors.add(FieldError(sec.id, sec.id, 'entries must be ${sec.minItems}..${sec.maxItems}'));
      }
    } else {
      entries = [data ?? <String, dynamic>{}];
    }
    for (var i = 0; i < entries.length; i++) {
      final base = sec.repeatable ? '${sec.id}[$i]' : sec.id;
      final entry = entries[i];
      if (entry is! Map) {
        errors.add(FieldError(base, sec.id, 'must be an object'));
        continue;
      }
      final e = Map<String, dynamic>.from(entry);
      for (final f in sec.fields) {
        if (displayOnlyTypes.contains(f.type) || !isVisible(f, e)) continue;
        final msg = _check(f, e[f.key]);
        if (msg != null) errors.add(FieldError('$base.${f.key}', f.key, msg));
      }
    }
  }
  return errors;
}

String? _check(FieldDef f, dynamic v) {
  if (isEmptyValue(v)) return f.required ? 'Required' : null;
  final r = f.validation;
  switch (f.type) {
    case 'text' || 'multiline_text' || 'phone' || 'email':
      if (v is! String) return 'Must be text';
      if (v.length > ((r['max_length'] as int?) ?? _defaultMaxText)) return 'Too long';
      if (v.length < ((r['min_length'] as int?) ?? 0)) return 'Too short';
      if (f.type == 'phone' && !_phoneRe.hasMatch(v)) return 'Invalid phone number';
      if (f.type == 'email' && !_emailRe.hasMatch(v)) return 'Invalid email';
      if (r['pattern'] != null && !RegExp('^(?:${r['pattern']})\$').hasMatch(v)) return 'Invalid format';
    case 'integer' || 'decimal':
      if (v is! num || (f.type == 'integer' && v is! int)) return 'Must be a number';
      if (r['min'] != null && v < (r['min'] as num)) return 'Must be at least ${r['min']}';
      if (r['max'] != null && v > (r['max'] as num)) return 'Must be at most ${r['max']}';
    case 'date':
      if (v is! String || !_dateRe.hasMatch(v) || DateTime.tryParse(v) == null) return 'Invalid date';
    case 'time':
      if (v is! String || !_timeRe.hasMatch(v)) return 'Invalid time';
    case 'datetime':
      if (v is! String || DateTime.tryParse(v) == null) return 'Invalid date/time';
    case 'dropdown' || 'radio':
      if (f.allowOther && v is String && v.startsWith(otherPrefix)) {
        final text = v.substring(otherPrefix.length).trim();
        if (text.isEmpty || text.length > 100) return 'Enter the other type (1-100 characters)';
      } else if (!f.options.any((o) => o.value == v)) {
        return 'Not a valid option';
      }
    case 'multi_select':
      if (v is! List || !v.every((x) => f.options.any((o) => o.value == x))) return 'Not a valid option';
    case 'checkbox':
      if (v is! bool) return 'Must be true/false';
    case 'photo':
      if (v is! String) return 'Invalid photo';
    case 'photos':
      if (v is! List || !v.every((x) => x is String)) return 'Invalid photos';
      // For photo lists, validation.min / validation.max are photo COUNTS.
      if (r['max'] != null && v.length > (r['max'] as num)) return 'At most ${r['max']} photos';
      if (r['min'] != null && v.length < (r['min'] as num)) return 'At least ${r['min']} photos';
    case 'location':
      if (v is! Map || v['latitude'] is! num || v['longitude'] is! num) return 'Invalid location';
      final lat = v['latitude'] as num, lon = v['longitude'] as num;
      if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return 'Invalid location';
  }
  return null;
}

/// Photo ids referenced by the answers (for attaching photos to a submission / cleaning orphans).
Set<String> photoIdsIn(FormSchema schema, Map<String, dynamic> answers) {
  final ids = <String>{};
  for (final sec in schema.sections) {
    final data = answers[sec.id];
    final entries = sec.repeatable ? (data is List ? data : const []) : [data];
    for (final e in entries) {
      if (e is! Map) continue;
      for (final f in sec.fields) {
        final v = e[f.key];
        if (f.type == 'photo' && v is String) ids.add(v);
        if (f.type == 'photos' && v is List) ids.addAll(v.whereType<String>());
      }
    }
  }
  return ids;
}

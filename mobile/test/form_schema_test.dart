import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:fieldsync_mobile/features/dynamic_form_renderer/form_schema.dart';
import 'package:fieldsync_mobile/features/submissions/history_screen.dart' show flagTarget;
import 'package:fieldsync_mobile/features/submissions/review_updates.dart' show flagsOf;

// Same shape as database/seed/field_meeting_report.v1.json
// Round-trip through JSON so nested lists/maps are fully dynamic (mutable with any shape), like real server JSON.
Map<String, dynamic> seed() => jsonDecode(jsonEncode(_rawSeed())) as Map<String, dynamic>;

Map<String, dynamic> _rawSeed() => {
      'form_id': 'field_meeting_report',
      'version': 1,
      'title': 'Field Meeting Report',
      'sections': [
        {
          'id': 'meeting_details',
          'title': 'Meeting Details',
          'repeatable': true,
          'min_items': 1,
          'max_items': 3,
          'fields': [
            {'key': 'contact_category', 'label': 'Contact Category', 'type': 'text', 'required': true},
            {'key': 'contact_name', 'label': 'Name', 'type': 'text', 'required': true, 'validation': {'max_length': 10}},
            {'key': 'contact_whatsapp', 'label': 'WhatsApp', 'type': 'phone'},
            {'key': 'meeting_date', 'label': 'Date', 'type': 'date', 'required': true},
            {'key': 'meeting_photo', 'label': 'Photo', 'type': 'photo'},
          ],
        }
      ],
    };

Map<String, dynamic> validEntry() => {'contact_category': 'Dealer', 'contact_name': 'Ravi', 'meeting_date': '2026-10-10'};

void main() {
  test('seed schema parses', () {
    final s = FormSchema.fromJson(seed());
    expect(s.sections.single.repeatable, isTrue);
    expect(s.sections.single.fields.length, 5);
  });

  test('unsupported types, bad rules and malformed conditions are rejected', () {
    for (final mutate in <void Function(Map<String, dynamic>)>[
      (m) => (m['sections'][0]['fields'][0] as Map)['type'] = 'javascript',
      (m) => (m['sections'][0]['fields'][0] as Map)['validation'] = {'eval': '1+1'},
      (m) => (m['sections'][0]['fields'][0] as Map)['validation'] = {'pattern': '(['},
      (m) => (m['sections'][0]['fields'][0] as Map)['visible_if'] = {'field': 'x', 'op': 'exec'},
      (m) => (m['sections'][0]['fields'] as List).add(Map.of((m['sections'][0]['fields'] as List)[0] as Map)),
      (m) => m['sections'] = [],
      (m) => (m['sections'][0]['fields'][0] as Map)['type'] = 'dropdown', // dropdown without options
    ]) {
      final m = seed();
      mutate(m);
      expect(() => FormSchema.fromJson(m), throwsA(isA<SchemaException>()));
    }
  });

  test('required, type, phone and length errors carry stable field paths', () {
    final s = FormSchema.fromJson(seed());
    final errs = validateAnswers(s, {
      'meeting_details': [
        {'contact_name': 'a very long name', 'meeting_date': 'nope', 'contact_whatsapp': 'abc'}
      ]
    });
    final by = {for (final e in errs) e.path: e.message};
    expect(by['meeting_details[0].contact_category'], 'Required');
    expect(by['meeting_details[0].contact_name'], 'Too long');
    expect(by['meeting_details[0].meeting_date'], 'Invalid date');
    expect(by['meeting_details[0].contact_whatsapp'], 'Invalid phone number');
  });

  test('repeatable bounds are enforced', () {
    final s = FormSchema.fromJson(seed());
    expect(validateAnswers(s, {'meeting_details': []}).single.message, contains('entries must be'));
    final four = {'meeting_details': List.generate(4, (_) => validEntry())};
    expect(validateAnswers(s, four).single.message, contains('entries must be 1..3'));
    expect(validateAnswers(s, {'meeting_details': [validEntry(), validEntry()]}), isEmpty);
  });

  test('emptyAnswers honours min_items; conditional fields are skipped when hidden', () {
    final m = seed();
    (m['sections'][0]['fields'] as List).add({
      'key': 'why', 'label': 'Why', 'type': 'text', 'required': true,
      'visible_if': {'field': 'contact_category', 'op': 'eq', 'value': 'Other'},
    });
    final s = FormSchema.fromJson(m);
    expect((emptyAnswers(s)['meeting_details'] as List).length, 1);
    expect(validateAnswers(s, {'meeting_details': [validEntry()]}), isEmpty);
    final other = validEntry()..['contact_category'] = 'Other';
    expect(validateAnswers(s, {'meeting_details': [other]}).single.fieldKey, 'why');
  });

  test('photo ids are collected for attachment', () {
    final s = FormSchema.fromJson(seed());
    final a = {'meeting_details': [validEntry()..['meeting_photo'] = 'p-1', validEntry()]};
    expect(photoIdsIn(s, a), {'p-1'});
  });

  test('multiple photos: count limit, duplicates and today default', () {
    final m = seed();
    final fields = m['sections'][0]['fields'] as List;
    fields
      ..removeWhere((f) => f['key'] == 'meeting_photo')
      ..add({'key': 'meeting_photos', 'label': 'Photos', 'type': 'photos', 'validation': {'max': 2}})
      ..add({'key': 'when', 'label': 'When', 'type': 'date', 'default': 'today'});
    final s = FormSchema.fromJson(m);
    Map<String, dynamic> entry(List photos) => validEntry()..['meeting_photos'] = photos;
    expect(validateAnswers(s, {'meeting_details': [entry(['a', 'b'])]}), isEmpty);
    final over = validateAnswers(s, {'meeting_details': [entry(['a', 'b', 'c'])]});
    expect(over.single.fieldKey, 'meeting_photos');
    expect(over.single.message, 'At most 2 photos');
    expect(photoIdsIn(s, {'meeting_details': [entry(['a', 'b'])]}), {'a', 'b'});
    // "today" is filled by the app from the device date; nothing is typed
    final fresh = newEntry(s.sections.single, now: DateTime(2026, 10, 17, 9, 5));
    expect(fresh['when'], '2026-10-17');
  });

  group('managed dropdown (type of person)', () {
    Map<String, dynamic> managed({bool required = true, bool allowOther = false, List<Map<String, String>>? options}) {
      final m = seed();
      (m['sections'][0]['fields'] as List)[0] = {
        'key': 'contact_category', 'label': 'Type of person', 'type': 'dropdown', 'options_source': 'person_types',
        'required': required, 'allow_other': allowOther, if (options != null) 'options': options,
      };
      return m;
    }

    final opts = [{'value': 'id-dealer', 'label': 'Dealer'}, {'value': 'id-customer', 'label': 'Customer'}];

    test('parses with options injected by the server, or none yet; unknown sources are refused', () {
      final f = FormSchema.fromJson(managed(options: opts)).sections.single.fields.first;
      expect(f.optionsSource, 'person_types');
      expect(f.options.map((o) => o.label), ['Dealer', 'Customer']);
      expect(FormSchema.fromJson(managed()).sections.single.fields.first.options, isEmpty); // nothing configured yet
      final bad = managed();
      ((bad['sections'][0]['fields'] as List)[0] as Map)['options_source'] = 'secrets';
      expect(() => FormSchema.fromJson(bad), throwsA(isA<SchemaException>()));
      final plain = seed();
      ((plain['sections'][0]['fields'] as List)[0] as Map)..['type'] = 'dropdown'..remove('options'); // no source, no options
      expect(() => FormSchema.fromJson(plain), throwsA(isA<SchemaException>()));
    });

    Map<String, dynamic> answers(String? v) => {'meeting_details': [validEntry()..['contact_category'] = v]};

    test('only listed ids are valid; Other needs the setting and a non-empty value', () {
      final s = FormSchema.fromJson(managed(options: opts));
      expect(validateAnswers(s, answers('id-dealer')), isEmpty);
      expect(validateAnswers(s, answers('Dealer')).single.message, 'Not a valid option'); // labels are not ids
      expect(validateAnswers(s, answers('other:Govt officer')).single.message, 'Not a valid option'); // Other is off
      final other = FormSchema.fromJson(managed(options: opts, allowOther: true));
      expect(validateAnswers(other, answers('other:Govt officer')), isEmpty);
      expect(validateAnswers(other, answers('other:   ')).single.message, contains('Enter the other type'));
      expect(validateAnswers(other, answers('other:${'x' * 101}')).single.message, contains('Enter the other type'));
    });

    test('required is controlled by the managed setting', () {
      final req = FormSchema.fromJson(managed(options: opts));
      final entry = validEntry()..remove('contact_category');
      expect(validateAnswers(req, {'meeting_details': [entry]}).single.message, 'Required');
      final optional = FormSchema.fromJson(managed(options: opts, required: false));
      expect(validateAnswers(optional, {'meeting_details': [entry]}), isEmpty);
    });
  });

  group('review helpers', () {
    test('flags are read as path -> note and tolerate bad data', () {
      expect(flagsOf('[{"path":"meeting_details[1]","note":"Which dealer?"}]'), {'meeting_details[1]': 'Which dealer?'});
      expect(flagsOf(null), isEmpty);
      expect(flagsOf('not json'), isEmpty);
    });

    test('flag targets are readable', () {
      expect(flagTarget('meeting_details[1]'), 'Meeting 2');
      expect(flagTarget('meeting_details[0].meeting_photos'), 'Meeting 1 · meeting photos');
      expect(flagTarget('weird'), 'weird');
    });
  });
}

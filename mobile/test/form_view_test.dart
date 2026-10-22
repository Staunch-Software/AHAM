import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fieldsync_mobile/features/dynamic_form_renderer/form_schema.dart';
import 'package:fieldsync_mobile/features/dynamic_form_renderer/form_view.dart';

FormSchema schema() => FormSchema.fromJson({
      'form_id': 'f', 'version': 1, 'title': 'F',
      'sections': [
        {
          'id': 'meetings', 'title': 'Meetings', 'repeatable': true, 'min_items': 1, 'max_items': 2,
          'fields': [
            {'key': 'name', 'label': 'Name', 'type': 'text', 'required': true},
          ],
        }
      ],
    });

void main() {
  testWidgets('repeatable entries can be added up to max and removed down to min; required marker shown', (t) async {
    final s = schema();
    final answers = emptyAnswers(s);
    var changes = 0;
    await t.pumpWidget(ProviderScope(
      child: MaterialApp(
        home: Scaffold(
          body: DynamicFormView(
            schema: s, answers: answers, errors: const {'meetings[0].name': 'Required'},
            onChanged: () => changes++,
            onCapturePhoto: (f, {bool fromGallery = false}) async => null,
            onDiscardPhoto: (_) async {},
          ),
        ),
      ),
    ));
    expect(find.text('Entry 1'), findsOneWidget);
    expect(find.text('Name *'), findsOneWidget);
    expect(find.text('Required'), findsOneWidget);
    expect(find.byTooltip('Remove entry 1'), findsNothing); // at min_items: cannot remove

    await t.tap(find.textContaining('Add meetings entry'));
    await t.pump();
    expect(find.text('Entry 2'), findsOneWidget);
    expect(find.textContaining('Add meetings entry'), findsNothing); // at max_items
    expect((answers['meetings'] as List).length, 2);

    await t.enterText(find.byType(TextFormField).first, 'Ravi');
    expect(((answers['meetings'] as List).first as Map)['name'], 'Ravi');
    expect(changes, greaterThan(1));
  });
}

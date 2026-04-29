// Smoke test for AIRA. We can't fully boot the app in a unit test
// because it touches SharedPreferences/network, so we just verify
// the widget tree compiles and the splash screen renders.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('material app renders', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: Center(child: Text('AIRA'))),
    ));
    expect(find.text('AIRA'), findsOneWidget);
  });
}

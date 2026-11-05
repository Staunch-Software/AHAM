// ignore_for_file: avoid_print
// Diagnostic: does the device deliver GPS fixes to (a) the app's LocationService, (b) Android's LocationManager?
import 'package:fieldsync_mobile/features/location_capture/location_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('location probe', (t) async {
    print('PROBE:READY');
    await Future<void>.delayed(const Duration(seconds: 12)); // host grants permissions
    final svc = await GeolocatorLocationService().currentFix();
    print('PROBE:service status=${svc.status} lat=${svc.latitude} lon=${svc.longitude} acc=${svc.accuracyM} fixAt=${svc.fixAt} src=${svc.source}');
    try {
      final p = await Geolocator.getCurrentPosition(
        locationSettings: AndroidSettings(accuracy: LocationAccuracy.high, forceLocationManager: true, timeLimit: const Duration(seconds: 10)),
      );
      print('PROBE:locationManager lat=${p.latitude} lon=${p.longitude} acc=${p.accuracy} ts=${p.timestamp}');
    } catch (e) {
      print('PROBE:locationManager FAILED $e');
    }
    print('PROBE:DONE');
  }, timeout: const Timeout(Duration(minutes: 3)));
}

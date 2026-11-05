import 'package:geolocator/geolocator.dart';

import '../../core/config.dart';

/// Why we do or don't have coordinates. Must match the backend's LocationStatus values.
class LocationStatus {
  static const obtained = 'obtained';
  static const permissionDenied = 'permission_denied';
  static const servicesDisabled = 'services_disabled';
  static const timeout = 'timeout';
  static const unavailable = 'unavailable';
}

class LocationFix {
  const LocationFix.unavailable(this.status)
      : latitude = null, longitude = null, accuracyM = null, fixAt = null, source = null;
  const LocationFix({required this.latitude, required this.longitude, required this.accuracyM, required this.fixAt, this.source = 'gps'})
      : status = LocationStatus.obtained;
  final double? latitude, longitude, accuracyM;
  final DateTime? fixAt;
  final String status;
  final String? source;
  bool get hasFix => latitude != null && longitude != null;
}

abstract class LocationService {
  /// Always completes within [timeout]; never throws; never fabricates coordinates.
  Future<LocationFix> currentFix({Duration timeout = AppConfig.locationTimeout});
}

class GeolocatorLocationService implements LocationService {
  @override
  Future<LocationFix> currentFix({Duration timeout = AppConfig.locationTimeout}) async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        return const LocationFix.unavailable(LocationStatus.servicesDisabled);
      }
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) perm = await Geolocator.requestPermission();
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        return const LocationFix.unavailable(LocationStatus.permissionDenied);
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: LocationSettings(accuracy: LocationAccuracy.high, timeLimit: timeout),
      ).timeout(timeout + const Duration(seconds: 2)); // belt and braces: some platforms ignore timeLimit
      return LocationFix(
        latitude: pos.latitude,
        longitude: pos.longitude,
        accuracyM: pos.accuracy,
        fixAt: pos.timestamp.toUtc(), // time of the fix as reported by the platform
        source: pos.isMocked ? 'mocked' : 'gps',
      );
    } on Exception catch (e) {
      final timedOut = e.toString().toLowerCase().contains('time');
      return LocationFix.unavailable(timedOut ? LocationStatus.timeout : LocationStatus.unavailable);
    }
  }
}

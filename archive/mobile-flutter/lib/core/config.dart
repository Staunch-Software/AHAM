class AppConfig {
  /// Override per build: --dart-define=API_BASE_URL=https://api.example.com
  /// Default is the Android emulator's alias for the host machine.
  static const apiBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');

  /// Fresh GPS fix budget when pressing Submit / capturing a photo. Never blocks beyond this.
  static const locationTimeout = Duration(seconds: 8);

  /// Chunk size for resumable photo upload.
  static const uploadChunkBytes = 256 * 1024;

  /// After this many failed attempts a submission moves to "Failed" and needs a manual retry.
  static const maxAutoAttempts = 10;
}

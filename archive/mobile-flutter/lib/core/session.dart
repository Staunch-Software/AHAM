import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Credentials live only in OS-protected storage (Keychain / Keystore), never in SQLite.
class SessionStore {
  SessionStore([FlutterSecureStorage? storage])
      : _s = storage ?? const FlutterSecureStorage();
  final FlutterSecureStorage _s;

  static const _access = 'access_token';
  static const _refresh = 'refresh_token';
  static const _userId = 'user_id';

  Future<String?> get accessToken => _s.read(key: _access);
  Future<String?> get refreshToken => _s.read(key: _refresh);
  Future<String?> get userId => _s.read(key: _userId);

  Future<void> saveTokens(String access, String refresh) async {
    await _s.write(key: _access, value: access);
    await _s.write(key: _refresh, value: refresh);
  }

  Future<void> saveUserId(String id) => _s.write(key: _userId, value: id);

  Future<void> clear() async {
    await _s.delete(key: _access);
    await _s.delete(key: _refresh);
    await _s.delete(key: _userId);
  }
}

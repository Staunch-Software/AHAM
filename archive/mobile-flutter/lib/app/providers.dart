import 'dart:async';
import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:drift/drift.dart' show OrderingTerm;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../core/session.dart';
import '../database/database.dart';
import '../features/assigned_forms/forms_repository.dart';
import '../features/location_capture/location_service.dart';
import '../features/photo_capture/photo_service.dart';
import '../features/submissions/review_updates.dart';
import '../features/submissions/submit_service.dart';
import '../features/synchronization/sync_engine.dart';
import '../features/synchronization/sync_wiring.dart';

// ---- Infrastructure (databaseProvider is overridden in main() with the opened DB) ----
final databaseProvider = Provider<AppDatabase>((ref) => throw UnimplementedError('override in main'));
final sessionStoreProvider = Provider((ref) => SessionStore());
final locationServiceProvider = Provider<LocationService>((ref) => GeolocatorLocationService());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(sessionStoreProvider), onSessionExpired: () => ref.read(authProvider.notifier).sessionExpired());
});

final formsRepositoryProvider = Provider((ref) => FormsRepository(ref.watch(databaseProvider), ref.watch(apiClientProvider)));
final photoServiceProvider = Provider((ref) => PhotoService(ref.watch(databaseProvider), ref.watch(locationServiceProvider)));
final reviewUpdatesProvider = Provider((ref) => ReviewUpdates(ref.watch(databaseProvider), ref.watch(apiClientProvider)));
final submitServiceProvider = Provider((ref) => SubmitService(ref.watch(databaseProvider), ref.watch(locationServiceProvider)));

// ---- Auth ----
enum AuthStatus { unknown, signedOut, signedIn }

class AuthState {
  const AuthState(this.status, {this.user, this.error});
  final AuthStatus status;
  final Map<String, dynamic>? user;
  final String? error;
  String get userId => user!['id'] as String;
  String get name => (user?['full_name'] as String?) ?? '';
}

final authProvider = NotifierProvider<AuthController, AuthState>(AuthController.new);

class AuthController extends Notifier<AuthState> {
  static const _meKey = 'me';
  @override
  AuthState build() => const AuthState(AuthStatus.unknown);

  /// Restores the session from secure storage. Works offline using the cached profile.
  Future<void> restore() async {
    final session = ref.read(sessionStoreProvider);
    final db = ref.read(databaseProvider);
    if (await session.refreshToken == null) {
      state = const AuthState(AuthStatus.signedOut);
      return;
    }
    final cached = await db.getValue(_meKey);
    if (cached != null) {
      state = AuthState(AuthStatus.signedIn, user: jsonDecode(cached) as Map<String, dynamic>);
      unawaited(_refreshProfile()); // best effort; offline is fine
      ref.read(syncProvider.notifier).trigger('start');
    } else {
      try {
        await _refreshProfile(throwOnError: true);
      } catch (_) {
        state = const AuthState(AuthStatus.signedOut);
      }
    }
  }

  Future<void> _refreshProfile({bool throwOnError = false}) async {
    try {
      final r = await ref.read(apiClientProvider).dio.get('/auth/me');
      final me = Map<String, dynamic>.from(r.data as Map);
      if (me['role'] != 'agent') throw StateError('not_agent');
      await ref.read(databaseProvider).setValue(_meKey, jsonEncode(me));
      await ref.read(sessionStoreProvider).saveUserId(me['id'] as String);
      state = AuthState(AuthStatus.signedIn, user: me);
      unawaited(ref.read(formsRepositoryProvider).refresh());
    } catch (e) {
      if (throwOnError) rethrow;
    }
  }

  Future<void> login(String email, String password) async {
    final session = ref.read(sessionStoreProvider);
    try {
      final r = await ref.read(apiClientProvider).dio.post('/auth/login', data: {'email': email.trim(), 'password': password});
      await session.saveTokens(r.data['access_token'] as String, r.data['refresh_token'] as String);
      await _refreshProfile(throwOnError: true);
      ref.read(syncProvider.notifier).trigger('login');
    } on StateError {
      await session.clear();
      state = const AuthState(AuthStatus.signedOut, error: 'This app is for field agents only.');
    } on DioException catch (e) {
      final bad = e.response?.statusCode == 401;
      state = AuthState(AuthStatus.signedOut, error: bad ? 'Invalid email or password' : apiErrorMessage(e));
    }
  }

  /// Signing out never deletes unsynced work; it stays on the device, tied to its owner.
  Future<void> logout() async {
    final session = ref.read(sessionStoreProvider);
    final refresh = await session.refreshToken;
    try {
      if (refresh != null) await ref.read(apiClientProvider).dio.post('/auth/logout', data: {'refresh_token': refresh});
    } catch (_) {}
    await session.clear();
    state = const AuthState(AuthStatus.signedOut);
  }

  void sessionExpired() => state = const AuthState(AuthStatus.signedOut, error: 'Your session expired. Please sign in again.');
}

// ---- Sync ----
class SyncStatus {
  const SyncStatus({this.running = false, this.lastSyncAt, this.lastMessage});
  final bool running;
  final DateTime? lastSyncAt;
  final String? lastMessage;
}

final syncProvider = NotifierProvider<SyncController, SyncStatus>(SyncController.new);

class SyncController extends Notifier<SyncStatus> {
  static const _lastKey = 'last_sync_at';
  SyncEngine? _engine;
  Timer? _timer;
  StreamSubscription? _conn;
  bool _disposed = false;

  @override
  SyncStatus build() {
    _disposed = false;
    ref.onDispose(() {
      _disposed = true; // an in-flight sync may still finish after teardown: it must not touch `ref`/state
      _timer?.cancel();
      _conn?.cancel();
    });
    // Connectivity returning is a *hint* to try; the engine still copes with an unreachable API.
    _conn = Connectivity().onConnectivityChanged.listen((r) {
      if (r.any((c) => c != ConnectivityResult.none)) trigger('connectivity');
    });
    ref.read(databaseProvider).getValue(_lastKey).then((v) {
      if (v != null && !_disposed) state = SyncStatus(lastSyncAt: DateTime.tryParse(v)?.toLocal());
    });
    return const SyncStatus();
  }

  SyncEngine get _e => _engine ??= buildEngine(ref.read(databaseProvider), ref.read(apiClientProvider), ref.read(sessionStoreProvider));

  /// reason: start | login | connectivity | resume | manual | timer
  Future<void> trigger(String reason) async {
    if (_e.running || ref.read(authProvider).status != AuthStatus.signedIn) return;
    state = SyncStatus(running: true, lastSyncAt: state.lastSyncAt, lastMessage: state.lastMessage);
    final db = ref.read(databaseProvider); // resolve everything before awaiting
    SyncResult? r;
    String? msg;
    try {
      r = await _e.run();
      if (r.signedOut) msg = 'Sign in again to sync';
    } catch (e) {
      msg = 'Sync error: $e';
    }
    if (_disposed) return;
    // Pick up reviewer decisions and refreshed form options on every sync (silent when offline).
    if (r != null && !r.signedOut) {
      try {
        await ref.read(reviewUpdatesProvider).pull();
        await ref.read(formsRepositoryProvider).refresh();
      } catch (_) {}
      if (_disposed) return;
    }
    final done = DateTime.now();
    if (r != null && !r.signedOut) {
      try {
        await db.setValue(_lastKey, done.toUtc().toIso8601String());
      } catch (_) {} // best effort bookkeeping
      if (_disposed) return;
    }
    state = SyncStatus(lastSyncAt: r != null && !r.signedOut ? done : state.lastSyncAt, lastMessage: msg);
    _timer?.cancel();
    final wake = r?.nextWake; // backoff: come back when the earliest retry is due
    if (wake != null) {
      final delay = wake.difference(DateTime.now().toUtc());
      _timer = Timer(delay.isNegative ? const Duration(seconds: 1) : delay + const Duration(milliseconds: 250), () => trigger('timer'));
    }
  }
}

// ---- Data streams for UI ----
final submissionsProvider = StreamProvider<List<LocalSubmission>>((ref) {
  final db = ref.watch(databaseProvider);
  final uid = ref.watch(authProvider.select((a) => a.user?['id'] as String?));
  if (uid == null) return const Stream.empty();
  return (db.select(db.localSubmissions)
        ..where((t) => t.userId.equals(uid))
        ..orderBy([(t) => OrderingTerm.desc(t.createdAt)]))
      .watch();
});

final draftsProvider = StreamProvider<List<Draft>>((ref) {
  final db = ref.watch(databaseProvider);
  final uid = ref.watch(authProvider.select((a) => a.user?['id'] as String?));
  if (uid == null) return const Stream.empty();
  return (db.select(db.drafts)
        ..where((t) => t.userId.equals(uid))
        ..orderBy([(t) => OrderingTerm.desc(t.updatedAt)]))
      .watch();
});

final assignedFormsProvider = StreamProvider<List<AssignedForm>>((ref) => ref.watch(formsRepositoryProvider).watch());

final photoPathProvider = FutureProvider.family<String?, String>((ref, id) async {
  final db = ref.watch(databaseProvider);
  return (await (db.select(db.localPhotos)..where((t) => t.id.equals(id))).getSingleOrNull())?.filePath;
});

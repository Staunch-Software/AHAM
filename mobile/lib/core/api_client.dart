import 'package:dio/dio.dart';

import 'config.dart';
import 'session.dart';

/// Dio client with bearer auth and single-flight token refresh.
/// A refresh that is *rejected* (401) ends the session; a refresh that merely fails
/// to reach the server (offline) keeps the session so the agent can keep working.
class ApiClient {
  ApiClient(this.session, {this.onSessionExpired})
      : dio = Dio(BaseOptions(
          baseUrl: '${AppConfig.apiBaseUrl}/api/v1',
          connectTimeout: const Duration(seconds: 10),
          sendTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 30),
          validateStatus: (s) => s != null && s < 400,
        )) {
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (o, h) async {
        final t = await session.accessToken;
        if (t != null) o.headers['Authorization'] = 'Bearer $t';
        h.next(o);
      },
      onError: (e, h) async {
        final req = e.requestOptions;
        final isAuthCall = req.path.startsWith('/auth/');
        if (e.response?.statusCode == 401 && req.extra['retried'] != true && !isAuthCall) {
          try {
            await _refresh();
            req.extra['retried'] = true;
            return h.resolve(await dio.fetch(req));
          } on DioException catch (re) {
            return h.next(re);
          }
        }
        h.next(e);
      },
    ));
  }

  final SessionStore session;
  final void Function()? onSessionExpired;
  final Dio dio;
  Future<void>? _refreshing;

  Future<void> _refresh() => _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);

  Future<void> _doRefresh() async {
    final refresh = await session.refreshToken;
    if (refresh == null) throw DioException(requestOptions: RequestOptions(path: '/auth/refresh'), type: DioExceptionType.cancel);
    final bare = Dio(BaseOptions(baseUrl: dio.options.baseUrl, connectTimeout: dio.options.connectTimeout, receiveTimeout: dio.options.receiveTimeout));
    try {
      final r = await bare.post('/auth/refresh', data: {'refresh_token': refresh});
      await session.saveTokens(r.data['access_token'] as String, r.data['refresh_token'] as String);
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) {
        await session.clear();
        onSessionExpired?.call();
      }
      rethrow;
    }
  }
}

/// Extracts a human message from a FastAPI error body.
String apiErrorMessage(Object e) {
  if (e is DioException) {
    final d = e.response?.data;
    if (d is Map) {
      final detail = d['detail'];
      if (detail is String) return detail;
      if (detail is Map && detail['message'] is String) return detail['message'] as String;
      if (detail is Map && detail['errors'] is List) {
        return (detail['errors'] as List).map((x) => '${x['field_id'] ?? ''}: ${x['message']}').join('; ');
      }
    }
    return switch (e.type) {
      DioExceptionType.connectionError || DioExceptionType.connectionTimeout => 'Cannot reach the server',
      DioExceptionType.receiveTimeout || DioExceptionType.sendTimeout => 'The server took too long to respond',
      _ => e.message ?? 'Request failed',
    };
  }
  return e.toString();
}

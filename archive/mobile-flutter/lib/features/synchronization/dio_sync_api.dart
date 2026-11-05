import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../core/api_client.dart';
import 'sync_engine.dart';

/// Maps HTTP outcomes onto the engine's error taxonomy.
class DioSyncApi implements SyncApi {
  DioSyncApi(this.client);
  final ApiClient client;
  Dio get _d => client.dio;

  Never _fail(DioException e) {
    final code = e.response?.statusCode;
    if (code == null) throw RetryableSyncError(apiErrorMessage(e)); // offline / DNS / timeout
    if (code == 401) throw AuthSyncError();
    if (code >= 500 || code == 408 || code == 429) throw RetryableSyncError('Server error ($code)');
    final d = e.response?.data;
    String? errCode;
    if (d is Map && d['detail'] is Map) errCode = (d['detail'] as Map)['code'] as String?;
    throw PermanentSyncError(apiErrorMessage(e), code: errCode);
  }

  int? _received(DioException e) {
    final d = e.response?.data;
    if (d is Map && d['detail'] is Map) return ((d['detail'] as Map)['received_bytes'] as num?)?.toInt();
    return null;
  }

  @override
  Future<PhotoServerState> initiatePhoto(PendingPhoto p) async {
    try {
      final r = await _d.post('/uploads/initiate', data: {
        'photo_id': p.id,
        'mime_type': p.mimeType,
        'size_bytes': p.sizeBytes,
        'sha256': p.sha256,
        'photo_captured_at_device': p.capturedAt.toUtc().toIso8601String(),
        if (p.latitude != null && p.longitude != null) ...{
          'latitude': p.latitude, 'longitude': p.longitude, 'accuracy_m': p.accuracyM,
          'location_fix_at_device': p.fixAt?.toUtc().toIso8601String(),
          'location_source': p.locationSource,
        },
        'location_status': p.locationStatus,
      });
      return PhotoServerState(
        complete: r.data['upload_status'] == 'complete',
        receivedBytes: (r.data['received_bytes'] as num?)?.toInt() ?? 0,
      );
    } on DioException catch (e) {
      _fail(e);
    }
  }

  @override
  Future<int> putChunk(String photoId, int offset, int total, List<int> bytes) async {
    try {
      final r = await _d.put(
        '/uploads/$photoId',
        data: Uint8List.fromList(bytes), // bytes (not a stream) so an auth-refresh retry can resend
        options: Options(headers: {
          'Content-Range': 'bytes $offset-${offset + bytes.length - 1}/$total',
          Headers.contentTypeHeader: 'application/octet-stream',
        }),
      );
      return (r.data['received_bytes'] as num).toInt();
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) throw OffsetMismatch(_received(e) ?? 0);
      _fail(e);
    }
  }

  @override
  Future<void> completePhoto(String photoId) async {
    try {
      await _d.post('/uploads/$photoId/complete');
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      if (code == 409) throw OffsetMismatch(_received(e) ?? 0);
      if (code == 422 && '${e.response?.data}'.contains('Checksum mismatch')) throw ChecksumMismatch();
      _fail(e);
    }
  }

  @override
  Future<Receipt> submit(PendingSubmission s) async {
    try {
      final r = await _d.post('/submissions', data: {
        'idempotency_key': s.idempotencyKey,
        'client_submission_id': s.localId,
        'form_id': s.formId,
        'form_version': s.formVersion,
        'answers': jsonDecode(s.answersJson),
        'submitted_at_device': s.submittedAtUtc.toUtc().toIso8601String(),
        'device_tz_offset_min': s.tzOffsetMin,
        if (s.correctsServerId != null) 'corrects': {'submission_id': s.correctsServerId, 'base_revision': s.baseRevision ?? 1},
        'location': {
          if (s.latitude != null && s.longitude != null) ...{
            'latitude': s.latitude, 'longitude': s.longitude, 'accuracy_m': s.accuracyM,
            'fix_at_device': s.fixAt?.toUtc().toIso8601String(),
          },
          'status': s.locationStatus,
        },
      });
      final d = r.data as Map;
      return Receipt(
        serverId: d['id'] as String,
        receivedAt: DateTime.tryParse('${d['received_at_server']}'),
        acceptedAt: DateTime.tryParse('${d['accepted_at_server']}'),
        duplicate: d['duplicate'] == true,
        reference: d['reference'] as String?,
        revision: (d['revision'] as num?)?.toInt() ?? 1,
      );
    } on DioException catch (e) {
      _fail(e);
    }
  }
}

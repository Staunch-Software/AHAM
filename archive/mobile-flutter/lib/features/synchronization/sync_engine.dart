/// Offline sync engine. Pure Dart (no Flutter/Drift/Dio imports) so it is unit-testable.
///
/// Delivery is at-least-once with idempotent processing:
///  * photos use a stable id and a resumable protocol, so re-uploading never duplicates;
///  * the submission carries the same idempotency key (and byte-identical body) on every retry,
///    so a timeout after the server committed just returns the existing record;
///  * a submission is marked accepted only after the server acknowledges it.
library;

import 'dart:io';
import 'dart:math';

import '../../core/config.dart';

// ---- States (stored in LocalSubmissions.state) ----
class SubState {
  static const queued = 'queued';
  static const uploading = 'uploading';
  static const syncPending = 'sync_pending';
  static const accepted = 'accepted';
  static const failed = 'failed';
  static const conflict = 'conflict';
  static const inFlight = [queued, uploading, syncPending];
}

/// Human label. Never says "accepted" without a server acknowledgement.
String stateLabel(String state, int attempts) => switch (state) {
      SubState.queued => attempts == 0 ? 'Saved offline' : 'Sync pending',
      SubState.uploading => 'Uploading',
      SubState.syncPending => 'Sync pending',
      SubState.accepted => 'Accepted by server',
      SubState.failed => 'Failed',
      SubState.conflict => 'Conflict — needs attention',
      _ => state,
    };

// ---- Errors ----
sealed class SyncError implements Exception {
  SyncError(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Network failure, timeout, 5xx, 429: try again later with backoff.
class RetryableSyncError extends SyncError {
  RetryableSyncError(super.message);
}

/// Server rejected it for good (validation, outdated schema, revoked access): needs a human.
class PermanentSyncError extends SyncError {
  PermanentSyncError(super.message, {this.code});
  final String? code;
}

/// 401 after a refresh attempt: stop syncing, keep everything queued, don't burn attempts.
class AuthSyncError extends SyncError {
  AuthSyncError() : super('Signed out');
}

/// Server's byte position differs from ours — re-initiate to learn where to resume.
class OffsetMismatch extends SyncError {
  OffsetMismatch(this.received) : super('offset mismatch');
  final int received;
}

/// Server discarded a corrupt upload; restart from byte 0.
class ChecksumMismatch extends SyncError {
  ChecksumMismatch() : super('checksum mismatch');
}

// ---- Data ----
class PendingPhoto {
  PendingPhoto({
    required this.id, required this.filePath, required this.sha256, required this.sizeBytes, required this.mimeType,
    required this.capturedAt, this.latitude, this.longitude, this.accuracyM, this.fixAt,
    required this.locationStatus, this.locationSource, required this.uploaded,
  });
  final String id, filePath, sha256, mimeType, locationStatus;
  final int sizeBytes;
  final DateTime capturedAt;
  final double? latitude, longitude, accuracyM;
  final DateTime? fixAt;
  final String? locationSource;
  final bool uploaded;
}

class PendingSubmission {
  PendingSubmission({
    required this.localId, required this.idempotencyKey, required this.formId, required this.formVersion,
    required this.answersJson, required this.submittedAtUtc, required this.tzOffsetMin,
    this.latitude, this.longitude, this.accuracyM, this.fixAt, required this.locationStatus,
    required this.attempts, required this.photos, this.correctsServerId, this.baseRevision,
  });
  /// Set when this submission corrects a report that was sent back: the server id and revision it corrects.
  final String? correctsServerId;
  final int? baseRevision;
  final String localId, idempotencyKey, formId, answersJson, locationStatus;
  final int formVersion, tzOffsetMin, attempts;
  final DateTime submittedAtUtc;
  final double? latitude, longitude, accuracyM;
  final DateTime? fixAt;
  final List<PendingPhoto> photos;
}

class PhotoServerState {
  const PhotoServerState({required this.complete, required this.receivedBytes});
  final bool complete;
  final int receivedBytes;
}

class Receipt {
  const Receipt({required this.serverId, this.receivedAt, this.acceptedAt, this.duplicate = false, this.reference, this.revision = 1});
  final String serverId;
  final DateTime? receivedAt, acceptedAt;
  final bool duplicate;
  final String? reference; // FS-2026-0042
  final int revision;
}

abstract class SyncStore {
  /// Submissions of [userId] in an in-flight state whose nextAttemptAt <= now.
  Future<List<PendingSubmission>> due(String userId, DateTime now);
  Future<DateTime?> nextWake(String userId); // earliest future nextAttemptAt among in-flight rows
  Future<void> update(String localId, {String? state, int? attempts, DateTime? nextAttemptAt, String? lastError, bool clearError = false});
  Future<void> markPhotoUploaded(String photoId);
  Future<void> markAccepted(String localId, Receipt r);
}

abstract class SyncApi {
  Future<PhotoServerState> initiatePhoto(PendingPhoto p);
  /// Returns total bytes the server now holds. Throws [OffsetMismatch].
  Future<int> putChunk(String photoId, int offset, int total, List<int> bytes);
  /// Throws [OffsetMismatch] (incomplete) or [ChecksumMismatch].
  Future<void> completePhoto(String photoId);
  Future<Receipt> submit(PendingSubmission s);
}

typedef ChunkReader = Future<List<int>> Function(String path, int offset, int length);

Future<List<int>> readFileChunk(String path, int offset, int length) async {
  final f = await File(path).open();
  try {
    await f.setPosition(offset);
    return await f.read(length);
  } finally {
    await f.close();
  }
}

class SyncResult {
  SyncResult({this.accepted = 0, this.retrying = 0, this.needsAttention = 0, this.signedOut = false, this.nextWake});
  int accepted, retrying, needsAttention;
  bool signedOut;
  DateTime? nextWake;
}

class SyncEngine {
  SyncEngine({
    required this.store,
    required this.api,
    required this.userId,
    this.chunkReader = readFileChunk,
    this.fileExists,
    DateTime Function()? now,
    Random? random,
    this.chunkSize = AppConfig.uploadChunkBytes,
    this.maxAttempts = AppConfig.maxAutoAttempts,
  })  : _now = now ?? DateTime.now,
        _rnd = random ?? Random();

  final SyncStore store;
  final SyncApi api;
  final Future<String?> Function() userId;
  final ChunkReader chunkReader;
  final Future<bool> Function(String path)? fileExists;
  final DateTime Function() _now;
  final Random _rnd;
  final int chunkSize, maxAttempts;
  bool _running = false;

  bool get running => _running;

  /// Exponential backoff with jitter: ~5s, 10s, 20s ... capped at 5 min (jitter 50–100%).
  Duration backoff(int attempts) {
    final base = min(300, 5 * pow(2, attempts).toInt());
    return Duration(milliseconds: (base * 1000 * (0.5 + _rnd.nextDouble() * 0.5)).round());
  }

  /// Processes everything that is due. Re-entrant calls while running are ignored.
  /// Submissions are processed one at a time (bounded concurrency = 1) so a large offline
  /// backlog can't flood the API or the device.
  Future<SyncResult> run() async {
    final result = SyncResult();
    if (_running) return result;
    _running = true;
    try {
      final uid = await userId();
      if (uid == null) return result..signedOut = true;
      for (final s in await store.due(uid, _now())) {
        try {
          await _process(s);
          result.accepted++;
        } on AuthSyncError {
          await store.update(s.localId, state: SubState.queued); // no attempt burned
          result.signedOut = true;
          break;
        } on PermanentSyncError catch (e) {
          await store.update(s.localId, state: SubState.conflict, lastError: e.message);
          result.needsAttention++;
        } on RetryableSyncError catch (e) {
          final attempts = s.attempts + 1;
          final failed = attempts >= maxAttempts;
          await store.update(
            s.localId,
            state: failed ? SubState.failed : SubState.queued,
            attempts: attempts,
            nextAttemptAt: _now().add(backoff(attempts)),
            lastError: e.message,
          );
          failed ? result.needsAttention++ : result.retrying++;
        }
      }
      result.nextWake = await store.nextWake(uid);
      return result;
    } finally {
      _running = false;
    }
  }

  Future<void> _process(PendingSubmission s) async {
    for (final p in s.photos.where((p) => !p.uploaded)) {
      await store.update(s.localId, state: SubState.uploading);
      await _checkFile(p);
      await _uploadPhoto(p);
      await store.markPhotoUploaded(p.id);
    }
    await store.update(s.localId, state: SubState.syncPending);
    final receipt = await api.submit(s);
    await store.markAccepted(s.localId, receipt);
  }

  Future<void> _checkFile(PendingPhoto p) async {
    final exists = fileExists != null ? await fileExists!(p.filePath) : await File(p.filePath).exists();
    if (!exists) throw PermanentSyncError('A photo file is missing from this device', code: 'photo_missing');
  }

  Future<void> _uploadPhoto(PendingPhoto p) async {
    for (var round = 0; round < 3; round++) {
      final st = await api.initiatePhoto(p); // idempotent; tells us where to resume
      if (st.complete) return;
      var offset = st.receivedBytes;
      try {
        while (offset < p.sizeBytes) {
          final len = min(chunkSize, p.sizeBytes - offset);
          final bytes = await chunkReader(p.filePath, offset, len);
          if (bytes.length != len) throw PermanentSyncError('Photo file changed on device', code: 'photo_changed');
          offset = await api.putChunk(p.id, offset, p.sizeBytes, bytes);
        }
        await api.completePhoto(p.id);
        return;
      } on OffsetMismatch {
        continue; // re-initiate and resume from the server's position
      } on ChecksumMismatch {
        continue; // server discarded the corrupt copy; restart from 0
      }
    }
    throw RetryableSyncError('Photo upload did not complete');
  }
}

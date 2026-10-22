import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:fieldsync_mobile/features/synchronization/sync_engine.dart';

// ---- Fakes ----
class FakeStore implements SyncStore {
  final Map<String, PendingSubmission> subs = {};
  final Map<String, String> state = {};
  final Map<String, int> attempts = {};
  final Map<String, String?> lastError = {};
  final Map<String, DateTime> next = {};
  final Set<String> uploaded = {};
  final Map<String, Receipt> receipts = {};

  void add(PendingSubmission s, {DateTime? at}) {
    subs[s.localId] = s;
    state[s.localId] = SubState.queued;
    attempts[s.localId] = s.attempts;
    next[s.localId] = at ?? DateTime.utc(2026, 1, 1);
  }

  @override
  Future<List<PendingSubmission>> due(String userId, DateTime now) async => [
        for (final s in subs.values)
          if (SubState.inFlight.contains(state[s.localId]) && !next[s.localId]!.isAfter(now))
            PendingSubmission(
              localId: s.localId, idempotencyKey: s.idempotencyKey, formId: s.formId, formVersion: s.formVersion,
              answersJson: s.answersJson, submittedAtUtc: s.submittedAtUtc, tzOffsetMin: s.tzOffsetMin,
              locationStatus: s.locationStatus, attempts: attempts[s.localId]!,
              photos: [for (final p in s.photos) _photo(p, uploaded.contains(p.id))],
            ),
      ];

  PendingPhoto _photo(PendingPhoto p, bool up) => PendingPhoto(
      id: p.id, filePath: p.filePath, sha256: p.sha256, sizeBytes: p.sizeBytes, mimeType: p.mimeType,
      capturedAt: p.capturedAt, locationStatus: p.locationStatus, uploaded: up);

  @override
  Future<DateTime?> nextWake(String userId) async {
    final t = [for (final e in next.entries) if (SubState.inFlight.contains(state[e.key])) e.value];
    return t.isEmpty ? null : t.reduce((a, b) => a.isBefore(b) ? a : b);
  }

  @override
  Future<void> update(String id, {String? state, int? attempts, DateTime? nextAttemptAt, String? lastError, bool clearError = false}) async {
    if (state != null) this.state[id] = state;
    if (attempts != null) this.attempts[id] = attempts;
    if (nextAttemptAt != null) next[id] = nextAttemptAt;
    if (lastError != null || clearError) this.lastError[id] = lastError;
  }

  @override
  Future<void> markPhotoUploaded(String photoId) async => uploaded.add(photoId);

  @override
  Future<void> markAccepted(String id, Receipt r) async {
    state[id] = SubState.accepted;
    receipts[id] = r;
  }
}

class FakeApi implements SyncApi {
  final calls = <String>[];
  final Map<String, int> held = {}; // photoId -> bytes server has
  final Set<String> done = {};
  final Set<String> committed = {}; // idempotency keys the "server" has stored
  final Map<String, String> serverIds = {};
  Object? Function(String op)? failOn; // return an error to throw for an operation
  int submitCalls = 0;

  Object? _fail(String op) => failOn?.call(op);

  @override
  Future<PhotoServerState> initiatePhoto(PendingPhoto p) async {
    calls.add('init:${p.id}');
    if (_fail('init') case final Object e) throw e;
    return PhotoServerState(complete: done.contains(p.id), receivedBytes: held[p.id] ?? 0);
  }

  @override
  Future<int> putChunk(String id, int offset, int total, List<int> bytes) async {
    calls.add('put:$id@$offset+${bytes.length}');
    if (_fail('put') case final Object e) throw e;
    if (offset != (held[id] ?? 0)) throw OffsetMismatch(held[id] ?? 0);
    return held[id] = offset + bytes.length;
  }

  @override
  Future<void> completePhoto(String id) async {
    calls.add('complete:$id');
    if (_fail('complete') case final Object e) throw e;
    done.add(id);
  }

  @override
  Future<Receipt> submit(PendingSubmission s) async {
    submitCalls++;
    calls.add('submit:${s.idempotencyKey}');
    final dup = committed.contains(s.idempotencyKey);
    committed.add(s.idempotencyKey);
    final id = serverIds.putIfAbsent(s.idempotencyKey, () => 'srv-${serverIds.length + 1}');
    if (_fail('submit') case final Object e) throw e; // may throw AFTER the server committed (timeout case)
    return Receipt(serverId: id, duplicate: dup);
  }
}

PendingPhoto photo(String id, {int size = 100}) => PendingPhoto(
    id: id, filePath: '/f/$id.jpg', sha256: 'x', sizeBytes: size, mimeType: 'image/jpeg',
    capturedAt: DateTime.utc(2026, 1, 1, 4, 30), locationStatus: 'obtained', uploaded: false);

PendingSubmission sub(String id, {List<PendingPhoto> photos = const [], String key = ''}) => PendingSubmission(
    localId: id, idempotencyKey: key.isEmpty ? 'key-$id' : key, formId: 'f', formVersion: 1, answersJson: '{}',
    submittedAtUtc: DateTime.utc(2026, 1, 1, 4, 45), tzOffsetMin: 330, locationStatus: 'obtained', attempts: 0, photos: photos);

void main() {
  late FakeStore store;
  late FakeApi api;
  late DateTime clock;

  SyncEngine engine({int chunk = 40, int maxAttempts = 3}) => SyncEngine(
        store: store, api: api, userId: () async => 'u1', now: () => clock, random: Random(1), chunkSize: chunk,
        maxAttempts: maxAttempts,
        chunkReader: (path, offset, length) async => List.filled(length, 7),
        fileExists: (p) async => !p.contains('missing'),
      );

  setUp(() {
    store = FakeStore();
    api = FakeApi();
    clock = DateTime.utc(2026, 6, 1);
  });

  test('happy path: photos upload in chunks, then submission is accepted only after acknowledgement', () async {
    store.add(sub('a', photos: [photo('p1', size: 100)]));
    final r = await engine().run();
    expect(r.accepted, 1);
    expect(api.calls.where((c) => c.startsWith('put:p1')).length, 3); // 40 + 40 + 20
    expect(store.uploaded, {'p1'});
    expect(store.state['a'], SubState.accepted);
    expect(store.receipts['a']!.serverId, 'srv-1');
    // photo upload strictly precedes the submission
    expect(api.calls.indexWhere((c) => c.startsWith('complete:')), lessThan(api.calls.indexWhere((c) => c.startsWith('submit:'))));
  });

  test('offline: retryable failure keeps the record queued with backoff and never marks it accepted', () async {
    store.add(sub('a'));
    api.failOn = (op) => op == 'submit' ? RetryableSyncError('Cannot reach the server') : null;
    final r = await engine().run();
    expect(r.retrying, 1);
    expect(store.state['a'], SubState.queued);
    expect(store.attempts['a'], 1);
    expect(store.lastError['a'], 'Cannot reach the server');
    expect(store.next['a']!.isAfter(clock), isTrue);
    expect(store.receipts, isEmpty);
    // not due again until the backoff elapses
    expect((await engine().run()).accepted, 0);
    expect(api.submitCalls, 1);
  });

  test('timeout after server commit: retry reuses the SAME idempotency key and ends with one logical record', () async {
    store.add(sub('a', key: 'idem-1'));
    var first = true;
    api.failOn = (op) {
      if (op == 'submit' && first) {
        first = false;
        return RetryableSyncError('timeout'); // server committed, client never heard back
      }
      return null;
    };
    await engine().run();
    expect(api.committed, {'idem-1'});
    clock = clock.add(const Duration(minutes: 10));
    final r = await engine().run();
    expect(r.accepted, 1);
    expect(api.committed.length, 1); // still one logical submission
    expect(api.calls.where((c) => c.startsWith('submit:')).toSet(), {'submit:idem-1'});
    expect(store.receipts['a']!.duplicate, isTrue);
    expect(store.state['a'], SubState.accepted);
  });

  test('interrupted upload resumes from the server position; no re-send of held bytes', () async {
    store.add(sub('a', photos: [photo('p1', size: 100)]));
    api.held['p1'] = 40;
    await engine().run();
    expect(api.calls.contains('put:p1@0+40'), isFalse);
    expect(api.calls.contains('put:p1@40+40'), isTrue);
    expect(store.state['a'], SubState.accepted);
  });

  test('offset mismatch and checksum mismatch re-initiate instead of failing', () async {
    store.add(sub('a', photos: [photo('p1', size: 80)]));
    var offsetOnce = true, checksumOnce = true;
    api.failOn = (op) {
      if (op == 'put' && offsetOnce) {
        offsetOnce = false;
        api.held['p1'] = 40; // server actually has more than the client thought
        return OffsetMismatch(40);
      }
      if (op == 'complete' && checksumOnce) {
        checksumOnce = false;
        api.held['p1'] = 0; // server discarded the corrupt copy
        return ChecksumMismatch();
      }
      return null;
    };
    await engine().run();
    expect(offsetOnce || checksumOnce, isFalse); // both recovery paths were exercised
    expect(store.state['a'], SubState.accepted);
    expect(api.done, {'p1'});
    // after the checksum failure the whole file was sent again from byte 0
    expect(api.calls.where((c) => c == 'put:p1@0+40').length, 2);
  });

  test('permanent rejection becomes Conflict, preserves the record and is not retried automatically', () async {
    store.add(sub('a'));
    api.failOn = (op) => op == 'submit' ? PermanentSyncError('Form version no longer accepted', code: 'schema_outdated') : null;
    final r = await engine().run();
    expect(r.needsAttention, 1);
    expect(store.state['a'], SubState.conflict);
    expect(store.lastError['a'], contains('no longer accepted'));
    clock = clock.add(const Duration(days: 1));
    await engine().run();
    expect(api.submitCalls, 1); // conflict is not in-flight => no automatic retry
  });

  test('401 stops the run, burns no attempts and leaves everything queued', () async {
    store.add(sub('a'));
    store.add(sub('b'));
    api.failOn = (op) => op == 'submit' ? AuthSyncError() : null;
    final r = await engine().run();
    expect(r.signedOut, isTrue);
    expect(api.submitCalls, 1); // did not continue to 'b'
    expect(store.attempts['a'], 0);
    expect(store.state['a'], SubState.queued);
    expect(store.state['b'], SubState.queued);
  });

  test('missing photo file is a conflict that needs attention, not an endless retry', () async {
    store.add(sub('a', photos: [PendingPhoto(id: 'p', filePath: '/f/missing.jpg', sha256: 'x', sizeBytes: 10, mimeType: 'image/jpeg', capturedAt: clock, locationStatus: 'unavailable', uploaded: false)]));
    await engine().run();
    expect(store.state['a'], SubState.conflict);
    expect(api.submitCalls, 0);
  });

  test('after maxAttempts retryable failures the record becomes Failed (manual retry)', () async {
    store.add(sub('a'));
    api.failOn = (op) => op == 'submit' ? RetryableSyncError('Server error (503)') : null;
    for (var i = 0; i < 3; i++) {
      clock = clock.add(const Duration(hours: 1));
      await engine().run();
    }
    expect(store.state['a'], SubState.failed);
    expect(store.attempts['a'], 3);
  });

  test('backoff grows exponentially with jitter and is capped at 5 minutes', () {
    final e = engine();
    final d1 = e.backoff(1).inMilliseconds, d4 = e.backoff(4).inMilliseconds, d20 = e.backoff(20).inMilliseconds;
    expect(d1, inInclusiveRange(5000, 10000));
    expect(d4, inInclusiveRange(40000, 80000));
    expect(d20, inInclusiveRange(150000, 300000));
  });

  test('uploaded photos are not re-uploaded when a later step is retried', () async {
    store.add(sub('a', photos: [photo('p1', size: 40)]));
    var failOnce = true;
    api.failOn = (op) {
      if (op == 'submit' && failOnce) {
        failOnce = false;
        return RetryableSyncError('boom');
      }
      return null;
    };
    await engine().run();
    clock = clock.add(const Duration(minutes: 10));
    await engine().run();
    expect(api.calls.where((c) => c.startsWith('put:')).length, 1);
    expect(store.state['a'], SubState.accepted);
  });

  test('state labels never claim server acceptance for unacknowledged records', () {
    expect(stateLabel(SubState.queued, 0), 'Saved offline');
    expect(stateLabel(SubState.queued, 2), 'Sync pending');
    expect(stateLabel(SubState.syncPending, 0), isNot(contains('Accepted')));
    expect(stateLabel(SubState.accepted, 1), 'Accepted by server');
  });

  test('re-entrant run is ignored while a run is in progress', () async {
    store.add(sub('a'));
    final e = engine();
    final first = e.run();
    final second = await e.run();
    await first;
    expect(second.accepted, 0);
    expect(api.submitCalls, 1);
  });
}

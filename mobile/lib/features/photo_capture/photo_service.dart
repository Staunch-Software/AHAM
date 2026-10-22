import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:drift/drift.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../../database/database.dart';
import '../location_capture/location_service.dart';

/// Captures a photo and, at that same moment, its own time and GPS fix. Those are stored with
/// the photo and are never replaced by the submission's time/location.
class PhotoService {
  PhotoService(this.db, this.location, {ImagePicker? picker}) : _picker = picker ?? ImagePicker();
  final AppDatabase db;
  final LocationService location;
  final ImagePicker _picker;
  static const _uuid = Uuid();

  /// Returns the new photo id, or null if the user cancelled.
  /// [fromGallery] must only be true when the field's policy allows it.
  Future<String?> capture({required String draftId, bool fromGallery = false}) async {
    // Fix the capture instant before anything slow (compression, location) happens.
    final capturedAt = DateTime.now().toUtc();
    final picked = await _picker.pickImage(
      source: fromGallery ? ImageSource.gallery : ImageSource.camera,
      maxWidth: 1920, // compress: readable evidence, bounded size
      imageQuality: 80,
    );
    if (picked == null) return null;
    // Gallery images keep the timestamp of picking; the capture time of an old file is untrustworthy,
    // which is why gallery use is policy-gated and the server also stores EXIF time separately.
    final fix = await location.currentFix();

    final id = _uuid.v4();
    final dir = Directory(p.join((await getApplicationDocumentsDirectory()).path, 'photos'));
    await dir.create(recursive: true);
    final dest = File(p.join(dir.path, '$id.jpg')); // app-private storage survives restarts
    await File(picked.path).copy(dest.path);
    final bytes = await dest.readAsBytes();

    await db.into(db.localPhotos).insert(LocalPhotosCompanion.insert(
          id: id,
          draftId: Value(draftId),
          filePath: dest.path,
          sha256: sha256.convert(bytes).toString(),
          sizeBytes: bytes.length,
          mimeType: 'image/jpeg',
          capturedAtDevice: capturedAt,
          latitude: Value(fix.latitude),
          longitude: Value(fix.longitude),
          accuracyM: Value(fix.accuracyM),
          locationFixAtDevice: Value(fix.fixAt),
          locationStatus: fix.hasFix ? LocationStatus.obtained : fix.status,
          locationSource: Value(fix.source),
        ));
    return id;
  }

  /// Removes a not-yet-submitted photo (retake / remove before submission).
  Future<void> discard(String photoId) async {
    final row = await (db.select(db.localPhotos)..where((t) => t.id.equals(photoId))).getSingleOrNull();
    if (row == null || row.submissionLocalId != null) return; // never delete evidence already queued
    await (db.delete(db.localPhotos)..where((t) => t.id.equals(photoId))).go();
    final f = File(row.filePath);
    if (await f.exists()) await f.delete();
  }
}

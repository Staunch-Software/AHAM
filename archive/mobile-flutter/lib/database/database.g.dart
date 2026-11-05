// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $CachedFormsTable extends CachedForms
    with TableInfo<$CachedFormsTable, CachedForm> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $CachedFormsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _formIdMeta = const VerificationMeta('formId');
  @override
  late final GeneratedColumn<String> formId = GeneratedColumn<String>(
    'form_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _versionMeta = const VerificationMeta(
    'version',
  );
  @override
  late final GeneratedColumn<int> version = GeneratedColumn<int>(
    'version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _schemaJsonMeta = const VerificationMeta(
    'schemaJson',
  );
  @override
  late final GeneratedColumn<String> schemaJson = GeneratedColumn<String>(
    'schema_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _fetchedAtMeta = const VerificationMeta(
    'fetchedAt',
  );
  @override
  late final GeneratedColumn<DateTime> fetchedAt = GeneratedColumn<DateTime>(
    'fetched_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    formId,
    version,
    title,
    schemaJson,
    fetchedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'cached_forms';
  @override
  VerificationContext validateIntegrity(
    Insertable<CachedForm> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('form_id')) {
      context.handle(
        _formIdMeta,
        formId.isAcceptableOrUnknown(data['form_id']!, _formIdMeta),
      );
    } else if (isInserting) {
      context.missing(_formIdMeta);
    }
    if (data.containsKey('version')) {
      context.handle(
        _versionMeta,
        version.isAcceptableOrUnknown(data['version']!, _versionMeta),
      );
    } else if (isInserting) {
      context.missing(_versionMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
        _titleMeta,
        title.isAcceptableOrUnknown(data['title']!, _titleMeta),
      );
    } else if (isInserting) {
      context.missing(_titleMeta);
    }
    if (data.containsKey('schema_json')) {
      context.handle(
        _schemaJsonMeta,
        schemaJson.isAcceptableOrUnknown(data['schema_json']!, _schemaJsonMeta),
      );
    } else if (isInserting) {
      context.missing(_schemaJsonMeta);
    }
    if (data.containsKey('fetched_at')) {
      context.handle(
        _fetchedAtMeta,
        fetchedAt.isAcceptableOrUnknown(data['fetched_at']!, _fetchedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_fetchedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {formId, version};
  @override
  CachedForm map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return CachedForm(
      formId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}form_id'],
      )!,
      version: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}version'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      )!,
      schemaJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}schema_json'],
      )!,
      fetchedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}fetched_at'],
      )!,
    );
  }

  @override
  $CachedFormsTable createAlias(String alias) {
    return $CachedFormsTable(attachedDatabase, alias);
  }
}

class CachedForm extends DataClass implements Insertable<CachedForm> {
  final String formId;
  final int version;
  final String title;
  final String schemaJson;
  final DateTime fetchedAt;
  const CachedForm({
    required this.formId,
    required this.version,
    required this.title,
    required this.schemaJson,
    required this.fetchedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['form_id'] = Variable<String>(formId);
    map['version'] = Variable<int>(version);
    map['title'] = Variable<String>(title);
    map['schema_json'] = Variable<String>(schemaJson);
    map['fetched_at'] = Variable<DateTime>(fetchedAt);
    return map;
  }

  CachedFormsCompanion toCompanion(bool nullToAbsent) {
    return CachedFormsCompanion(
      formId: Value(formId),
      version: Value(version),
      title: Value(title),
      schemaJson: Value(schemaJson),
      fetchedAt: Value(fetchedAt),
    );
  }

  factory CachedForm.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return CachedForm(
      formId: serializer.fromJson<String>(json['formId']),
      version: serializer.fromJson<int>(json['version']),
      title: serializer.fromJson<String>(json['title']),
      schemaJson: serializer.fromJson<String>(json['schemaJson']),
      fetchedAt: serializer.fromJson<DateTime>(json['fetchedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'formId': serializer.toJson<String>(formId),
      'version': serializer.toJson<int>(version),
      'title': serializer.toJson<String>(title),
      'schemaJson': serializer.toJson<String>(schemaJson),
      'fetchedAt': serializer.toJson<DateTime>(fetchedAt),
    };
  }

  CachedForm copyWith({
    String? formId,
    int? version,
    String? title,
    String? schemaJson,
    DateTime? fetchedAt,
  }) => CachedForm(
    formId: formId ?? this.formId,
    version: version ?? this.version,
    title: title ?? this.title,
    schemaJson: schemaJson ?? this.schemaJson,
    fetchedAt: fetchedAt ?? this.fetchedAt,
  );
  CachedForm copyWithCompanion(CachedFormsCompanion data) {
    return CachedForm(
      formId: data.formId.present ? data.formId.value : this.formId,
      version: data.version.present ? data.version.value : this.version,
      title: data.title.present ? data.title.value : this.title,
      schemaJson: data.schemaJson.present
          ? data.schemaJson.value
          : this.schemaJson,
      fetchedAt: data.fetchedAt.present ? data.fetchedAt.value : this.fetchedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('CachedForm(')
          ..write('formId: $formId, ')
          ..write('version: $version, ')
          ..write('title: $title, ')
          ..write('schemaJson: $schemaJson, ')
          ..write('fetchedAt: $fetchedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(formId, version, title, schemaJson, fetchedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is CachedForm &&
          other.formId == this.formId &&
          other.version == this.version &&
          other.title == this.title &&
          other.schemaJson == this.schemaJson &&
          other.fetchedAt == this.fetchedAt);
}

class CachedFormsCompanion extends UpdateCompanion<CachedForm> {
  final Value<String> formId;
  final Value<int> version;
  final Value<String> title;
  final Value<String> schemaJson;
  final Value<DateTime> fetchedAt;
  final Value<int> rowid;
  const CachedFormsCompanion({
    this.formId = const Value.absent(),
    this.version = const Value.absent(),
    this.title = const Value.absent(),
    this.schemaJson = const Value.absent(),
    this.fetchedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  CachedFormsCompanion.insert({
    required String formId,
    required int version,
    required String title,
    required String schemaJson,
    required DateTime fetchedAt,
    this.rowid = const Value.absent(),
  }) : formId = Value(formId),
       version = Value(version),
       title = Value(title),
       schemaJson = Value(schemaJson),
       fetchedAt = Value(fetchedAt);
  static Insertable<CachedForm> custom({
    Expression<String>? formId,
    Expression<int>? version,
    Expression<String>? title,
    Expression<String>? schemaJson,
    Expression<DateTime>? fetchedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (formId != null) 'form_id': formId,
      if (version != null) 'version': version,
      if (title != null) 'title': title,
      if (schemaJson != null) 'schema_json': schemaJson,
      if (fetchedAt != null) 'fetched_at': fetchedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  CachedFormsCompanion copyWith({
    Value<String>? formId,
    Value<int>? version,
    Value<String>? title,
    Value<String>? schemaJson,
    Value<DateTime>? fetchedAt,
    Value<int>? rowid,
  }) {
    return CachedFormsCompanion(
      formId: formId ?? this.formId,
      version: version ?? this.version,
      title: title ?? this.title,
      schemaJson: schemaJson ?? this.schemaJson,
      fetchedAt: fetchedAt ?? this.fetchedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (formId.present) {
      map['form_id'] = Variable<String>(formId.value);
    }
    if (version.present) {
      map['version'] = Variable<int>(version.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (schemaJson.present) {
      map['schema_json'] = Variable<String>(schemaJson.value);
    }
    if (fetchedAt.present) {
      map['fetched_at'] = Variable<DateTime>(fetchedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('CachedFormsCompanion(')
          ..write('formId: $formId, ')
          ..write('version: $version, ')
          ..write('title: $title, ')
          ..write('schemaJson: $schemaJson, ')
          ..write('fetchedAt: $fetchedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $DraftsTable extends Drafts with TableInfo<$DraftsTable, Draft> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $DraftsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _userIdMeta = const VerificationMeta('userId');
  @override
  late final GeneratedColumn<String> userId = GeneratedColumn<String>(
    'user_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _formIdMeta = const VerificationMeta('formId');
  @override
  late final GeneratedColumn<String> formId = GeneratedColumn<String>(
    'form_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _formVersionMeta = const VerificationMeta(
    'formVersion',
  );
  @override
  late final GeneratedColumn<int> formVersion = GeneratedColumn<int>(
    'form_version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _answersJsonMeta = const VerificationMeta(
    'answersJson',
  );
  @override
  late final GeneratedColumn<String> answersJson = GeneratedColumn<String>(
    'answers_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _correctsServerIdMeta = const VerificationMeta(
    'correctsServerId',
  );
  @override
  late final GeneratedColumn<String> correctsServerId = GeneratedColumn<String>(
    'corrects_server_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _baseRevisionMeta = const VerificationMeta(
    'baseRevision',
  );
  @override
  late final GeneratedColumn<int> baseRevision = GeneratedColumn<int>(
    'base_revision',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _correctsLocalIdMeta = const VerificationMeta(
    'correctsLocalId',
  );
  @override
  late final GeneratedColumn<String> correctsLocalId = GeneratedColumn<String>(
    'corrects_local_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _referenceMeta = const VerificationMeta(
    'reference',
  );
  @override
  late final GeneratedColumn<String> reference = GeneratedColumn<String>(
    'reference',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    userId,
    formId,
    formVersion,
    answersJson,
    createdAt,
    updatedAt,
    correctsServerId,
    baseRevision,
    correctsLocalId,
    reference,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'drafts';
  @override
  VerificationContext validateIntegrity(
    Insertable<Draft> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('user_id')) {
      context.handle(
        _userIdMeta,
        userId.isAcceptableOrUnknown(data['user_id']!, _userIdMeta),
      );
    } else if (isInserting) {
      context.missing(_userIdMeta);
    }
    if (data.containsKey('form_id')) {
      context.handle(
        _formIdMeta,
        formId.isAcceptableOrUnknown(data['form_id']!, _formIdMeta),
      );
    } else if (isInserting) {
      context.missing(_formIdMeta);
    }
    if (data.containsKey('form_version')) {
      context.handle(
        _formVersionMeta,
        formVersion.isAcceptableOrUnknown(
          data['form_version']!,
          _formVersionMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_formVersionMeta);
    }
    if (data.containsKey('answers_json')) {
      context.handle(
        _answersJsonMeta,
        answersJson.isAcceptableOrUnknown(
          data['answers_json']!,
          _answersJsonMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_answersJsonMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    if (data.containsKey('corrects_server_id')) {
      context.handle(
        _correctsServerIdMeta,
        correctsServerId.isAcceptableOrUnknown(
          data['corrects_server_id']!,
          _correctsServerIdMeta,
        ),
      );
    }
    if (data.containsKey('base_revision')) {
      context.handle(
        _baseRevisionMeta,
        baseRevision.isAcceptableOrUnknown(
          data['base_revision']!,
          _baseRevisionMeta,
        ),
      );
    }
    if (data.containsKey('corrects_local_id')) {
      context.handle(
        _correctsLocalIdMeta,
        correctsLocalId.isAcceptableOrUnknown(
          data['corrects_local_id']!,
          _correctsLocalIdMeta,
        ),
      );
    }
    if (data.containsKey('reference')) {
      context.handle(
        _referenceMeta,
        reference.isAcceptableOrUnknown(data['reference']!, _referenceMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Draft map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Draft(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      userId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}user_id'],
      )!,
      formId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}form_id'],
      )!,
      formVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}form_version'],
      )!,
      answersJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}answers_json'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
      correctsServerId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}corrects_server_id'],
      ),
      baseRevision: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}base_revision'],
      ),
      correctsLocalId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}corrects_local_id'],
      ),
      reference: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}reference'],
      ),
    );
  }

  @override
  $DraftsTable createAlias(String alias) {
    return $DraftsTable(attachedDatabase, alias);
  }
}

class Draft extends DataClass implements Insertable<Draft> {
  final String id;
  final String userId;
  final String formId;
  final int formVersion;
  final String answersJson;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? correctsServerId;
  final int? baseRevision;
  final String? correctsLocalId;
  final String? reference;
  const Draft({
    required this.id,
    required this.userId,
    required this.formId,
    required this.formVersion,
    required this.answersJson,
    required this.createdAt,
    required this.updatedAt,
    this.correctsServerId,
    this.baseRevision,
    this.correctsLocalId,
    this.reference,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    map['user_id'] = Variable<String>(userId);
    map['form_id'] = Variable<String>(formId);
    map['form_version'] = Variable<int>(formVersion);
    map['answers_json'] = Variable<String>(answersJson);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    if (!nullToAbsent || correctsServerId != null) {
      map['corrects_server_id'] = Variable<String>(correctsServerId);
    }
    if (!nullToAbsent || baseRevision != null) {
      map['base_revision'] = Variable<int>(baseRevision);
    }
    if (!nullToAbsent || correctsLocalId != null) {
      map['corrects_local_id'] = Variable<String>(correctsLocalId);
    }
    if (!nullToAbsent || reference != null) {
      map['reference'] = Variable<String>(reference);
    }
    return map;
  }

  DraftsCompanion toCompanion(bool nullToAbsent) {
    return DraftsCompanion(
      id: Value(id),
      userId: Value(userId),
      formId: Value(formId),
      formVersion: Value(formVersion),
      answersJson: Value(answersJson),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
      correctsServerId: correctsServerId == null && nullToAbsent
          ? const Value.absent()
          : Value(correctsServerId),
      baseRevision: baseRevision == null && nullToAbsent
          ? const Value.absent()
          : Value(baseRevision),
      correctsLocalId: correctsLocalId == null && nullToAbsent
          ? const Value.absent()
          : Value(correctsLocalId),
      reference: reference == null && nullToAbsent
          ? const Value.absent()
          : Value(reference),
    );
  }

  factory Draft.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Draft(
      id: serializer.fromJson<String>(json['id']),
      userId: serializer.fromJson<String>(json['userId']),
      formId: serializer.fromJson<String>(json['formId']),
      formVersion: serializer.fromJson<int>(json['formVersion']),
      answersJson: serializer.fromJson<String>(json['answersJson']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
      correctsServerId: serializer.fromJson<String?>(json['correctsServerId']),
      baseRevision: serializer.fromJson<int?>(json['baseRevision']),
      correctsLocalId: serializer.fromJson<String?>(json['correctsLocalId']),
      reference: serializer.fromJson<String?>(json['reference']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'userId': serializer.toJson<String>(userId),
      'formId': serializer.toJson<String>(formId),
      'formVersion': serializer.toJson<int>(formVersion),
      'answersJson': serializer.toJson<String>(answersJson),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
      'correctsServerId': serializer.toJson<String?>(correctsServerId),
      'baseRevision': serializer.toJson<int?>(baseRevision),
      'correctsLocalId': serializer.toJson<String?>(correctsLocalId),
      'reference': serializer.toJson<String?>(reference),
    };
  }

  Draft copyWith({
    String? id,
    String? userId,
    String? formId,
    int? formVersion,
    String? answersJson,
    DateTime? createdAt,
    DateTime? updatedAt,
    Value<String?> correctsServerId = const Value.absent(),
    Value<int?> baseRevision = const Value.absent(),
    Value<String?> correctsLocalId = const Value.absent(),
    Value<String?> reference = const Value.absent(),
  }) => Draft(
    id: id ?? this.id,
    userId: userId ?? this.userId,
    formId: formId ?? this.formId,
    formVersion: formVersion ?? this.formVersion,
    answersJson: answersJson ?? this.answersJson,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
    correctsServerId: correctsServerId.present
        ? correctsServerId.value
        : this.correctsServerId,
    baseRevision: baseRevision.present ? baseRevision.value : this.baseRevision,
    correctsLocalId: correctsLocalId.present
        ? correctsLocalId.value
        : this.correctsLocalId,
    reference: reference.present ? reference.value : this.reference,
  );
  Draft copyWithCompanion(DraftsCompanion data) {
    return Draft(
      id: data.id.present ? data.id.value : this.id,
      userId: data.userId.present ? data.userId.value : this.userId,
      formId: data.formId.present ? data.formId.value : this.formId,
      formVersion: data.formVersion.present
          ? data.formVersion.value
          : this.formVersion,
      answersJson: data.answersJson.present
          ? data.answersJson.value
          : this.answersJson,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
      correctsServerId: data.correctsServerId.present
          ? data.correctsServerId.value
          : this.correctsServerId,
      baseRevision: data.baseRevision.present
          ? data.baseRevision.value
          : this.baseRevision,
      correctsLocalId: data.correctsLocalId.present
          ? data.correctsLocalId.value
          : this.correctsLocalId,
      reference: data.reference.present ? data.reference.value : this.reference,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Draft(')
          ..write('id: $id, ')
          ..write('userId: $userId, ')
          ..write('formId: $formId, ')
          ..write('formVersion: $formVersion, ')
          ..write('answersJson: $answersJson, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('correctsServerId: $correctsServerId, ')
          ..write('baseRevision: $baseRevision, ')
          ..write('correctsLocalId: $correctsLocalId, ')
          ..write('reference: $reference')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    userId,
    formId,
    formVersion,
    answersJson,
    createdAt,
    updatedAt,
    correctsServerId,
    baseRevision,
    correctsLocalId,
    reference,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Draft &&
          other.id == this.id &&
          other.userId == this.userId &&
          other.formId == this.formId &&
          other.formVersion == this.formVersion &&
          other.answersJson == this.answersJson &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt &&
          other.correctsServerId == this.correctsServerId &&
          other.baseRevision == this.baseRevision &&
          other.correctsLocalId == this.correctsLocalId &&
          other.reference == this.reference);
}

class DraftsCompanion extends UpdateCompanion<Draft> {
  final Value<String> id;
  final Value<String> userId;
  final Value<String> formId;
  final Value<int> formVersion;
  final Value<String> answersJson;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  final Value<String?> correctsServerId;
  final Value<int?> baseRevision;
  final Value<String?> correctsLocalId;
  final Value<String?> reference;
  final Value<int> rowid;
  const DraftsCompanion({
    this.id = const Value.absent(),
    this.userId = const Value.absent(),
    this.formId = const Value.absent(),
    this.formVersion = const Value.absent(),
    this.answersJson = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
    this.correctsServerId = const Value.absent(),
    this.baseRevision = const Value.absent(),
    this.correctsLocalId = const Value.absent(),
    this.reference = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  DraftsCompanion.insert({
    required String id,
    required String userId,
    required String formId,
    required int formVersion,
    required String answersJson,
    required DateTime createdAt,
    required DateTime updatedAt,
    this.correctsServerId = const Value.absent(),
    this.baseRevision = const Value.absent(),
    this.correctsLocalId = const Value.absent(),
    this.reference = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       userId = Value(userId),
       formId = Value(formId),
       formVersion = Value(formVersion),
       answersJson = Value(answersJson),
       createdAt = Value(createdAt),
       updatedAt = Value(updatedAt);
  static Insertable<Draft> custom({
    Expression<String>? id,
    Expression<String>? userId,
    Expression<String>? formId,
    Expression<int>? formVersion,
    Expression<String>? answersJson,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
    Expression<String>? correctsServerId,
    Expression<int>? baseRevision,
    Expression<String>? correctsLocalId,
    Expression<String>? reference,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (userId != null) 'user_id': userId,
      if (formId != null) 'form_id': formId,
      if (formVersion != null) 'form_version': formVersion,
      if (answersJson != null) 'answers_json': answersJson,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
      if (correctsServerId != null) 'corrects_server_id': correctsServerId,
      if (baseRevision != null) 'base_revision': baseRevision,
      if (correctsLocalId != null) 'corrects_local_id': correctsLocalId,
      if (reference != null) 'reference': reference,
      if (rowid != null) 'rowid': rowid,
    });
  }

  DraftsCompanion copyWith({
    Value<String>? id,
    Value<String>? userId,
    Value<String>? formId,
    Value<int>? formVersion,
    Value<String>? answersJson,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
    Value<String?>? correctsServerId,
    Value<int?>? baseRevision,
    Value<String?>? correctsLocalId,
    Value<String?>? reference,
    Value<int>? rowid,
  }) {
    return DraftsCompanion(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      formId: formId ?? this.formId,
      formVersion: formVersion ?? this.formVersion,
      answersJson: answersJson ?? this.answersJson,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      correctsServerId: correctsServerId ?? this.correctsServerId,
      baseRevision: baseRevision ?? this.baseRevision,
      correctsLocalId: correctsLocalId ?? this.correctsLocalId,
      reference: reference ?? this.reference,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (userId.present) {
      map['user_id'] = Variable<String>(userId.value);
    }
    if (formId.present) {
      map['form_id'] = Variable<String>(formId.value);
    }
    if (formVersion.present) {
      map['form_version'] = Variable<int>(formVersion.value);
    }
    if (answersJson.present) {
      map['answers_json'] = Variable<String>(answersJson.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    if (correctsServerId.present) {
      map['corrects_server_id'] = Variable<String>(correctsServerId.value);
    }
    if (baseRevision.present) {
      map['base_revision'] = Variable<int>(baseRevision.value);
    }
    if (correctsLocalId.present) {
      map['corrects_local_id'] = Variable<String>(correctsLocalId.value);
    }
    if (reference.present) {
      map['reference'] = Variable<String>(reference.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('DraftsCompanion(')
          ..write('id: $id, ')
          ..write('userId: $userId, ')
          ..write('formId: $formId, ')
          ..write('formVersion: $formVersion, ')
          ..write('answersJson: $answersJson, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt, ')
          ..write('correctsServerId: $correctsServerId, ')
          ..write('baseRevision: $baseRevision, ')
          ..write('correctsLocalId: $correctsLocalId, ')
          ..write('reference: $reference, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $LocalSubmissionsTable extends LocalSubmissions
    with TableInfo<$LocalSubmissionsTable, LocalSubmission> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalSubmissionsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _localIdMeta = const VerificationMeta(
    'localId',
  );
  @override
  late final GeneratedColumn<String> localId = GeneratedColumn<String>(
    'local_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _userIdMeta = const VerificationMeta('userId');
  @override
  late final GeneratedColumn<String> userId = GeneratedColumn<String>(
    'user_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _idempotencyKeyMeta = const VerificationMeta(
    'idempotencyKey',
  );
  @override
  late final GeneratedColumn<String> idempotencyKey = GeneratedColumn<String>(
    'idempotency_key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _formIdMeta = const VerificationMeta('formId');
  @override
  late final GeneratedColumn<String> formId = GeneratedColumn<String>(
    'form_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _formVersionMeta = const VerificationMeta(
    'formVersion',
  );
  @override
  late final GeneratedColumn<int> formVersion = GeneratedColumn<int>(
    'form_version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _formTitleMeta = const VerificationMeta(
    'formTitle',
  );
  @override
  late final GeneratedColumn<String> formTitle = GeneratedColumn<String>(
    'form_title',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _answersJsonMeta = const VerificationMeta(
    'answersJson',
  );
  @override
  late final GeneratedColumn<String> answersJson = GeneratedColumn<String>(
    'answers_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _submittedAtDeviceMeta = const VerificationMeta(
    'submittedAtDevice',
  );
  @override
  late final GeneratedColumn<DateTime> submittedAtDevice =
      GeneratedColumn<DateTime>(
        'submitted_at_device',
        aliasedName,
        false,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _tzOffsetMinMeta = const VerificationMeta(
    'tzOffsetMin',
  );
  @override
  late final GeneratedColumn<int> tzOffsetMin = GeneratedColumn<int>(
    'tz_offset_min',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _subLatitudeMeta = const VerificationMeta(
    'subLatitude',
  );
  @override
  late final GeneratedColumn<double> subLatitude = GeneratedColumn<double>(
    'sub_latitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _subLongitudeMeta = const VerificationMeta(
    'subLongitude',
  );
  @override
  late final GeneratedColumn<double> subLongitude = GeneratedColumn<double>(
    'sub_longitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _subAccuracyMMeta = const VerificationMeta(
    'subAccuracyM',
  );
  @override
  late final GeneratedColumn<double> subAccuracyM = GeneratedColumn<double>(
    'sub_accuracy_m',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _subFixAtDeviceMeta = const VerificationMeta(
    'subFixAtDevice',
  );
  @override
  late final GeneratedColumn<DateTime> subFixAtDevice =
      GeneratedColumn<DateTime>(
        'sub_fix_at_device',
        aliasedName,
        true,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _subLocationStatusMeta = const VerificationMeta(
    'subLocationStatus',
  );
  @override
  late final GeneratedColumn<String> subLocationStatus =
      GeneratedColumn<String>(
        'sub_location_status',
        aliasedName,
        false,
        type: DriftSqlType.string,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _stateMeta = const VerificationMeta('state');
  @override
  late final GeneratedColumn<String> state = GeneratedColumn<String>(
    'state',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _attemptsMeta = const VerificationMeta(
    'attempts',
  );
  @override
  late final GeneratedColumn<int> attempts = GeneratedColumn<int>(
    'attempts',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _nextAttemptAtMeta = const VerificationMeta(
    'nextAttemptAt',
  );
  @override
  late final GeneratedColumn<DateTime> nextAttemptAt =
      GeneratedColumn<DateTime>(
        'next_attempt_at',
        aliasedName,
        false,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _lastErrorMeta = const VerificationMeta(
    'lastError',
  );
  @override
  late final GeneratedColumn<String> lastError = GeneratedColumn<String>(
    'last_error',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _serverIdMeta = const VerificationMeta(
    'serverId',
  );
  @override
  late final GeneratedColumn<String> serverId = GeneratedColumn<String>(
    'server_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _receivedAtServerMeta = const VerificationMeta(
    'receivedAtServer',
  );
  @override
  late final GeneratedColumn<DateTime> receivedAtServer =
      GeneratedColumn<DateTime>(
        'received_at_server',
        aliasedName,
        true,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _acceptedAtServerMeta = const VerificationMeta(
    'acceptedAtServer',
  );
  @override
  late final GeneratedColumn<DateTime> acceptedAtServer =
      GeneratedColumn<DateTime>(
        'accepted_at_server',
        aliasedName,
        true,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _referenceMeta = const VerificationMeta(
    'reference',
  );
  @override
  late final GeneratedColumn<String> reference = GeneratedColumn<String>(
    'reference',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _revisionMeta = const VerificationMeta(
    'revision',
  );
  @override
  late final GeneratedColumn<int> revision = GeneratedColumn<int>(
    'revision',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _isLatestMeta = const VerificationMeta(
    'isLatest',
  );
  @override
  late final GeneratedColumn<bool> isLatest = GeneratedColumn<bool>(
    'is_latest',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("is_latest" IN (0, 1))',
    ),
    defaultValue: const Constant(true),
  );
  static const VerificationMeta _correctsServerIdMeta = const VerificationMeta(
    'correctsServerId',
  );
  @override
  late final GeneratedColumn<String> correctsServerId = GeneratedColumn<String>(
    'corrects_server_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _baseRevisionMeta = const VerificationMeta(
    'baseRevision',
  );
  @override
  late final GeneratedColumn<int> baseRevision = GeneratedColumn<int>(
    'base_revision',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _reviewStatusMeta = const VerificationMeta(
    'reviewStatus',
  );
  @override
  late final GeneratedColumn<String> reviewStatus = GeneratedColumn<String>(
    'review_status',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _reviewReasonMeta = const VerificationMeta(
    'reviewReason',
  );
  @override
  late final GeneratedColumn<String> reviewReason = GeneratedColumn<String>(
    'review_reason',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _reviewCommentMeta = const VerificationMeta(
    'reviewComment',
  );
  @override
  late final GeneratedColumn<String> reviewComment = GeneratedColumn<String>(
    'review_comment',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _reviewFlagsJsonMeta = const VerificationMeta(
    'reviewFlagsJson',
  );
  @override
  late final GeneratedColumn<String> reviewFlagsJson = GeneratedColumn<String>(
    'review_flags_json',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _reviewedAtMeta = const VerificationMeta(
    'reviewedAt',
  );
  @override
  late final GeneratedColumn<DateTime> reviewedAt = GeneratedColumn<DateTime>(
    'reviewed_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  @override
  List<GeneratedColumn> get $columns => [
    localId,
    userId,
    idempotencyKey,
    formId,
    formVersion,
    formTitle,
    answersJson,
    submittedAtDevice,
    tzOffsetMin,
    subLatitude,
    subLongitude,
    subAccuracyM,
    subFixAtDevice,
    subLocationStatus,
    state,
    attempts,
    nextAttemptAt,
    lastError,
    serverId,
    receivedAtServer,
    acceptedAtServer,
    createdAt,
    reference,
    revision,
    isLatest,
    correctsServerId,
    baseRevision,
    reviewStatus,
    reviewReason,
    reviewComment,
    reviewFlagsJson,
    reviewedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_submissions';
  @override
  VerificationContext validateIntegrity(
    Insertable<LocalSubmission> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('local_id')) {
      context.handle(
        _localIdMeta,
        localId.isAcceptableOrUnknown(data['local_id']!, _localIdMeta),
      );
    } else if (isInserting) {
      context.missing(_localIdMeta);
    }
    if (data.containsKey('user_id')) {
      context.handle(
        _userIdMeta,
        userId.isAcceptableOrUnknown(data['user_id']!, _userIdMeta),
      );
    } else if (isInserting) {
      context.missing(_userIdMeta);
    }
    if (data.containsKey('idempotency_key')) {
      context.handle(
        _idempotencyKeyMeta,
        idempotencyKey.isAcceptableOrUnknown(
          data['idempotency_key']!,
          _idempotencyKeyMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_idempotencyKeyMeta);
    }
    if (data.containsKey('form_id')) {
      context.handle(
        _formIdMeta,
        formId.isAcceptableOrUnknown(data['form_id']!, _formIdMeta),
      );
    } else if (isInserting) {
      context.missing(_formIdMeta);
    }
    if (data.containsKey('form_version')) {
      context.handle(
        _formVersionMeta,
        formVersion.isAcceptableOrUnknown(
          data['form_version']!,
          _formVersionMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_formVersionMeta);
    }
    if (data.containsKey('form_title')) {
      context.handle(
        _formTitleMeta,
        formTitle.isAcceptableOrUnknown(data['form_title']!, _formTitleMeta),
      );
    } else if (isInserting) {
      context.missing(_formTitleMeta);
    }
    if (data.containsKey('answers_json')) {
      context.handle(
        _answersJsonMeta,
        answersJson.isAcceptableOrUnknown(
          data['answers_json']!,
          _answersJsonMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_answersJsonMeta);
    }
    if (data.containsKey('submitted_at_device')) {
      context.handle(
        _submittedAtDeviceMeta,
        submittedAtDevice.isAcceptableOrUnknown(
          data['submitted_at_device']!,
          _submittedAtDeviceMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_submittedAtDeviceMeta);
    }
    if (data.containsKey('tz_offset_min')) {
      context.handle(
        _tzOffsetMinMeta,
        tzOffsetMin.isAcceptableOrUnknown(
          data['tz_offset_min']!,
          _tzOffsetMinMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_tzOffsetMinMeta);
    }
    if (data.containsKey('sub_latitude')) {
      context.handle(
        _subLatitudeMeta,
        subLatitude.isAcceptableOrUnknown(
          data['sub_latitude']!,
          _subLatitudeMeta,
        ),
      );
    }
    if (data.containsKey('sub_longitude')) {
      context.handle(
        _subLongitudeMeta,
        subLongitude.isAcceptableOrUnknown(
          data['sub_longitude']!,
          _subLongitudeMeta,
        ),
      );
    }
    if (data.containsKey('sub_accuracy_m')) {
      context.handle(
        _subAccuracyMMeta,
        subAccuracyM.isAcceptableOrUnknown(
          data['sub_accuracy_m']!,
          _subAccuracyMMeta,
        ),
      );
    }
    if (data.containsKey('sub_fix_at_device')) {
      context.handle(
        _subFixAtDeviceMeta,
        subFixAtDevice.isAcceptableOrUnknown(
          data['sub_fix_at_device']!,
          _subFixAtDeviceMeta,
        ),
      );
    }
    if (data.containsKey('sub_location_status')) {
      context.handle(
        _subLocationStatusMeta,
        subLocationStatus.isAcceptableOrUnknown(
          data['sub_location_status']!,
          _subLocationStatusMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_subLocationStatusMeta);
    }
    if (data.containsKey('state')) {
      context.handle(
        _stateMeta,
        state.isAcceptableOrUnknown(data['state']!, _stateMeta),
      );
    } else if (isInserting) {
      context.missing(_stateMeta);
    }
    if (data.containsKey('attempts')) {
      context.handle(
        _attemptsMeta,
        attempts.isAcceptableOrUnknown(data['attempts']!, _attemptsMeta),
      );
    }
    if (data.containsKey('next_attempt_at')) {
      context.handle(
        _nextAttemptAtMeta,
        nextAttemptAt.isAcceptableOrUnknown(
          data['next_attempt_at']!,
          _nextAttemptAtMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_nextAttemptAtMeta);
    }
    if (data.containsKey('last_error')) {
      context.handle(
        _lastErrorMeta,
        lastError.isAcceptableOrUnknown(data['last_error']!, _lastErrorMeta),
      );
    }
    if (data.containsKey('server_id')) {
      context.handle(
        _serverIdMeta,
        serverId.isAcceptableOrUnknown(data['server_id']!, _serverIdMeta),
      );
    }
    if (data.containsKey('received_at_server')) {
      context.handle(
        _receivedAtServerMeta,
        receivedAtServer.isAcceptableOrUnknown(
          data['received_at_server']!,
          _receivedAtServerMeta,
        ),
      );
    }
    if (data.containsKey('accepted_at_server')) {
      context.handle(
        _acceptedAtServerMeta,
        acceptedAtServer.isAcceptableOrUnknown(
          data['accepted_at_server']!,
          _acceptedAtServerMeta,
        ),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('reference')) {
      context.handle(
        _referenceMeta,
        reference.isAcceptableOrUnknown(data['reference']!, _referenceMeta),
      );
    }
    if (data.containsKey('revision')) {
      context.handle(
        _revisionMeta,
        revision.isAcceptableOrUnknown(data['revision']!, _revisionMeta),
      );
    }
    if (data.containsKey('is_latest')) {
      context.handle(
        _isLatestMeta,
        isLatest.isAcceptableOrUnknown(data['is_latest']!, _isLatestMeta),
      );
    }
    if (data.containsKey('corrects_server_id')) {
      context.handle(
        _correctsServerIdMeta,
        correctsServerId.isAcceptableOrUnknown(
          data['corrects_server_id']!,
          _correctsServerIdMeta,
        ),
      );
    }
    if (data.containsKey('base_revision')) {
      context.handle(
        _baseRevisionMeta,
        baseRevision.isAcceptableOrUnknown(
          data['base_revision']!,
          _baseRevisionMeta,
        ),
      );
    }
    if (data.containsKey('review_status')) {
      context.handle(
        _reviewStatusMeta,
        reviewStatus.isAcceptableOrUnknown(
          data['review_status']!,
          _reviewStatusMeta,
        ),
      );
    }
    if (data.containsKey('review_reason')) {
      context.handle(
        _reviewReasonMeta,
        reviewReason.isAcceptableOrUnknown(
          data['review_reason']!,
          _reviewReasonMeta,
        ),
      );
    }
    if (data.containsKey('review_comment')) {
      context.handle(
        _reviewCommentMeta,
        reviewComment.isAcceptableOrUnknown(
          data['review_comment']!,
          _reviewCommentMeta,
        ),
      );
    }
    if (data.containsKey('review_flags_json')) {
      context.handle(
        _reviewFlagsJsonMeta,
        reviewFlagsJson.isAcceptableOrUnknown(
          data['review_flags_json']!,
          _reviewFlagsJsonMeta,
        ),
      );
    }
    if (data.containsKey('reviewed_at')) {
      context.handle(
        _reviewedAtMeta,
        reviewedAt.isAcceptableOrUnknown(data['reviewed_at']!, _reviewedAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {localId};
  @override
  LocalSubmission map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalSubmission(
      localId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}local_id'],
      )!,
      userId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}user_id'],
      )!,
      idempotencyKey: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}idempotency_key'],
      )!,
      formId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}form_id'],
      )!,
      formVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}form_version'],
      )!,
      formTitle: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}form_title'],
      )!,
      answersJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}answers_json'],
      )!,
      submittedAtDevice: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}submitted_at_device'],
      )!,
      tzOffsetMin: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}tz_offset_min'],
      )!,
      subLatitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}sub_latitude'],
      ),
      subLongitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}sub_longitude'],
      ),
      subAccuracyM: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}sub_accuracy_m'],
      ),
      subFixAtDevice: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}sub_fix_at_device'],
      ),
      subLocationStatus: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sub_location_status'],
      )!,
      state: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}state'],
      )!,
      attempts: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}attempts'],
      )!,
      nextAttemptAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}next_attempt_at'],
      )!,
      lastError: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}last_error'],
      ),
      serverId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}server_id'],
      ),
      receivedAtServer: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}received_at_server'],
      ),
      acceptedAtServer: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}accepted_at_server'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      reference: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}reference'],
      ),
      revision: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}revision'],
      )!,
      isLatest: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}is_latest'],
      )!,
      correctsServerId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}corrects_server_id'],
      ),
      baseRevision: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}base_revision'],
      ),
      reviewStatus: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}review_status'],
      ),
      reviewReason: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}review_reason'],
      ),
      reviewComment: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}review_comment'],
      ),
      reviewFlagsJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}review_flags_json'],
      ),
      reviewedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}reviewed_at'],
      ),
    );
  }

  @override
  $LocalSubmissionsTable createAlias(String alias) {
    return $LocalSubmissionsTable(attachedDatabase, alias);
  }
}

class LocalSubmission extends DataClass implements Insertable<LocalSubmission> {
  final String localId;
  final String userId;
  final String idempotencyKey;
  final String formId;
  final int formVersion;
  final String formTitle;
  final String answersJson;
  final DateTime submittedAtDevice;
  final int tzOffsetMin;
  final double? subLatitude;
  final double? subLongitude;
  final double? subAccuracyM;
  final DateTime? subFixAtDevice;
  final String subLocationStatus;
  final String state;
  final int attempts;
  final DateTime nextAttemptAt;
  final String? lastError;
  final String? serverId;
  final DateTime? receivedAtServer;
  final DateTime? acceptedAtServer;
  final DateTime createdAt;
  final String? reference;
  final int revision;
  final bool isLatest;
  final String? correctsServerId;
  final int? baseRevision;
  final String? reviewStatus;
  final String? reviewReason;
  final String? reviewComment;
  final String? reviewFlagsJson;
  final DateTime? reviewedAt;
  const LocalSubmission({
    required this.localId,
    required this.userId,
    required this.idempotencyKey,
    required this.formId,
    required this.formVersion,
    required this.formTitle,
    required this.answersJson,
    required this.submittedAtDevice,
    required this.tzOffsetMin,
    this.subLatitude,
    this.subLongitude,
    this.subAccuracyM,
    this.subFixAtDevice,
    required this.subLocationStatus,
    required this.state,
    required this.attempts,
    required this.nextAttemptAt,
    this.lastError,
    this.serverId,
    this.receivedAtServer,
    this.acceptedAtServer,
    required this.createdAt,
    this.reference,
    required this.revision,
    required this.isLatest,
    this.correctsServerId,
    this.baseRevision,
    this.reviewStatus,
    this.reviewReason,
    this.reviewComment,
    this.reviewFlagsJson,
    this.reviewedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['local_id'] = Variable<String>(localId);
    map['user_id'] = Variable<String>(userId);
    map['idempotency_key'] = Variable<String>(idempotencyKey);
    map['form_id'] = Variable<String>(formId);
    map['form_version'] = Variable<int>(formVersion);
    map['form_title'] = Variable<String>(formTitle);
    map['answers_json'] = Variable<String>(answersJson);
    map['submitted_at_device'] = Variable<DateTime>(submittedAtDevice);
    map['tz_offset_min'] = Variable<int>(tzOffsetMin);
    if (!nullToAbsent || subLatitude != null) {
      map['sub_latitude'] = Variable<double>(subLatitude);
    }
    if (!nullToAbsent || subLongitude != null) {
      map['sub_longitude'] = Variable<double>(subLongitude);
    }
    if (!nullToAbsent || subAccuracyM != null) {
      map['sub_accuracy_m'] = Variable<double>(subAccuracyM);
    }
    if (!nullToAbsent || subFixAtDevice != null) {
      map['sub_fix_at_device'] = Variable<DateTime>(subFixAtDevice);
    }
    map['sub_location_status'] = Variable<String>(subLocationStatus);
    map['state'] = Variable<String>(state);
    map['attempts'] = Variable<int>(attempts);
    map['next_attempt_at'] = Variable<DateTime>(nextAttemptAt);
    if (!nullToAbsent || lastError != null) {
      map['last_error'] = Variable<String>(lastError);
    }
    if (!nullToAbsent || serverId != null) {
      map['server_id'] = Variable<String>(serverId);
    }
    if (!nullToAbsent || receivedAtServer != null) {
      map['received_at_server'] = Variable<DateTime>(receivedAtServer);
    }
    if (!nullToAbsent || acceptedAtServer != null) {
      map['accepted_at_server'] = Variable<DateTime>(acceptedAtServer);
    }
    map['created_at'] = Variable<DateTime>(createdAt);
    if (!nullToAbsent || reference != null) {
      map['reference'] = Variable<String>(reference);
    }
    map['revision'] = Variable<int>(revision);
    map['is_latest'] = Variable<bool>(isLatest);
    if (!nullToAbsent || correctsServerId != null) {
      map['corrects_server_id'] = Variable<String>(correctsServerId);
    }
    if (!nullToAbsent || baseRevision != null) {
      map['base_revision'] = Variable<int>(baseRevision);
    }
    if (!nullToAbsent || reviewStatus != null) {
      map['review_status'] = Variable<String>(reviewStatus);
    }
    if (!nullToAbsent || reviewReason != null) {
      map['review_reason'] = Variable<String>(reviewReason);
    }
    if (!nullToAbsent || reviewComment != null) {
      map['review_comment'] = Variable<String>(reviewComment);
    }
    if (!nullToAbsent || reviewFlagsJson != null) {
      map['review_flags_json'] = Variable<String>(reviewFlagsJson);
    }
    if (!nullToAbsent || reviewedAt != null) {
      map['reviewed_at'] = Variable<DateTime>(reviewedAt);
    }
    return map;
  }

  LocalSubmissionsCompanion toCompanion(bool nullToAbsent) {
    return LocalSubmissionsCompanion(
      localId: Value(localId),
      userId: Value(userId),
      idempotencyKey: Value(idempotencyKey),
      formId: Value(formId),
      formVersion: Value(formVersion),
      formTitle: Value(formTitle),
      answersJson: Value(answersJson),
      submittedAtDevice: Value(submittedAtDevice),
      tzOffsetMin: Value(tzOffsetMin),
      subLatitude: subLatitude == null && nullToAbsent
          ? const Value.absent()
          : Value(subLatitude),
      subLongitude: subLongitude == null && nullToAbsent
          ? const Value.absent()
          : Value(subLongitude),
      subAccuracyM: subAccuracyM == null && nullToAbsent
          ? const Value.absent()
          : Value(subAccuracyM),
      subFixAtDevice: subFixAtDevice == null && nullToAbsent
          ? const Value.absent()
          : Value(subFixAtDevice),
      subLocationStatus: Value(subLocationStatus),
      state: Value(state),
      attempts: Value(attempts),
      nextAttemptAt: Value(nextAttemptAt),
      lastError: lastError == null && nullToAbsent
          ? const Value.absent()
          : Value(lastError),
      serverId: serverId == null && nullToAbsent
          ? const Value.absent()
          : Value(serverId),
      receivedAtServer: receivedAtServer == null && nullToAbsent
          ? const Value.absent()
          : Value(receivedAtServer),
      acceptedAtServer: acceptedAtServer == null && nullToAbsent
          ? const Value.absent()
          : Value(acceptedAtServer),
      createdAt: Value(createdAt),
      reference: reference == null && nullToAbsent
          ? const Value.absent()
          : Value(reference),
      revision: Value(revision),
      isLatest: Value(isLatest),
      correctsServerId: correctsServerId == null && nullToAbsent
          ? const Value.absent()
          : Value(correctsServerId),
      baseRevision: baseRevision == null && nullToAbsent
          ? const Value.absent()
          : Value(baseRevision),
      reviewStatus: reviewStatus == null && nullToAbsent
          ? const Value.absent()
          : Value(reviewStatus),
      reviewReason: reviewReason == null && nullToAbsent
          ? const Value.absent()
          : Value(reviewReason),
      reviewComment: reviewComment == null && nullToAbsent
          ? const Value.absent()
          : Value(reviewComment),
      reviewFlagsJson: reviewFlagsJson == null && nullToAbsent
          ? const Value.absent()
          : Value(reviewFlagsJson),
      reviewedAt: reviewedAt == null && nullToAbsent
          ? const Value.absent()
          : Value(reviewedAt),
    );
  }

  factory LocalSubmission.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalSubmission(
      localId: serializer.fromJson<String>(json['localId']),
      userId: serializer.fromJson<String>(json['userId']),
      idempotencyKey: serializer.fromJson<String>(json['idempotencyKey']),
      formId: serializer.fromJson<String>(json['formId']),
      formVersion: serializer.fromJson<int>(json['formVersion']),
      formTitle: serializer.fromJson<String>(json['formTitle']),
      answersJson: serializer.fromJson<String>(json['answersJson']),
      submittedAtDevice: serializer.fromJson<DateTime>(
        json['submittedAtDevice'],
      ),
      tzOffsetMin: serializer.fromJson<int>(json['tzOffsetMin']),
      subLatitude: serializer.fromJson<double?>(json['subLatitude']),
      subLongitude: serializer.fromJson<double?>(json['subLongitude']),
      subAccuracyM: serializer.fromJson<double?>(json['subAccuracyM']),
      subFixAtDevice: serializer.fromJson<DateTime?>(json['subFixAtDevice']),
      subLocationStatus: serializer.fromJson<String>(json['subLocationStatus']),
      state: serializer.fromJson<String>(json['state']),
      attempts: serializer.fromJson<int>(json['attempts']),
      nextAttemptAt: serializer.fromJson<DateTime>(json['nextAttemptAt']),
      lastError: serializer.fromJson<String?>(json['lastError']),
      serverId: serializer.fromJson<String?>(json['serverId']),
      receivedAtServer: serializer.fromJson<DateTime?>(
        json['receivedAtServer'],
      ),
      acceptedAtServer: serializer.fromJson<DateTime?>(
        json['acceptedAtServer'],
      ),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      reference: serializer.fromJson<String?>(json['reference']),
      revision: serializer.fromJson<int>(json['revision']),
      isLatest: serializer.fromJson<bool>(json['isLatest']),
      correctsServerId: serializer.fromJson<String?>(json['correctsServerId']),
      baseRevision: serializer.fromJson<int?>(json['baseRevision']),
      reviewStatus: serializer.fromJson<String?>(json['reviewStatus']),
      reviewReason: serializer.fromJson<String?>(json['reviewReason']),
      reviewComment: serializer.fromJson<String?>(json['reviewComment']),
      reviewFlagsJson: serializer.fromJson<String?>(json['reviewFlagsJson']),
      reviewedAt: serializer.fromJson<DateTime?>(json['reviewedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'localId': serializer.toJson<String>(localId),
      'userId': serializer.toJson<String>(userId),
      'idempotencyKey': serializer.toJson<String>(idempotencyKey),
      'formId': serializer.toJson<String>(formId),
      'formVersion': serializer.toJson<int>(formVersion),
      'formTitle': serializer.toJson<String>(formTitle),
      'answersJson': serializer.toJson<String>(answersJson),
      'submittedAtDevice': serializer.toJson<DateTime>(submittedAtDevice),
      'tzOffsetMin': serializer.toJson<int>(tzOffsetMin),
      'subLatitude': serializer.toJson<double?>(subLatitude),
      'subLongitude': serializer.toJson<double?>(subLongitude),
      'subAccuracyM': serializer.toJson<double?>(subAccuracyM),
      'subFixAtDevice': serializer.toJson<DateTime?>(subFixAtDevice),
      'subLocationStatus': serializer.toJson<String>(subLocationStatus),
      'state': serializer.toJson<String>(state),
      'attempts': serializer.toJson<int>(attempts),
      'nextAttemptAt': serializer.toJson<DateTime>(nextAttemptAt),
      'lastError': serializer.toJson<String?>(lastError),
      'serverId': serializer.toJson<String?>(serverId),
      'receivedAtServer': serializer.toJson<DateTime?>(receivedAtServer),
      'acceptedAtServer': serializer.toJson<DateTime?>(acceptedAtServer),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'reference': serializer.toJson<String?>(reference),
      'revision': serializer.toJson<int>(revision),
      'isLatest': serializer.toJson<bool>(isLatest),
      'correctsServerId': serializer.toJson<String?>(correctsServerId),
      'baseRevision': serializer.toJson<int?>(baseRevision),
      'reviewStatus': serializer.toJson<String?>(reviewStatus),
      'reviewReason': serializer.toJson<String?>(reviewReason),
      'reviewComment': serializer.toJson<String?>(reviewComment),
      'reviewFlagsJson': serializer.toJson<String?>(reviewFlagsJson),
      'reviewedAt': serializer.toJson<DateTime?>(reviewedAt),
    };
  }

  LocalSubmission copyWith({
    String? localId,
    String? userId,
    String? idempotencyKey,
    String? formId,
    int? formVersion,
    String? formTitle,
    String? answersJson,
    DateTime? submittedAtDevice,
    int? tzOffsetMin,
    Value<double?> subLatitude = const Value.absent(),
    Value<double?> subLongitude = const Value.absent(),
    Value<double?> subAccuracyM = const Value.absent(),
    Value<DateTime?> subFixAtDevice = const Value.absent(),
    String? subLocationStatus,
    String? state,
    int? attempts,
    DateTime? nextAttemptAt,
    Value<String?> lastError = const Value.absent(),
    Value<String?> serverId = const Value.absent(),
    Value<DateTime?> receivedAtServer = const Value.absent(),
    Value<DateTime?> acceptedAtServer = const Value.absent(),
    DateTime? createdAt,
    Value<String?> reference = const Value.absent(),
    int? revision,
    bool? isLatest,
    Value<String?> correctsServerId = const Value.absent(),
    Value<int?> baseRevision = const Value.absent(),
    Value<String?> reviewStatus = const Value.absent(),
    Value<String?> reviewReason = const Value.absent(),
    Value<String?> reviewComment = const Value.absent(),
    Value<String?> reviewFlagsJson = const Value.absent(),
    Value<DateTime?> reviewedAt = const Value.absent(),
  }) => LocalSubmission(
    localId: localId ?? this.localId,
    userId: userId ?? this.userId,
    idempotencyKey: idempotencyKey ?? this.idempotencyKey,
    formId: formId ?? this.formId,
    formVersion: formVersion ?? this.formVersion,
    formTitle: formTitle ?? this.formTitle,
    answersJson: answersJson ?? this.answersJson,
    submittedAtDevice: submittedAtDevice ?? this.submittedAtDevice,
    tzOffsetMin: tzOffsetMin ?? this.tzOffsetMin,
    subLatitude: subLatitude.present ? subLatitude.value : this.subLatitude,
    subLongitude: subLongitude.present ? subLongitude.value : this.subLongitude,
    subAccuracyM: subAccuracyM.present ? subAccuracyM.value : this.subAccuracyM,
    subFixAtDevice: subFixAtDevice.present
        ? subFixAtDevice.value
        : this.subFixAtDevice,
    subLocationStatus: subLocationStatus ?? this.subLocationStatus,
    state: state ?? this.state,
    attempts: attempts ?? this.attempts,
    nextAttemptAt: nextAttemptAt ?? this.nextAttemptAt,
    lastError: lastError.present ? lastError.value : this.lastError,
    serverId: serverId.present ? serverId.value : this.serverId,
    receivedAtServer: receivedAtServer.present
        ? receivedAtServer.value
        : this.receivedAtServer,
    acceptedAtServer: acceptedAtServer.present
        ? acceptedAtServer.value
        : this.acceptedAtServer,
    createdAt: createdAt ?? this.createdAt,
    reference: reference.present ? reference.value : this.reference,
    revision: revision ?? this.revision,
    isLatest: isLatest ?? this.isLatest,
    correctsServerId: correctsServerId.present
        ? correctsServerId.value
        : this.correctsServerId,
    baseRevision: baseRevision.present ? baseRevision.value : this.baseRevision,
    reviewStatus: reviewStatus.present ? reviewStatus.value : this.reviewStatus,
    reviewReason: reviewReason.present ? reviewReason.value : this.reviewReason,
    reviewComment: reviewComment.present
        ? reviewComment.value
        : this.reviewComment,
    reviewFlagsJson: reviewFlagsJson.present
        ? reviewFlagsJson.value
        : this.reviewFlagsJson,
    reviewedAt: reviewedAt.present ? reviewedAt.value : this.reviewedAt,
  );
  LocalSubmission copyWithCompanion(LocalSubmissionsCompanion data) {
    return LocalSubmission(
      localId: data.localId.present ? data.localId.value : this.localId,
      userId: data.userId.present ? data.userId.value : this.userId,
      idempotencyKey: data.idempotencyKey.present
          ? data.idempotencyKey.value
          : this.idempotencyKey,
      formId: data.formId.present ? data.formId.value : this.formId,
      formVersion: data.formVersion.present
          ? data.formVersion.value
          : this.formVersion,
      formTitle: data.formTitle.present ? data.formTitle.value : this.formTitle,
      answersJson: data.answersJson.present
          ? data.answersJson.value
          : this.answersJson,
      submittedAtDevice: data.submittedAtDevice.present
          ? data.submittedAtDevice.value
          : this.submittedAtDevice,
      tzOffsetMin: data.tzOffsetMin.present
          ? data.tzOffsetMin.value
          : this.tzOffsetMin,
      subLatitude: data.subLatitude.present
          ? data.subLatitude.value
          : this.subLatitude,
      subLongitude: data.subLongitude.present
          ? data.subLongitude.value
          : this.subLongitude,
      subAccuracyM: data.subAccuracyM.present
          ? data.subAccuracyM.value
          : this.subAccuracyM,
      subFixAtDevice: data.subFixAtDevice.present
          ? data.subFixAtDevice.value
          : this.subFixAtDevice,
      subLocationStatus: data.subLocationStatus.present
          ? data.subLocationStatus.value
          : this.subLocationStatus,
      state: data.state.present ? data.state.value : this.state,
      attempts: data.attempts.present ? data.attempts.value : this.attempts,
      nextAttemptAt: data.nextAttemptAt.present
          ? data.nextAttemptAt.value
          : this.nextAttemptAt,
      lastError: data.lastError.present ? data.lastError.value : this.lastError,
      serverId: data.serverId.present ? data.serverId.value : this.serverId,
      receivedAtServer: data.receivedAtServer.present
          ? data.receivedAtServer.value
          : this.receivedAtServer,
      acceptedAtServer: data.acceptedAtServer.present
          ? data.acceptedAtServer.value
          : this.acceptedAtServer,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      reference: data.reference.present ? data.reference.value : this.reference,
      revision: data.revision.present ? data.revision.value : this.revision,
      isLatest: data.isLatest.present ? data.isLatest.value : this.isLatest,
      correctsServerId: data.correctsServerId.present
          ? data.correctsServerId.value
          : this.correctsServerId,
      baseRevision: data.baseRevision.present
          ? data.baseRevision.value
          : this.baseRevision,
      reviewStatus: data.reviewStatus.present
          ? data.reviewStatus.value
          : this.reviewStatus,
      reviewReason: data.reviewReason.present
          ? data.reviewReason.value
          : this.reviewReason,
      reviewComment: data.reviewComment.present
          ? data.reviewComment.value
          : this.reviewComment,
      reviewFlagsJson: data.reviewFlagsJson.present
          ? data.reviewFlagsJson.value
          : this.reviewFlagsJson,
      reviewedAt: data.reviewedAt.present
          ? data.reviewedAt.value
          : this.reviewedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalSubmission(')
          ..write('localId: $localId, ')
          ..write('userId: $userId, ')
          ..write('idempotencyKey: $idempotencyKey, ')
          ..write('formId: $formId, ')
          ..write('formVersion: $formVersion, ')
          ..write('formTitle: $formTitle, ')
          ..write('answersJson: $answersJson, ')
          ..write('submittedAtDevice: $submittedAtDevice, ')
          ..write('tzOffsetMin: $tzOffsetMin, ')
          ..write('subLatitude: $subLatitude, ')
          ..write('subLongitude: $subLongitude, ')
          ..write('subAccuracyM: $subAccuracyM, ')
          ..write('subFixAtDevice: $subFixAtDevice, ')
          ..write('subLocationStatus: $subLocationStatus, ')
          ..write('state: $state, ')
          ..write('attempts: $attempts, ')
          ..write('nextAttemptAt: $nextAttemptAt, ')
          ..write('lastError: $lastError, ')
          ..write('serverId: $serverId, ')
          ..write('receivedAtServer: $receivedAtServer, ')
          ..write('acceptedAtServer: $acceptedAtServer, ')
          ..write('createdAt: $createdAt, ')
          ..write('reference: $reference, ')
          ..write('revision: $revision, ')
          ..write('isLatest: $isLatest, ')
          ..write('correctsServerId: $correctsServerId, ')
          ..write('baseRevision: $baseRevision, ')
          ..write('reviewStatus: $reviewStatus, ')
          ..write('reviewReason: $reviewReason, ')
          ..write('reviewComment: $reviewComment, ')
          ..write('reviewFlagsJson: $reviewFlagsJson, ')
          ..write('reviewedAt: $reviewedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hashAll([
    localId,
    userId,
    idempotencyKey,
    formId,
    formVersion,
    formTitle,
    answersJson,
    submittedAtDevice,
    tzOffsetMin,
    subLatitude,
    subLongitude,
    subAccuracyM,
    subFixAtDevice,
    subLocationStatus,
    state,
    attempts,
    nextAttemptAt,
    lastError,
    serverId,
    receivedAtServer,
    acceptedAtServer,
    createdAt,
    reference,
    revision,
    isLatest,
    correctsServerId,
    baseRevision,
    reviewStatus,
    reviewReason,
    reviewComment,
    reviewFlagsJson,
    reviewedAt,
  ]);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LocalSubmission &&
          other.localId == this.localId &&
          other.userId == this.userId &&
          other.idempotencyKey == this.idempotencyKey &&
          other.formId == this.formId &&
          other.formVersion == this.formVersion &&
          other.formTitle == this.formTitle &&
          other.answersJson == this.answersJson &&
          other.submittedAtDevice == this.submittedAtDevice &&
          other.tzOffsetMin == this.tzOffsetMin &&
          other.subLatitude == this.subLatitude &&
          other.subLongitude == this.subLongitude &&
          other.subAccuracyM == this.subAccuracyM &&
          other.subFixAtDevice == this.subFixAtDevice &&
          other.subLocationStatus == this.subLocationStatus &&
          other.state == this.state &&
          other.attempts == this.attempts &&
          other.nextAttemptAt == this.nextAttemptAt &&
          other.lastError == this.lastError &&
          other.serverId == this.serverId &&
          other.receivedAtServer == this.receivedAtServer &&
          other.acceptedAtServer == this.acceptedAtServer &&
          other.createdAt == this.createdAt &&
          other.reference == this.reference &&
          other.revision == this.revision &&
          other.isLatest == this.isLatest &&
          other.correctsServerId == this.correctsServerId &&
          other.baseRevision == this.baseRevision &&
          other.reviewStatus == this.reviewStatus &&
          other.reviewReason == this.reviewReason &&
          other.reviewComment == this.reviewComment &&
          other.reviewFlagsJson == this.reviewFlagsJson &&
          other.reviewedAt == this.reviewedAt);
}

class LocalSubmissionsCompanion extends UpdateCompanion<LocalSubmission> {
  final Value<String> localId;
  final Value<String> userId;
  final Value<String> idempotencyKey;
  final Value<String> formId;
  final Value<int> formVersion;
  final Value<String> formTitle;
  final Value<String> answersJson;
  final Value<DateTime> submittedAtDevice;
  final Value<int> tzOffsetMin;
  final Value<double?> subLatitude;
  final Value<double?> subLongitude;
  final Value<double?> subAccuracyM;
  final Value<DateTime?> subFixAtDevice;
  final Value<String> subLocationStatus;
  final Value<String> state;
  final Value<int> attempts;
  final Value<DateTime> nextAttemptAt;
  final Value<String?> lastError;
  final Value<String?> serverId;
  final Value<DateTime?> receivedAtServer;
  final Value<DateTime?> acceptedAtServer;
  final Value<DateTime> createdAt;
  final Value<String?> reference;
  final Value<int> revision;
  final Value<bool> isLatest;
  final Value<String?> correctsServerId;
  final Value<int?> baseRevision;
  final Value<String?> reviewStatus;
  final Value<String?> reviewReason;
  final Value<String?> reviewComment;
  final Value<String?> reviewFlagsJson;
  final Value<DateTime?> reviewedAt;
  final Value<int> rowid;
  const LocalSubmissionsCompanion({
    this.localId = const Value.absent(),
    this.userId = const Value.absent(),
    this.idempotencyKey = const Value.absent(),
    this.formId = const Value.absent(),
    this.formVersion = const Value.absent(),
    this.formTitle = const Value.absent(),
    this.answersJson = const Value.absent(),
    this.submittedAtDevice = const Value.absent(),
    this.tzOffsetMin = const Value.absent(),
    this.subLatitude = const Value.absent(),
    this.subLongitude = const Value.absent(),
    this.subAccuracyM = const Value.absent(),
    this.subFixAtDevice = const Value.absent(),
    this.subLocationStatus = const Value.absent(),
    this.state = const Value.absent(),
    this.attempts = const Value.absent(),
    this.nextAttemptAt = const Value.absent(),
    this.lastError = const Value.absent(),
    this.serverId = const Value.absent(),
    this.receivedAtServer = const Value.absent(),
    this.acceptedAtServer = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.reference = const Value.absent(),
    this.revision = const Value.absent(),
    this.isLatest = const Value.absent(),
    this.correctsServerId = const Value.absent(),
    this.baseRevision = const Value.absent(),
    this.reviewStatus = const Value.absent(),
    this.reviewReason = const Value.absent(),
    this.reviewComment = const Value.absent(),
    this.reviewFlagsJson = const Value.absent(),
    this.reviewedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  LocalSubmissionsCompanion.insert({
    required String localId,
    required String userId,
    required String idempotencyKey,
    required String formId,
    required int formVersion,
    required String formTitle,
    required String answersJson,
    required DateTime submittedAtDevice,
    required int tzOffsetMin,
    this.subLatitude = const Value.absent(),
    this.subLongitude = const Value.absent(),
    this.subAccuracyM = const Value.absent(),
    this.subFixAtDevice = const Value.absent(),
    required String subLocationStatus,
    required String state,
    this.attempts = const Value.absent(),
    required DateTime nextAttemptAt,
    this.lastError = const Value.absent(),
    this.serverId = const Value.absent(),
    this.receivedAtServer = const Value.absent(),
    this.acceptedAtServer = const Value.absent(),
    required DateTime createdAt,
    this.reference = const Value.absent(),
    this.revision = const Value.absent(),
    this.isLatest = const Value.absent(),
    this.correctsServerId = const Value.absent(),
    this.baseRevision = const Value.absent(),
    this.reviewStatus = const Value.absent(),
    this.reviewReason = const Value.absent(),
    this.reviewComment = const Value.absent(),
    this.reviewFlagsJson = const Value.absent(),
    this.reviewedAt = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : localId = Value(localId),
       userId = Value(userId),
       idempotencyKey = Value(idempotencyKey),
       formId = Value(formId),
       formVersion = Value(formVersion),
       formTitle = Value(formTitle),
       answersJson = Value(answersJson),
       submittedAtDevice = Value(submittedAtDevice),
       tzOffsetMin = Value(tzOffsetMin),
       subLocationStatus = Value(subLocationStatus),
       state = Value(state),
       nextAttemptAt = Value(nextAttemptAt),
       createdAt = Value(createdAt);
  static Insertable<LocalSubmission> custom({
    Expression<String>? localId,
    Expression<String>? userId,
    Expression<String>? idempotencyKey,
    Expression<String>? formId,
    Expression<int>? formVersion,
    Expression<String>? formTitle,
    Expression<String>? answersJson,
    Expression<DateTime>? submittedAtDevice,
    Expression<int>? tzOffsetMin,
    Expression<double>? subLatitude,
    Expression<double>? subLongitude,
    Expression<double>? subAccuracyM,
    Expression<DateTime>? subFixAtDevice,
    Expression<String>? subLocationStatus,
    Expression<String>? state,
    Expression<int>? attempts,
    Expression<DateTime>? nextAttemptAt,
    Expression<String>? lastError,
    Expression<String>? serverId,
    Expression<DateTime>? receivedAtServer,
    Expression<DateTime>? acceptedAtServer,
    Expression<DateTime>? createdAt,
    Expression<String>? reference,
    Expression<int>? revision,
    Expression<bool>? isLatest,
    Expression<String>? correctsServerId,
    Expression<int>? baseRevision,
    Expression<String>? reviewStatus,
    Expression<String>? reviewReason,
    Expression<String>? reviewComment,
    Expression<String>? reviewFlagsJson,
    Expression<DateTime>? reviewedAt,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (localId != null) 'local_id': localId,
      if (userId != null) 'user_id': userId,
      if (idempotencyKey != null) 'idempotency_key': idempotencyKey,
      if (formId != null) 'form_id': formId,
      if (formVersion != null) 'form_version': formVersion,
      if (formTitle != null) 'form_title': formTitle,
      if (answersJson != null) 'answers_json': answersJson,
      if (submittedAtDevice != null) 'submitted_at_device': submittedAtDevice,
      if (tzOffsetMin != null) 'tz_offset_min': tzOffsetMin,
      if (subLatitude != null) 'sub_latitude': subLatitude,
      if (subLongitude != null) 'sub_longitude': subLongitude,
      if (subAccuracyM != null) 'sub_accuracy_m': subAccuracyM,
      if (subFixAtDevice != null) 'sub_fix_at_device': subFixAtDevice,
      if (subLocationStatus != null) 'sub_location_status': subLocationStatus,
      if (state != null) 'state': state,
      if (attempts != null) 'attempts': attempts,
      if (nextAttemptAt != null) 'next_attempt_at': nextAttemptAt,
      if (lastError != null) 'last_error': lastError,
      if (serverId != null) 'server_id': serverId,
      if (receivedAtServer != null) 'received_at_server': receivedAtServer,
      if (acceptedAtServer != null) 'accepted_at_server': acceptedAtServer,
      if (createdAt != null) 'created_at': createdAt,
      if (reference != null) 'reference': reference,
      if (revision != null) 'revision': revision,
      if (isLatest != null) 'is_latest': isLatest,
      if (correctsServerId != null) 'corrects_server_id': correctsServerId,
      if (baseRevision != null) 'base_revision': baseRevision,
      if (reviewStatus != null) 'review_status': reviewStatus,
      if (reviewReason != null) 'review_reason': reviewReason,
      if (reviewComment != null) 'review_comment': reviewComment,
      if (reviewFlagsJson != null) 'review_flags_json': reviewFlagsJson,
      if (reviewedAt != null) 'reviewed_at': reviewedAt,
      if (rowid != null) 'rowid': rowid,
    });
  }

  LocalSubmissionsCompanion copyWith({
    Value<String>? localId,
    Value<String>? userId,
    Value<String>? idempotencyKey,
    Value<String>? formId,
    Value<int>? formVersion,
    Value<String>? formTitle,
    Value<String>? answersJson,
    Value<DateTime>? submittedAtDevice,
    Value<int>? tzOffsetMin,
    Value<double?>? subLatitude,
    Value<double?>? subLongitude,
    Value<double?>? subAccuracyM,
    Value<DateTime?>? subFixAtDevice,
    Value<String>? subLocationStatus,
    Value<String>? state,
    Value<int>? attempts,
    Value<DateTime>? nextAttemptAt,
    Value<String?>? lastError,
    Value<String?>? serverId,
    Value<DateTime?>? receivedAtServer,
    Value<DateTime?>? acceptedAtServer,
    Value<DateTime>? createdAt,
    Value<String?>? reference,
    Value<int>? revision,
    Value<bool>? isLatest,
    Value<String?>? correctsServerId,
    Value<int?>? baseRevision,
    Value<String?>? reviewStatus,
    Value<String?>? reviewReason,
    Value<String?>? reviewComment,
    Value<String?>? reviewFlagsJson,
    Value<DateTime?>? reviewedAt,
    Value<int>? rowid,
  }) {
    return LocalSubmissionsCompanion(
      localId: localId ?? this.localId,
      userId: userId ?? this.userId,
      idempotencyKey: idempotencyKey ?? this.idempotencyKey,
      formId: formId ?? this.formId,
      formVersion: formVersion ?? this.formVersion,
      formTitle: formTitle ?? this.formTitle,
      answersJson: answersJson ?? this.answersJson,
      submittedAtDevice: submittedAtDevice ?? this.submittedAtDevice,
      tzOffsetMin: tzOffsetMin ?? this.tzOffsetMin,
      subLatitude: subLatitude ?? this.subLatitude,
      subLongitude: subLongitude ?? this.subLongitude,
      subAccuracyM: subAccuracyM ?? this.subAccuracyM,
      subFixAtDevice: subFixAtDevice ?? this.subFixAtDevice,
      subLocationStatus: subLocationStatus ?? this.subLocationStatus,
      state: state ?? this.state,
      attempts: attempts ?? this.attempts,
      nextAttemptAt: nextAttemptAt ?? this.nextAttemptAt,
      lastError: lastError ?? this.lastError,
      serverId: serverId ?? this.serverId,
      receivedAtServer: receivedAtServer ?? this.receivedAtServer,
      acceptedAtServer: acceptedAtServer ?? this.acceptedAtServer,
      createdAt: createdAt ?? this.createdAt,
      reference: reference ?? this.reference,
      revision: revision ?? this.revision,
      isLatest: isLatest ?? this.isLatest,
      correctsServerId: correctsServerId ?? this.correctsServerId,
      baseRevision: baseRevision ?? this.baseRevision,
      reviewStatus: reviewStatus ?? this.reviewStatus,
      reviewReason: reviewReason ?? this.reviewReason,
      reviewComment: reviewComment ?? this.reviewComment,
      reviewFlagsJson: reviewFlagsJson ?? this.reviewFlagsJson,
      reviewedAt: reviewedAt ?? this.reviewedAt,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (localId.present) {
      map['local_id'] = Variable<String>(localId.value);
    }
    if (userId.present) {
      map['user_id'] = Variable<String>(userId.value);
    }
    if (idempotencyKey.present) {
      map['idempotency_key'] = Variable<String>(idempotencyKey.value);
    }
    if (formId.present) {
      map['form_id'] = Variable<String>(formId.value);
    }
    if (formVersion.present) {
      map['form_version'] = Variable<int>(formVersion.value);
    }
    if (formTitle.present) {
      map['form_title'] = Variable<String>(formTitle.value);
    }
    if (answersJson.present) {
      map['answers_json'] = Variable<String>(answersJson.value);
    }
    if (submittedAtDevice.present) {
      map['submitted_at_device'] = Variable<DateTime>(submittedAtDevice.value);
    }
    if (tzOffsetMin.present) {
      map['tz_offset_min'] = Variable<int>(tzOffsetMin.value);
    }
    if (subLatitude.present) {
      map['sub_latitude'] = Variable<double>(subLatitude.value);
    }
    if (subLongitude.present) {
      map['sub_longitude'] = Variable<double>(subLongitude.value);
    }
    if (subAccuracyM.present) {
      map['sub_accuracy_m'] = Variable<double>(subAccuracyM.value);
    }
    if (subFixAtDevice.present) {
      map['sub_fix_at_device'] = Variable<DateTime>(subFixAtDevice.value);
    }
    if (subLocationStatus.present) {
      map['sub_location_status'] = Variable<String>(subLocationStatus.value);
    }
    if (state.present) {
      map['state'] = Variable<String>(state.value);
    }
    if (attempts.present) {
      map['attempts'] = Variable<int>(attempts.value);
    }
    if (nextAttemptAt.present) {
      map['next_attempt_at'] = Variable<DateTime>(nextAttemptAt.value);
    }
    if (lastError.present) {
      map['last_error'] = Variable<String>(lastError.value);
    }
    if (serverId.present) {
      map['server_id'] = Variable<String>(serverId.value);
    }
    if (receivedAtServer.present) {
      map['received_at_server'] = Variable<DateTime>(receivedAtServer.value);
    }
    if (acceptedAtServer.present) {
      map['accepted_at_server'] = Variable<DateTime>(acceptedAtServer.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (reference.present) {
      map['reference'] = Variable<String>(reference.value);
    }
    if (revision.present) {
      map['revision'] = Variable<int>(revision.value);
    }
    if (isLatest.present) {
      map['is_latest'] = Variable<bool>(isLatest.value);
    }
    if (correctsServerId.present) {
      map['corrects_server_id'] = Variable<String>(correctsServerId.value);
    }
    if (baseRevision.present) {
      map['base_revision'] = Variable<int>(baseRevision.value);
    }
    if (reviewStatus.present) {
      map['review_status'] = Variable<String>(reviewStatus.value);
    }
    if (reviewReason.present) {
      map['review_reason'] = Variable<String>(reviewReason.value);
    }
    if (reviewComment.present) {
      map['review_comment'] = Variable<String>(reviewComment.value);
    }
    if (reviewFlagsJson.present) {
      map['review_flags_json'] = Variable<String>(reviewFlagsJson.value);
    }
    if (reviewedAt.present) {
      map['reviewed_at'] = Variable<DateTime>(reviewedAt.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalSubmissionsCompanion(')
          ..write('localId: $localId, ')
          ..write('userId: $userId, ')
          ..write('idempotencyKey: $idempotencyKey, ')
          ..write('formId: $formId, ')
          ..write('formVersion: $formVersion, ')
          ..write('formTitle: $formTitle, ')
          ..write('answersJson: $answersJson, ')
          ..write('submittedAtDevice: $submittedAtDevice, ')
          ..write('tzOffsetMin: $tzOffsetMin, ')
          ..write('subLatitude: $subLatitude, ')
          ..write('subLongitude: $subLongitude, ')
          ..write('subAccuracyM: $subAccuracyM, ')
          ..write('subFixAtDevice: $subFixAtDevice, ')
          ..write('subLocationStatus: $subLocationStatus, ')
          ..write('state: $state, ')
          ..write('attempts: $attempts, ')
          ..write('nextAttemptAt: $nextAttemptAt, ')
          ..write('lastError: $lastError, ')
          ..write('serverId: $serverId, ')
          ..write('receivedAtServer: $receivedAtServer, ')
          ..write('acceptedAtServer: $acceptedAtServer, ')
          ..write('createdAt: $createdAt, ')
          ..write('reference: $reference, ')
          ..write('revision: $revision, ')
          ..write('isLatest: $isLatest, ')
          ..write('correctsServerId: $correctsServerId, ')
          ..write('baseRevision: $baseRevision, ')
          ..write('reviewStatus: $reviewStatus, ')
          ..write('reviewReason: $reviewReason, ')
          ..write('reviewComment: $reviewComment, ')
          ..write('reviewFlagsJson: $reviewFlagsJson, ')
          ..write('reviewedAt: $reviewedAt, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $LocalPhotosTable extends LocalPhotos
    with TableInfo<$LocalPhotosTable, LocalPhoto> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalPhotosTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<String> id = GeneratedColumn<String>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _draftIdMeta = const VerificationMeta(
    'draftId',
  );
  @override
  late final GeneratedColumn<String> draftId = GeneratedColumn<String>(
    'draft_id',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _submissionLocalIdMeta = const VerificationMeta(
    'submissionLocalId',
  );
  @override
  late final GeneratedColumn<String> submissionLocalId =
      GeneratedColumn<String>(
        'submission_local_id',
        aliasedName,
        true,
        type: DriftSqlType.string,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _filePathMeta = const VerificationMeta(
    'filePath',
  );
  @override
  late final GeneratedColumn<String> filePath = GeneratedColumn<String>(
    'file_path',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sha256Meta = const VerificationMeta('sha256');
  @override
  late final GeneratedColumn<String> sha256 = GeneratedColumn<String>(
    'sha256',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sizeBytesMeta = const VerificationMeta(
    'sizeBytes',
  );
  @override
  late final GeneratedColumn<int> sizeBytes = GeneratedColumn<int>(
    'size_bytes',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _mimeTypeMeta = const VerificationMeta(
    'mimeType',
  );
  @override
  late final GeneratedColumn<String> mimeType = GeneratedColumn<String>(
    'mime_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _capturedAtDeviceMeta = const VerificationMeta(
    'capturedAtDevice',
  );
  @override
  late final GeneratedColumn<DateTime> capturedAtDevice =
      GeneratedColumn<DateTime>(
        'captured_at_device',
        aliasedName,
        false,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: true,
      );
  static const VerificationMeta _latitudeMeta = const VerificationMeta(
    'latitude',
  );
  @override
  late final GeneratedColumn<double> latitude = GeneratedColumn<double>(
    'latitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _longitudeMeta = const VerificationMeta(
    'longitude',
  );
  @override
  late final GeneratedColumn<double> longitude = GeneratedColumn<double>(
    'longitude',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _accuracyMMeta = const VerificationMeta(
    'accuracyM',
  );
  @override
  late final GeneratedColumn<double> accuracyM = GeneratedColumn<double>(
    'accuracy_m',
    aliasedName,
    true,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _locationFixAtDeviceMeta =
      const VerificationMeta('locationFixAtDevice');
  @override
  late final GeneratedColumn<DateTime> locationFixAtDevice =
      GeneratedColumn<DateTime>(
        'location_fix_at_device',
        aliasedName,
        true,
        type: DriftSqlType.dateTime,
        requiredDuringInsert: false,
      );
  static const VerificationMeta _locationStatusMeta = const VerificationMeta(
    'locationStatus',
  );
  @override
  late final GeneratedColumn<String> locationStatus = GeneratedColumn<String>(
    'location_status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _locationSourceMeta = const VerificationMeta(
    'locationSource',
  );
  @override
  late final GeneratedColumn<String> locationSource = GeneratedColumn<String>(
    'location_source',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _uploadStateMeta = const VerificationMeta(
    'uploadState',
  );
  @override
  late final GeneratedColumn<String> uploadState = GeneratedColumn<String>(
    'upload_state',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('pending'),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    draftId,
    submissionLocalId,
    filePath,
    sha256,
    sizeBytes,
    mimeType,
    capturedAtDevice,
    latitude,
    longitude,
    accuracyM,
    locationFixAtDevice,
    locationStatus,
    locationSource,
    uploadState,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_photos';
  @override
  VerificationContext validateIntegrity(
    Insertable<LocalPhoto> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    } else if (isInserting) {
      context.missing(_idMeta);
    }
    if (data.containsKey('draft_id')) {
      context.handle(
        _draftIdMeta,
        draftId.isAcceptableOrUnknown(data['draft_id']!, _draftIdMeta),
      );
    }
    if (data.containsKey('submission_local_id')) {
      context.handle(
        _submissionLocalIdMeta,
        submissionLocalId.isAcceptableOrUnknown(
          data['submission_local_id']!,
          _submissionLocalIdMeta,
        ),
      );
    }
    if (data.containsKey('file_path')) {
      context.handle(
        _filePathMeta,
        filePath.isAcceptableOrUnknown(data['file_path']!, _filePathMeta),
      );
    } else if (isInserting) {
      context.missing(_filePathMeta);
    }
    if (data.containsKey('sha256')) {
      context.handle(
        _sha256Meta,
        sha256.isAcceptableOrUnknown(data['sha256']!, _sha256Meta),
      );
    } else if (isInserting) {
      context.missing(_sha256Meta);
    }
    if (data.containsKey('size_bytes')) {
      context.handle(
        _sizeBytesMeta,
        sizeBytes.isAcceptableOrUnknown(data['size_bytes']!, _sizeBytesMeta),
      );
    } else if (isInserting) {
      context.missing(_sizeBytesMeta);
    }
    if (data.containsKey('mime_type')) {
      context.handle(
        _mimeTypeMeta,
        mimeType.isAcceptableOrUnknown(data['mime_type']!, _mimeTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_mimeTypeMeta);
    }
    if (data.containsKey('captured_at_device')) {
      context.handle(
        _capturedAtDeviceMeta,
        capturedAtDevice.isAcceptableOrUnknown(
          data['captured_at_device']!,
          _capturedAtDeviceMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_capturedAtDeviceMeta);
    }
    if (data.containsKey('latitude')) {
      context.handle(
        _latitudeMeta,
        latitude.isAcceptableOrUnknown(data['latitude']!, _latitudeMeta),
      );
    }
    if (data.containsKey('longitude')) {
      context.handle(
        _longitudeMeta,
        longitude.isAcceptableOrUnknown(data['longitude']!, _longitudeMeta),
      );
    }
    if (data.containsKey('accuracy_m')) {
      context.handle(
        _accuracyMMeta,
        accuracyM.isAcceptableOrUnknown(data['accuracy_m']!, _accuracyMMeta),
      );
    }
    if (data.containsKey('location_fix_at_device')) {
      context.handle(
        _locationFixAtDeviceMeta,
        locationFixAtDevice.isAcceptableOrUnknown(
          data['location_fix_at_device']!,
          _locationFixAtDeviceMeta,
        ),
      );
    }
    if (data.containsKey('location_status')) {
      context.handle(
        _locationStatusMeta,
        locationStatus.isAcceptableOrUnknown(
          data['location_status']!,
          _locationStatusMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_locationStatusMeta);
    }
    if (data.containsKey('location_source')) {
      context.handle(
        _locationSourceMeta,
        locationSource.isAcceptableOrUnknown(
          data['location_source']!,
          _locationSourceMeta,
        ),
      );
    }
    if (data.containsKey('upload_state')) {
      context.handle(
        _uploadStateMeta,
        uploadState.isAcceptableOrUnknown(
          data['upload_state']!,
          _uploadStateMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LocalPhoto map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalPhoto(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id'],
      )!,
      draftId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}draft_id'],
      ),
      submissionLocalId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}submission_local_id'],
      ),
      filePath: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}file_path'],
      )!,
      sha256: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sha256'],
      )!,
      sizeBytes: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}size_bytes'],
      )!,
      mimeType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}mime_type'],
      )!,
      capturedAtDevice: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}captured_at_device'],
      )!,
      latitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}latitude'],
      ),
      longitude: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}longitude'],
      ),
      accuracyM: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}accuracy_m'],
      ),
      locationFixAtDevice: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}location_fix_at_device'],
      ),
      locationStatus: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}location_status'],
      )!,
      locationSource: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}location_source'],
      ),
      uploadState: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}upload_state'],
      )!,
    );
  }

  @override
  $LocalPhotosTable createAlias(String alias) {
    return $LocalPhotosTable(attachedDatabase, alias);
  }
}

class LocalPhoto extends DataClass implements Insertable<LocalPhoto> {
  final String id;
  final String? draftId;
  final String? submissionLocalId;
  final String filePath;
  final String sha256;
  final int sizeBytes;
  final String mimeType;
  final DateTime capturedAtDevice;
  final double? latitude;
  final double? longitude;
  final double? accuracyM;
  final DateTime? locationFixAtDevice;
  final String locationStatus;
  final String? locationSource;

  /// pending | uploaded
  final String uploadState;
  const LocalPhoto({
    required this.id,
    this.draftId,
    this.submissionLocalId,
    required this.filePath,
    required this.sha256,
    required this.sizeBytes,
    required this.mimeType,
    required this.capturedAtDevice,
    this.latitude,
    this.longitude,
    this.accuracyM,
    this.locationFixAtDevice,
    required this.locationStatus,
    this.locationSource,
    required this.uploadState,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<String>(id);
    if (!nullToAbsent || draftId != null) {
      map['draft_id'] = Variable<String>(draftId);
    }
    if (!nullToAbsent || submissionLocalId != null) {
      map['submission_local_id'] = Variable<String>(submissionLocalId);
    }
    map['file_path'] = Variable<String>(filePath);
    map['sha256'] = Variable<String>(sha256);
    map['size_bytes'] = Variable<int>(sizeBytes);
    map['mime_type'] = Variable<String>(mimeType);
    map['captured_at_device'] = Variable<DateTime>(capturedAtDevice);
    if (!nullToAbsent || latitude != null) {
      map['latitude'] = Variable<double>(latitude);
    }
    if (!nullToAbsent || longitude != null) {
      map['longitude'] = Variable<double>(longitude);
    }
    if (!nullToAbsent || accuracyM != null) {
      map['accuracy_m'] = Variable<double>(accuracyM);
    }
    if (!nullToAbsent || locationFixAtDevice != null) {
      map['location_fix_at_device'] = Variable<DateTime>(locationFixAtDevice);
    }
    map['location_status'] = Variable<String>(locationStatus);
    if (!nullToAbsent || locationSource != null) {
      map['location_source'] = Variable<String>(locationSource);
    }
    map['upload_state'] = Variable<String>(uploadState);
    return map;
  }

  LocalPhotosCompanion toCompanion(bool nullToAbsent) {
    return LocalPhotosCompanion(
      id: Value(id),
      draftId: draftId == null && nullToAbsent
          ? const Value.absent()
          : Value(draftId),
      submissionLocalId: submissionLocalId == null && nullToAbsent
          ? const Value.absent()
          : Value(submissionLocalId),
      filePath: Value(filePath),
      sha256: Value(sha256),
      sizeBytes: Value(sizeBytes),
      mimeType: Value(mimeType),
      capturedAtDevice: Value(capturedAtDevice),
      latitude: latitude == null && nullToAbsent
          ? const Value.absent()
          : Value(latitude),
      longitude: longitude == null && nullToAbsent
          ? const Value.absent()
          : Value(longitude),
      accuracyM: accuracyM == null && nullToAbsent
          ? const Value.absent()
          : Value(accuracyM),
      locationFixAtDevice: locationFixAtDevice == null && nullToAbsent
          ? const Value.absent()
          : Value(locationFixAtDevice),
      locationStatus: Value(locationStatus),
      locationSource: locationSource == null && nullToAbsent
          ? const Value.absent()
          : Value(locationSource),
      uploadState: Value(uploadState),
    );
  }

  factory LocalPhoto.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalPhoto(
      id: serializer.fromJson<String>(json['id']),
      draftId: serializer.fromJson<String?>(json['draftId']),
      submissionLocalId: serializer.fromJson<String?>(
        json['submissionLocalId'],
      ),
      filePath: serializer.fromJson<String>(json['filePath']),
      sha256: serializer.fromJson<String>(json['sha256']),
      sizeBytes: serializer.fromJson<int>(json['sizeBytes']),
      mimeType: serializer.fromJson<String>(json['mimeType']),
      capturedAtDevice: serializer.fromJson<DateTime>(json['capturedAtDevice']),
      latitude: serializer.fromJson<double?>(json['latitude']),
      longitude: serializer.fromJson<double?>(json['longitude']),
      accuracyM: serializer.fromJson<double?>(json['accuracyM']),
      locationFixAtDevice: serializer.fromJson<DateTime?>(
        json['locationFixAtDevice'],
      ),
      locationStatus: serializer.fromJson<String>(json['locationStatus']),
      locationSource: serializer.fromJson<String?>(json['locationSource']),
      uploadState: serializer.fromJson<String>(json['uploadState']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<String>(id),
      'draftId': serializer.toJson<String?>(draftId),
      'submissionLocalId': serializer.toJson<String?>(submissionLocalId),
      'filePath': serializer.toJson<String>(filePath),
      'sha256': serializer.toJson<String>(sha256),
      'sizeBytes': serializer.toJson<int>(sizeBytes),
      'mimeType': serializer.toJson<String>(mimeType),
      'capturedAtDevice': serializer.toJson<DateTime>(capturedAtDevice),
      'latitude': serializer.toJson<double?>(latitude),
      'longitude': serializer.toJson<double?>(longitude),
      'accuracyM': serializer.toJson<double?>(accuracyM),
      'locationFixAtDevice': serializer.toJson<DateTime?>(locationFixAtDevice),
      'locationStatus': serializer.toJson<String>(locationStatus),
      'locationSource': serializer.toJson<String?>(locationSource),
      'uploadState': serializer.toJson<String>(uploadState),
    };
  }

  LocalPhoto copyWith({
    String? id,
    Value<String?> draftId = const Value.absent(),
    Value<String?> submissionLocalId = const Value.absent(),
    String? filePath,
    String? sha256,
    int? sizeBytes,
    String? mimeType,
    DateTime? capturedAtDevice,
    Value<double?> latitude = const Value.absent(),
    Value<double?> longitude = const Value.absent(),
    Value<double?> accuracyM = const Value.absent(),
    Value<DateTime?> locationFixAtDevice = const Value.absent(),
    String? locationStatus,
    Value<String?> locationSource = const Value.absent(),
    String? uploadState,
  }) => LocalPhoto(
    id: id ?? this.id,
    draftId: draftId.present ? draftId.value : this.draftId,
    submissionLocalId: submissionLocalId.present
        ? submissionLocalId.value
        : this.submissionLocalId,
    filePath: filePath ?? this.filePath,
    sha256: sha256 ?? this.sha256,
    sizeBytes: sizeBytes ?? this.sizeBytes,
    mimeType: mimeType ?? this.mimeType,
    capturedAtDevice: capturedAtDevice ?? this.capturedAtDevice,
    latitude: latitude.present ? latitude.value : this.latitude,
    longitude: longitude.present ? longitude.value : this.longitude,
    accuracyM: accuracyM.present ? accuracyM.value : this.accuracyM,
    locationFixAtDevice: locationFixAtDevice.present
        ? locationFixAtDevice.value
        : this.locationFixAtDevice,
    locationStatus: locationStatus ?? this.locationStatus,
    locationSource: locationSource.present
        ? locationSource.value
        : this.locationSource,
    uploadState: uploadState ?? this.uploadState,
  );
  LocalPhoto copyWithCompanion(LocalPhotosCompanion data) {
    return LocalPhoto(
      id: data.id.present ? data.id.value : this.id,
      draftId: data.draftId.present ? data.draftId.value : this.draftId,
      submissionLocalId: data.submissionLocalId.present
          ? data.submissionLocalId.value
          : this.submissionLocalId,
      filePath: data.filePath.present ? data.filePath.value : this.filePath,
      sha256: data.sha256.present ? data.sha256.value : this.sha256,
      sizeBytes: data.sizeBytes.present ? data.sizeBytes.value : this.sizeBytes,
      mimeType: data.mimeType.present ? data.mimeType.value : this.mimeType,
      capturedAtDevice: data.capturedAtDevice.present
          ? data.capturedAtDevice.value
          : this.capturedAtDevice,
      latitude: data.latitude.present ? data.latitude.value : this.latitude,
      longitude: data.longitude.present ? data.longitude.value : this.longitude,
      accuracyM: data.accuracyM.present ? data.accuracyM.value : this.accuracyM,
      locationFixAtDevice: data.locationFixAtDevice.present
          ? data.locationFixAtDevice.value
          : this.locationFixAtDevice,
      locationStatus: data.locationStatus.present
          ? data.locationStatus.value
          : this.locationStatus,
      locationSource: data.locationSource.present
          ? data.locationSource.value
          : this.locationSource,
      uploadState: data.uploadState.present
          ? data.uploadState.value
          : this.uploadState,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalPhoto(')
          ..write('id: $id, ')
          ..write('draftId: $draftId, ')
          ..write('submissionLocalId: $submissionLocalId, ')
          ..write('filePath: $filePath, ')
          ..write('sha256: $sha256, ')
          ..write('sizeBytes: $sizeBytes, ')
          ..write('mimeType: $mimeType, ')
          ..write('capturedAtDevice: $capturedAtDevice, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('accuracyM: $accuracyM, ')
          ..write('locationFixAtDevice: $locationFixAtDevice, ')
          ..write('locationStatus: $locationStatus, ')
          ..write('locationSource: $locationSource, ')
          ..write('uploadState: $uploadState')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    draftId,
    submissionLocalId,
    filePath,
    sha256,
    sizeBytes,
    mimeType,
    capturedAtDevice,
    latitude,
    longitude,
    accuracyM,
    locationFixAtDevice,
    locationStatus,
    locationSource,
    uploadState,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LocalPhoto &&
          other.id == this.id &&
          other.draftId == this.draftId &&
          other.submissionLocalId == this.submissionLocalId &&
          other.filePath == this.filePath &&
          other.sha256 == this.sha256 &&
          other.sizeBytes == this.sizeBytes &&
          other.mimeType == this.mimeType &&
          other.capturedAtDevice == this.capturedAtDevice &&
          other.latitude == this.latitude &&
          other.longitude == this.longitude &&
          other.accuracyM == this.accuracyM &&
          other.locationFixAtDevice == this.locationFixAtDevice &&
          other.locationStatus == this.locationStatus &&
          other.locationSource == this.locationSource &&
          other.uploadState == this.uploadState);
}

class LocalPhotosCompanion extends UpdateCompanion<LocalPhoto> {
  final Value<String> id;
  final Value<String?> draftId;
  final Value<String?> submissionLocalId;
  final Value<String> filePath;
  final Value<String> sha256;
  final Value<int> sizeBytes;
  final Value<String> mimeType;
  final Value<DateTime> capturedAtDevice;
  final Value<double?> latitude;
  final Value<double?> longitude;
  final Value<double?> accuracyM;
  final Value<DateTime?> locationFixAtDevice;
  final Value<String> locationStatus;
  final Value<String?> locationSource;
  final Value<String> uploadState;
  final Value<int> rowid;
  const LocalPhotosCompanion({
    this.id = const Value.absent(),
    this.draftId = const Value.absent(),
    this.submissionLocalId = const Value.absent(),
    this.filePath = const Value.absent(),
    this.sha256 = const Value.absent(),
    this.sizeBytes = const Value.absent(),
    this.mimeType = const Value.absent(),
    this.capturedAtDevice = const Value.absent(),
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.accuracyM = const Value.absent(),
    this.locationFixAtDevice = const Value.absent(),
    this.locationStatus = const Value.absent(),
    this.locationSource = const Value.absent(),
    this.uploadState = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  LocalPhotosCompanion.insert({
    required String id,
    this.draftId = const Value.absent(),
    this.submissionLocalId = const Value.absent(),
    required String filePath,
    required String sha256,
    required int sizeBytes,
    required String mimeType,
    required DateTime capturedAtDevice,
    this.latitude = const Value.absent(),
    this.longitude = const Value.absent(),
    this.accuracyM = const Value.absent(),
    this.locationFixAtDevice = const Value.absent(),
    required String locationStatus,
    this.locationSource = const Value.absent(),
    this.uploadState = const Value.absent(),
    this.rowid = const Value.absent(),
  }) : id = Value(id),
       filePath = Value(filePath),
       sha256 = Value(sha256),
       sizeBytes = Value(sizeBytes),
       mimeType = Value(mimeType),
       capturedAtDevice = Value(capturedAtDevice),
       locationStatus = Value(locationStatus);
  static Insertable<LocalPhoto> custom({
    Expression<String>? id,
    Expression<String>? draftId,
    Expression<String>? submissionLocalId,
    Expression<String>? filePath,
    Expression<String>? sha256,
    Expression<int>? sizeBytes,
    Expression<String>? mimeType,
    Expression<DateTime>? capturedAtDevice,
    Expression<double>? latitude,
    Expression<double>? longitude,
    Expression<double>? accuracyM,
    Expression<DateTime>? locationFixAtDevice,
    Expression<String>? locationStatus,
    Expression<String>? locationSource,
    Expression<String>? uploadState,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (draftId != null) 'draft_id': draftId,
      if (submissionLocalId != null) 'submission_local_id': submissionLocalId,
      if (filePath != null) 'file_path': filePath,
      if (sha256 != null) 'sha256': sha256,
      if (sizeBytes != null) 'size_bytes': sizeBytes,
      if (mimeType != null) 'mime_type': mimeType,
      if (capturedAtDevice != null) 'captured_at_device': capturedAtDevice,
      if (latitude != null) 'latitude': latitude,
      if (longitude != null) 'longitude': longitude,
      if (accuracyM != null) 'accuracy_m': accuracyM,
      if (locationFixAtDevice != null)
        'location_fix_at_device': locationFixAtDevice,
      if (locationStatus != null) 'location_status': locationStatus,
      if (locationSource != null) 'location_source': locationSource,
      if (uploadState != null) 'upload_state': uploadState,
      if (rowid != null) 'rowid': rowid,
    });
  }

  LocalPhotosCompanion copyWith({
    Value<String>? id,
    Value<String?>? draftId,
    Value<String?>? submissionLocalId,
    Value<String>? filePath,
    Value<String>? sha256,
    Value<int>? sizeBytes,
    Value<String>? mimeType,
    Value<DateTime>? capturedAtDevice,
    Value<double?>? latitude,
    Value<double?>? longitude,
    Value<double?>? accuracyM,
    Value<DateTime?>? locationFixAtDevice,
    Value<String>? locationStatus,
    Value<String?>? locationSource,
    Value<String>? uploadState,
    Value<int>? rowid,
  }) {
    return LocalPhotosCompanion(
      id: id ?? this.id,
      draftId: draftId ?? this.draftId,
      submissionLocalId: submissionLocalId ?? this.submissionLocalId,
      filePath: filePath ?? this.filePath,
      sha256: sha256 ?? this.sha256,
      sizeBytes: sizeBytes ?? this.sizeBytes,
      mimeType: mimeType ?? this.mimeType,
      capturedAtDevice: capturedAtDevice ?? this.capturedAtDevice,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      accuracyM: accuracyM ?? this.accuracyM,
      locationFixAtDevice: locationFixAtDevice ?? this.locationFixAtDevice,
      locationStatus: locationStatus ?? this.locationStatus,
      locationSource: locationSource ?? this.locationSource,
      uploadState: uploadState ?? this.uploadState,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<String>(id.value);
    }
    if (draftId.present) {
      map['draft_id'] = Variable<String>(draftId.value);
    }
    if (submissionLocalId.present) {
      map['submission_local_id'] = Variable<String>(submissionLocalId.value);
    }
    if (filePath.present) {
      map['file_path'] = Variable<String>(filePath.value);
    }
    if (sha256.present) {
      map['sha256'] = Variable<String>(sha256.value);
    }
    if (sizeBytes.present) {
      map['size_bytes'] = Variable<int>(sizeBytes.value);
    }
    if (mimeType.present) {
      map['mime_type'] = Variable<String>(mimeType.value);
    }
    if (capturedAtDevice.present) {
      map['captured_at_device'] = Variable<DateTime>(capturedAtDevice.value);
    }
    if (latitude.present) {
      map['latitude'] = Variable<double>(latitude.value);
    }
    if (longitude.present) {
      map['longitude'] = Variable<double>(longitude.value);
    }
    if (accuracyM.present) {
      map['accuracy_m'] = Variable<double>(accuracyM.value);
    }
    if (locationFixAtDevice.present) {
      map['location_fix_at_device'] = Variable<DateTime>(
        locationFixAtDevice.value,
      );
    }
    if (locationStatus.present) {
      map['location_status'] = Variable<String>(locationStatus.value);
    }
    if (locationSource.present) {
      map['location_source'] = Variable<String>(locationSource.value);
    }
    if (uploadState.present) {
      map['upload_state'] = Variable<String>(uploadState.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalPhotosCompanion(')
          ..write('id: $id, ')
          ..write('draftId: $draftId, ')
          ..write('submissionLocalId: $submissionLocalId, ')
          ..write('filePath: $filePath, ')
          ..write('sha256: $sha256, ')
          ..write('sizeBytes: $sizeBytes, ')
          ..write('mimeType: $mimeType, ')
          ..write('capturedAtDevice: $capturedAtDevice, ')
          ..write('latitude: $latitude, ')
          ..write('longitude: $longitude, ')
          ..write('accuracyM: $accuracyM, ')
          ..write('locationFixAtDevice: $locationFixAtDevice, ')
          ..write('locationStatus: $locationStatus, ')
          ..write('locationSource: $locationSource, ')
          ..write('uploadState: $uploadState, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $KeyValuesTable extends KeyValues
    with TableInfo<$KeyValuesTable, KeyValue> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $KeyValuesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _keyMeta = const VerificationMeta('key');
  @override
  late final GeneratedColumn<String> key = GeneratedColumn<String>(
    'key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _valueMeta = const VerificationMeta('value');
  @override
  late final GeneratedColumn<String> value = GeneratedColumn<String>(
    'value',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [key, value];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'key_values';
  @override
  VerificationContext validateIntegrity(
    Insertable<KeyValue> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('key')) {
      context.handle(
        _keyMeta,
        key.isAcceptableOrUnknown(data['key']!, _keyMeta),
      );
    } else if (isInserting) {
      context.missing(_keyMeta);
    }
    if (data.containsKey('value')) {
      context.handle(
        _valueMeta,
        value.isAcceptableOrUnknown(data['value']!, _valueMeta),
      );
    } else if (isInserting) {
      context.missing(_valueMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {key};
  @override
  KeyValue map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return KeyValue(
      key: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}key'],
      )!,
      value: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}value'],
      )!,
    );
  }

  @override
  $KeyValuesTable createAlias(String alias) {
    return $KeyValuesTable(attachedDatabase, alias);
  }
}

class KeyValue extends DataClass implements Insertable<KeyValue> {
  final String key;
  final String value;
  const KeyValue({required this.key, required this.value});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['key'] = Variable<String>(key);
    map['value'] = Variable<String>(value);
    return map;
  }

  KeyValuesCompanion toCompanion(bool nullToAbsent) {
    return KeyValuesCompanion(key: Value(key), value: Value(value));
  }

  factory KeyValue.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return KeyValue(
      key: serializer.fromJson<String>(json['key']),
      value: serializer.fromJson<String>(json['value']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'key': serializer.toJson<String>(key),
      'value': serializer.toJson<String>(value),
    };
  }

  KeyValue copyWith({String? key, String? value}) =>
      KeyValue(key: key ?? this.key, value: value ?? this.value);
  KeyValue copyWithCompanion(KeyValuesCompanion data) {
    return KeyValue(
      key: data.key.present ? data.key.value : this.key,
      value: data.value.present ? data.value.value : this.value,
    );
  }

  @override
  String toString() {
    return (StringBuffer('KeyValue(')
          ..write('key: $key, ')
          ..write('value: $value')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(key, value);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is KeyValue && other.key == this.key && other.value == this.value);
}

class KeyValuesCompanion extends UpdateCompanion<KeyValue> {
  final Value<String> key;
  final Value<String> value;
  final Value<int> rowid;
  const KeyValuesCompanion({
    this.key = const Value.absent(),
    this.value = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  KeyValuesCompanion.insert({
    required String key,
    required String value,
    this.rowid = const Value.absent(),
  }) : key = Value(key),
       value = Value(value);
  static Insertable<KeyValue> custom({
    Expression<String>? key,
    Expression<String>? value,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (key != null) 'key': key,
      if (value != null) 'value': value,
      if (rowid != null) 'rowid': rowid,
    });
  }

  KeyValuesCompanion copyWith({
    Value<String>? key,
    Value<String>? value,
    Value<int>? rowid,
  }) {
    return KeyValuesCompanion(
      key: key ?? this.key,
      value: value ?? this.value,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (key.present) {
      map['key'] = Variable<String>(key.value);
    }
    if (value.present) {
      map['value'] = Variable<String>(value.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('KeyValuesCompanion(')
          ..write('key: $key, ')
          ..write('value: $value, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $CachedFormsTable cachedForms = $CachedFormsTable(this);
  late final $DraftsTable drafts = $DraftsTable(this);
  late final $LocalSubmissionsTable localSubmissions = $LocalSubmissionsTable(
    this,
  );
  late final $LocalPhotosTable localPhotos = $LocalPhotosTable(this);
  late final $KeyValuesTable keyValues = $KeyValuesTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    cachedForms,
    drafts,
    localSubmissions,
    localPhotos,
    keyValues,
  ];
}

typedef $$CachedFormsTableCreateCompanionBuilder =
    CachedFormsCompanion Function({
      required String formId,
      required int version,
      required String title,
      required String schemaJson,
      required DateTime fetchedAt,
      Value<int> rowid,
    });
typedef $$CachedFormsTableUpdateCompanionBuilder =
    CachedFormsCompanion Function({
      Value<String> formId,
      Value<int> version,
      Value<String> title,
      Value<String> schemaJson,
      Value<DateTime> fetchedAt,
      Value<int> rowid,
    });

class $$CachedFormsTableFilterComposer
    extends Composer<_$AppDatabase, $CachedFormsTable> {
  $$CachedFormsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get version => $composableBuilder(
    column: $table.version,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get schemaJson => $composableBuilder(
    column: $table.schemaJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$CachedFormsTableOrderingComposer
    extends Composer<_$AppDatabase, $CachedFormsTable> {
  $$CachedFormsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get version => $composableBuilder(
    column: $table.version,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get schemaJson => $composableBuilder(
    column: $table.schemaJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get fetchedAt => $composableBuilder(
    column: $table.fetchedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$CachedFormsTableAnnotationComposer
    extends Composer<_$AppDatabase, $CachedFormsTable> {
  $$CachedFormsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get formId =>
      $composableBuilder(column: $table.formId, builder: (column) => column);

  GeneratedColumn<int> get version =>
      $composableBuilder(column: $table.version, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get schemaJson => $composableBuilder(
    column: $table.schemaJson,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get fetchedAt =>
      $composableBuilder(column: $table.fetchedAt, builder: (column) => column);
}

class $$CachedFormsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $CachedFormsTable,
          CachedForm,
          $$CachedFormsTableFilterComposer,
          $$CachedFormsTableOrderingComposer,
          $$CachedFormsTableAnnotationComposer,
          $$CachedFormsTableCreateCompanionBuilder,
          $$CachedFormsTableUpdateCompanionBuilder,
          (
            CachedForm,
            BaseReferences<_$AppDatabase, $CachedFormsTable, CachedForm>,
          ),
          CachedForm,
          PrefetchHooks Function()
        > {
  $$CachedFormsTableTableManager(_$AppDatabase db, $CachedFormsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$CachedFormsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$CachedFormsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$CachedFormsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> formId = const Value.absent(),
                Value<int> version = const Value.absent(),
                Value<String> title = const Value.absent(),
                Value<String> schemaJson = const Value.absent(),
                Value<DateTime> fetchedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => CachedFormsCompanion(
                formId: formId,
                version: version,
                title: title,
                schemaJson: schemaJson,
                fetchedAt: fetchedAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String formId,
                required int version,
                required String title,
                required String schemaJson,
                required DateTime fetchedAt,
                Value<int> rowid = const Value.absent(),
              }) => CachedFormsCompanion.insert(
                formId: formId,
                version: version,
                title: title,
                schemaJson: schemaJson,
                fetchedAt: fetchedAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$CachedFormsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $CachedFormsTable,
      CachedForm,
      $$CachedFormsTableFilterComposer,
      $$CachedFormsTableOrderingComposer,
      $$CachedFormsTableAnnotationComposer,
      $$CachedFormsTableCreateCompanionBuilder,
      $$CachedFormsTableUpdateCompanionBuilder,
      (
        CachedForm,
        BaseReferences<_$AppDatabase, $CachedFormsTable, CachedForm>,
      ),
      CachedForm,
      PrefetchHooks Function()
    >;
typedef $$DraftsTableCreateCompanionBuilder =
    DraftsCompanion Function({
      required String id,
      required String userId,
      required String formId,
      required int formVersion,
      required String answersJson,
      required DateTime createdAt,
      required DateTime updatedAt,
      Value<String?> correctsServerId,
      Value<int?> baseRevision,
      Value<String?> correctsLocalId,
      Value<String?> reference,
      Value<int> rowid,
    });
typedef $$DraftsTableUpdateCompanionBuilder =
    DraftsCompanion Function({
      Value<String> id,
      Value<String> userId,
      Value<String> formId,
      Value<int> formVersion,
      Value<String> answersJson,
      Value<DateTime> createdAt,
      Value<DateTime> updatedAt,
      Value<String?> correctsServerId,
      Value<int?> baseRevision,
      Value<String?> correctsLocalId,
      Value<String?> reference,
      Value<int> rowid,
    });

class $$DraftsTableFilterComposer
    extends Composer<_$AppDatabase, $DraftsTable> {
  $$DraftsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get userId => $composableBuilder(
    column: $table.userId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get formVersion => $composableBuilder(
    column: $table.formVersion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get correctsServerId => $composableBuilder(
    column: $table.correctsServerId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get baseRevision => $composableBuilder(
    column: $table.baseRevision,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get correctsLocalId => $composableBuilder(
    column: $table.correctsLocalId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get reference => $composableBuilder(
    column: $table.reference,
    builder: (column) => ColumnFilters(column),
  );
}

class $$DraftsTableOrderingComposer
    extends Composer<_$AppDatabase, $DraftsTable> {
  $$DraftsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get userId => $composableBuilder(
    column: $table.userId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get formVersion => $composableBuilder(
    column: $table.formVersion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get correctsServerId => $composableBuilder(
    column: $table.correctsServerId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get baseRevision => $composableBuilder(
    column: $table.baseRevision,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get correctsLocalId => $composableBuilder(
    column: $table.correctsLocalId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get reference => $composableBuilder(
    column: $table.reference,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$DraftsTableAnnotationComposer
    extends Composer<_$AppDatabase, $DraftsTable> {
  $$DraftsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get userId =>
      $composableBuilder(column: $table.userId, builder: (column) => column);

  GeneratedColumn<String> get formId =>
      $composableBuilder(column: $table.formId, builder: (column) => column);

  GeneratedColumn<int> get formVersion => $composableBuilder(
    column: $table.formVersion,
    builder: (column) => column,
  );

  GeneratedColumn<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<DateTime> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);

  GeneratedColumn<String> get correctsServerId => $composableBuilder(
    column: $table.correctsServerId,
    builder: (column) => column,
  );

  GeneratedColumn<int> get baseRevision => $composableBuilder(
    column: $table.baseRevision,
    builder: (column) => column,
  );

  GeneratedColumn<String> get correctsLocalId => $composableBuilder(
    column: $table.correctsLocalId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get reference =>
      $composableBuilder(column: $table.reference, builder: (column) => column);
}

class $$DraftsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $DraftsTable,
          Draft,
          $$DraftsTableFilterComposer,
          $$DraftsTableOrderingComposer,
          $$DraftsTableAnnotationComposer,
          $$DraftsTableCreateCompanionBuilder,
          $$DraftsTableUpdateCompanionBuilder,
          (Draft, BaseReferences<_$AppDatabase, $DraftsTable, Draft>),
          Draft,
          PrefetchHooks Function()
        > {
  $$DraftsTableTableManager(_$AppDatabase db, $DraftsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$DraftsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$DraftsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$DraftsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String> userId = const Value.absent(),
                Value<String> formId = const Value.absent(),
                Value<int> formVersion = const Value.absent(),
                Value<String> answersJson = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<DateTime> updatedAt = const Value.absent(),
                Value<String?> correctsServerId = const Value.absent(),
                Value<int?> baseRevision = const Value.absent(),
                Value<String?> correctsLocalId = const Value.absent(),
                Value<String?> reference = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => DraftsCompanion(
                id: id,
                userId: userId,
                formId: formId,
                formVersion: formVersion,
                answersJson: answersJson,
                createdAt: createdAt,
                updatedAt: updatedAt,
                correctsServerId: correctsServerId,
                baseRevision: baseRevision,
                correctsLocalId: correctsLocalId,
                reference: reference,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                required String userId,
                required String formId,
                required int formVersion,
                required String answersJson,
                required DateTime createdAt,
                required DateTime updatedAt,
                Value<String?> correctsServerId = const Value.absent(),
                Value<int?> baseRevision = const Value.absent(),
                Value<String?> correctsLocalId = const Value.absent(),
                Value<String?> reference = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => DraftsCompanion.insert(
                id: id,
                userId: userId,
                formId: formId,
                formVersion: formVersion,
                answersJson: answersJson,
                createdAt: createdAt,
                updatedAt: updatedAt,
                correctsServerId: correctsServerId,
                baseRevision: baseRevision,
                correctsLocalId: correctsLocalId,
                reference: reference,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$DraftsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $DraftsTable,
      Draft,
      $$DraftsTableFilterComposer,
      $$DraftsTableOrderingComposer,
      $$DraftsTableAnnotationComposer,
      $$DraftsTableCreateCompanionBuilder,
      $$DraftsTableUpdateCompanionBuilder,
      (Draft, BaseReferences<_$AppDatabase, $DraftsTable, Draft>),
      Draft,
      PrefetchHooks Function()
    >;
typedef $$LocalSubmissionsTableCreateCompanionBuilder =
    LocalSubmissionsCompanion Function({
      required String localId,
      required String userId,
      required String idempotencyKey,
      required String formId,
      required int formVersion,
      required String formTitle,
      required String answersJson,
      required DateTime submittedAtDevice,
      required int tzOffsetMin,
      Value<double?> subLatitude,
      Value<double?> subLongitude,
      Value<double?> subAccuracyM,
      Value<DateTime?> subFixAtDevice,
      required String subLocationStatus,
      required String state,
      Value<int> attempts,
      required DateTime nextAttemptAt,
      Value<String?> lastError,
      Value<String?> serverId,
      Value<DateTime?> receivedAtServer,
      Value<DateTime?> acceptedAtServer,
      required DateTime createdAt,
      Value<String?> reference,
      Value<int> revision,
      Value<bool> isLatest,
      Value<String?> correctsServerId,
      Value<int?> baseRevision,
      Value<String?> reviewStatus,
      Value<String?> reviewReason,
      Value<String?> reviewComment,
      Value<String?> reviewFlagsJson,
      Value<DateTime?> reviewedAt,
      Value<int> rowid,
    });
typedef $$LocalSubmissionsTableUpdateCompanionBuilder =
    LocalSubmissionsCompanion Function({
      Value<String> localId,
      Value<String> userId,
      Value<String> idempotencyKey,
      Value<String> formId,
      Value<int> formVersion,
      Value<String> formTitle,
      Value<String> answersJson,
      Value<DateTime> submittedAtDevice,
      Value<int> tzOffsetMin,
      Value<double?> subLatitude,
      Value<double?> subLongitude,
      Value<double?> subAccuracyM,
      Value<DateTime?> subFixAtDevice,
      Value<String> subLocationStatus,
      Value<String> state,
      Value<int> attempts,
      Value<DateTime> nextAttemptAt,
      Value<String?> lastError,
      Value<String?> serverId,
      Value<DateTime?> receivedAtServer,
      Value<DateTime?> acceptedAtServer,
      Value<DateTime> createdAt,
      Value<String?> reference,
      Value<int> revision,
      Value<bool> isLatest,
      Value<String?> correctsServerId,
      Value<int?> baseRevision,
      Value<String?> reviewStatus,
      Value<String?> reviewReason,
      Value<String?> reviewComment,
      Value<String?> reviewFlagsJson,
      Value<DateTime?> reviewedAt,
      Value<int> rowid,
    });

class $$LocalSubmissionsTableFilterComposer
    extends Composer<_$AppDatabase, $LocalSubmissionsTable> {
  $$LocalSubmissionsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get localId => $composableBuilder(
    column: $table.localId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get userId => $composableBuilder(
    column: $table.userId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get idempotencyKey => $composableBuilder(
    column: $table.idempotencyKey,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get formVersion => $composableBuilder(
    column: $table.formVersion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get formTitle => $composableBuilder(
    column: $table.formTitle,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get submittedAtDevice => $composableBuilder(
    column: $table.submittedAtDevice,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get tzOffsetMin => $composableBuilder(
    column: $table.tzOffsetMin,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get subLatitude => $composableBuilder(
    column: $table.subLatitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get subLongitude => $composableBuilder(
    column: $table.subLongitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get subAccuracyM => $composableBuilder(
    column: $table.subAccuracyM,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get subFixAtDevice => $composableBuilder(
    column: $table.subFixAtDevice,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get subLocationStatus => $composableBuilder(
    column: $table.subLocationStatus,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get state => $composableBuilder(
    column: $table.state,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get attempts => $composableBuilder(
    column: $table.attempts,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get nextAttemptAt => $composableBuilder(
    column: $table.nextAttemptAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get serverId => $composableBuilder(
    column: $table.serverId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get receivedAtServer => $composableBuilder(
    column: $table.receivedAtServer,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get acceptedAtServer => $composableBuilder(
    column: $table.acceptedAtServer,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get reference => $composableBuilder(
    column: $table.reference,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get revision => $composableBuilder(
    column: $table.revision,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get isLatest => $composableBuilder(
    column: $table.isLatest,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get correctsServerId => $composableBuilder(
    column: $table.correctsServerId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get baseRevision => $composableBuilder(
    column: $table.baseRevision,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get reviewStatus => $composableBuilder(
    column: $table.reviewStatus,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get reviewReason => $composableBuilder(
    column: $table.reviewReason,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get reviewComment => $composableBuilder(
    column: $table.reviewComment,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get reviewFlagsJson => $composableBuilder(
    column: $table.reviewFlagsJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get reviewedAt => $composableBuilder(
    column: $table.reviewedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LocalSubmissionsTableOrderingComposer
    extends Composer<_$AppDatabase, $LocalSubmissionsTable> {
  $$LocalSubmissionsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get localId => $composableBuilder(
    column: $table.localId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get userId => $composableBuilder(
    column: $table.userId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get idempotencyKey => $composableBuilder(
    column: $table.idempotencyKey,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get formId => $composableBuilder(
    column: $table.formId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get formVersion => $composableBuilder(
    column: $table.formVersion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get formTitle => $composableBuilder(
    column: $table.formTitle,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get submittedAtDevice => $composableBuilder(
    column: $table.submittedAtDevice,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get tzOffsetMin => $composableBuilder(
    column: $table.tzOffsetMin,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get subLatitude => $composableBuilder(
    column: $table.subLatitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get subLongitude => $composableBuilder(
    column: $table.subLongitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get subAccuracyM => $composableBuilder(
    column: $table.subAccuracyM,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get subFixAtDevice => $composableBuilder(
    column: $table.subFixAtDevice,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get subLocationStatus => $composableBuilder(
    column: $table.subLocationStatus,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get state => $composableBuilder(
    column: $table.state,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get attempts => $composableBuilder(
    column: $table.attempts,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get nextAttemptAt => $composableBuilder(
    column: $table.nextAttemptAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get lastError => $composableBuilder(
    column: $table.lastError,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get serverId => $composableBuilder(
    column: $table.serverId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get receivedAtServer => $composableBuilder(
    column: $table.receivedAtServer,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get acceptedAtServer => $composableBuilder(
    column: $table.acceptedAtServer,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get reference => $composableBuilder(
    column: $table.reference,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get revision => $composableBuilder(
    column: $table.revision,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get isLatest => $composableBuilder(
    column: $table.isLatest,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get correctsServerId => $composableBuilder(
    column: $table.correctsServerId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get baseRevision => $composableBuilder(
    column: $table.baseRevision,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get reviewStatus => $composableBuilder(
    column: $table.reviewStatus,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get reviewReason => $composableBuilder(
    column: $table.reviewReason,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get reviewComment => $composableBuilder(
    column: $table.reviewComment,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get reviewFlagsJson => $composableBuilder(
    column: $table.reviewFlagsJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get reviewedAt => $composableBuilder(
    column: $table.reviewedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LocalSubmissionsTableAnnotationComposer
    extends Composer<_$AppDatabase, $LocalSubmissionsTable> {
  $$LocalSubmissionsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get localId =>
      $composableBuilder(column: $table.localId, builder: (column) => column);

  GeneratedColumn<String> get userId =>
      $composableBuilder(column: $table.userId, builder: (column) => column);

  GeneratedColumn<String> get idempotencyKey => $composableBuilder(
    column: $table.idempotencyKey,
    builder: (column) => column,
  );

  GeneratedColumn<String> get formId =>
      $composableBuilder(column: $table.formId, builder: (column) => column);

  GeneratedColumn<int> get formVersion => $composableBuilder(
    column: $table.formVersion,
    builder: (column) => column,
  );

  GeneratedColumn<String> get formTitle =>
      $composableBuilder(column: $table.formTitle, builder: (column) => column);

  GeneratedColumn<String> get answersJson => $composableBuilder(
    column: $table.answersJson,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get submittedAtDevice => $composableBuilder(
    column: $table.submittedAtDevice,
    builder: (column) => column,
  );

  GeneratedColumn<int> get tzOffsetMin => $composableBuilder(
    column: $table.tzOffsetMin,
    builder: (column) => column,
  );

  GeneratedColumn<double> get subLatitude => $composableBuilder(
    column: $table.subLatitude,
    builder: (column) => column,
  );

  GeneratedColumn<double> get subLongitude => $composableBuilder(
    column: $table.subLongitude,
    builder: (column) => column,
  );

  GeneratedColumn<double> get subAccuracyM => $composableBuilder(
    column: $table.subAccuracyM,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get subFixAtDevice => $composableBuilder(
    column: $table.subFixAtDevice,
    builder: (column) => column,
  );

  GeneratedColumn<String> get subLocationStatus => $composableBuilder(
    column: $table.subLocationStatus,
    builder: (column) => column,
  );

  GeneratedColumn<String> get state =>
      $composableBuilder(column: $table.state, builder: (column) => column);

  GeneratedColumn<int> get attempts =>
      $composableBuilder(column: $table.attempts, builder: (column) => column);

  GeneratedColumn<DateTime> get nextAttemptAt => $composableBuilder(
    column: $table.nextAttemptAt,
    builder: (column) => column,
  );

  GeneratedColumn<String> get lastError =>
      $composableBuilder(column: $table.lastError, builder: (column) => column);

  GeneratedColumn<String> get serverId =>
      $composableBuilder(column: $table.serverId, builder: (column) => column);

  GeneratedColumn<DateTime> get receivedAtServer => $composableBuilder(
    column: $table.receivedAtServer,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get acceptedAtServer => $composableBuilder(
    column: $table.acceptedAtServer,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get reference =>
      $composableBuilder(column: $table.reference, builder: (column) => column);

  GeneratedColumn<int> get revision =>
      $composableBuilder(column: $table.revision, builder: (column) => column);

  GeneratedColumn<bool> get isLatest =>
      $composableBuilder(column: $table.isLatest, builder: (column) => column);

  GeneratedColumn<String> get correctsServerId => $composableBuilder(
    column: $table.correctsServerId,
    builder: (column) => column,
  );

  GeneratedColumn<int> get baseRevision => $composableBuilder(
    column: $table.baseRevision,
    builder: (column) => column,
  );

  GeneratedColumn<String> get reviewStatus => $composableBuilder(
    column: $table.reviewStatus,
    builder: (column) => column,
  );

  GeneratedColumn<String> get reviewReason => $composableBuilder(
    column: $table.reviewReason,
    builder: (column) => column,
  );

  GeneratedColumn<String> get reviewComment => $composableBuilder(
    column: $table.reviewComment,
    builder: (column) => column,
  );

  GeneratedColumn<String> get reviewFlagsJson => $composableBuilder(
    column: $table.reviewFlagsJson,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get reviewedAt => $composableBuilder(
    column: $table.reviewedAt,
    builder: (column) => column,
  );
}

class $$LocalSubmissionsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LocalSubmissionsTable,
          LocalSubmission,
          $$LocalSubmissionsTableFilterComposer,
          $$LocalSubmissionsTableOrderingComposer,
          $$LocalSubmissionsTableAnnotationComposer,
          $$LocalSubmissionsTableCreateCompanionBuilder,
          $$LocalSubmissionsTableUpdateCompanionBuilder,
          (
            LocalSubmission,
            BaseReferences<
              _$AppDatabase,
              $LocalSubmissionsTable,
              LocalSubmission
            >,
          ),
          LocalSubmission,
          PrefetchHooks Function()
        > {
  $$LocalSubmissionsTableTableManager(
    _$AppDatabase db,
    $LocalSubmissionsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LocalSubmissionsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LocalSubmissionsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LocalSubmissionsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> localId = const Value.absent(),
                Value<String> userId = const Value.absent(),
                Value<String> idempotencyKey = const Value.absent(),
                Value<String> formId = const Value.absent(),
                Value<int> formVersion = const Value.absent(),
                Value<String> formTitle = const Value.absent(),
                Value<String> answersJson = const Value.absent(),
                Value<DateTime> submittedAtDevice = const Value.absent(),
                Value<int> tzOffsetMin = const Value.absent(),
                Value<double?> subLatitude = const Value.absent(),
                Value<double?> subLongitude = const Value.absent(),
                Value<double?> subAccuracyM = const Value.absent(),
                Value<DateTime?> subFixAtDevice = const Value.absent(),
                Value<String> subLocationStatus = const Value.absent(),
                Value<String> state = const Value.absent(),
                Value<int> attempts = const Value.absent(),
                Value<DateTime> nextAttemptAt = const Value.absent(),
                Value<String?> lastError = const Value.absent(),
                Value<String?> serverId = const Value.absent(),
                Value<DateTime?> receivedAtServer = const Value.absent(),
                Value<DateTime?> acceptedAtServer = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<String?> reference = const Value.absent(),
                Value<int> revision = const Value.absent(),
                Value<bool> isLatest = const Value.absent(),
                Value<String?> correctsServerId = const Value.absent(),
                Value<int?> baseRevision = const Value.absent(),
                Value<String?> reviewStatus = const Value.absent(),
                Value<String?> reviewReason = const Value.absent(),
                Value<String?> reviewComment = const Value.absent(),
                Value<String?> reviewFlagsJson = const Value.absent(),
                Value<DateTime?> reviewedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LocalSubmissionsCompanion(
                localId: localId,
                userId: userId,
                idempotencyKey: idempotencyKey,
                formId: formId,
                formVersion: formVersion,
                formTitle: formTitle,
                answersJson: answersJson,
                submittedAtDevice: submittedAtDevice,
                tzOffsetMin: tzOffsetMin,
                subLatitude: subLatitude,
                subLongitude: subLongitude,
                subAccuracyM: subAccuracyM,
                subFixAtDevice: subFixAtDevice,
                subLocationStatus: subLocationStatus,
                state: state,
                attempts: attempts,
                nextAttemptAt: nextAttemptAt,
                lastError: lastError,
                serverId: serverId,
                receivedAtServer: receivedAtServer,
                acceptedAtServer: acceptedAtServer,
                createdAt: createdAt,
                reference: reference,
                revision: revision,
                isLatest: isLatest,
                correctsServerId: correctsServerId,
                baseRevision: baseRevision,
                reviewStatus: reviewStatus,
                reviewReason: reviewReason,
                reviewComment: reviewComment,
                reviewFlagsJson: reviewFlagsJson,
                reviewedAt: reviewedAt,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String localId,
                required String userId,
                required String idempotencyKey,
                required String formId,
                required int formVersion,
                required String formTitle,
                required String answersJson,
                required DateTime submittedAtDevice,
                required int tzOffsetMin,
                Value<double?> subLatitude = const Value.absent(),
                Value<double?> subLongitude = const Value.absent(),
                Value<double?> subAccuracyM = const Value.absent(),
                Value<DateTime?> subFixAtDevice = const Value.absent(),
                required String subLocationStatus,
                required String state,
                Value<int> attempts = const Value.absent(),
                required DateTime nextAttemptAt,
                Value<String?> lastError = const Value.absent(),
                Value<String?> serverId = const Value.absent(),
                Value<DateTime?> receivedAtServer = const Value.absent(),
                Value<DateTime?> acceptedAtServer = const Value.absent(),
                required DateTime createdAt,
                Value<String?> reference = const Value.absent(),
                Value<int> revision = const Value.absent(),
                Value<bool> isLatest = const Value.absent(),
                Value<String?> correctsServerId = const Value.absent(),
                Value<int?> baseRevision = const Value.absent(),
                Value<String?> reviewStatus = const Value.absent(),
                Value<String?> reviewReason = const Value.absent(),
                Value<String?> reviewComment = const Value.absent(),
                Value<String?> reviewFlagsJson = const Value.absent(),
                Value<DateTime?> reviewedAt = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LocalSubmissionsCompanion.insert(
                localId: localId,
                userId: userId,
                idempotencyKey: idempotencyKey,
                formId: formId,
                formVersion: formVersion,
                formTitle: formTitle,
                answersJson: answersJson,
                submittedAtDevice: submittedAtDevice,
                tzOffsetMin: tzOffsetMin,
                subLatitude: subLatitude,
                subLongitude: subLongitude,
                subAccuracyM: subAccuracyM,
                subFixAtDevice: subFixAtDevice,
                subLocationStatus: subLocationStatus,
                state: state,
                attempts: attempts,
                nextAttemptAt: nextAttemptAt,
                lastError: lastError,
                serverId: serverId,
                receivedAtServer: receivedAtServer,
                acceptedAtServer: acceptedAtServer,
                createdAt: createdAt,
                reference: reference,
                revision: revision,
                isLatest: isLatest,
                correctsServerId: correctsServerId,
                baseRevision: baseRevision,
                reviewStatus: reviewStatus,
                reviewReason: reviewReason,
                reviewComment: reviewComment,
                reviewFlagsJson: reviewFlagsJson,
                reviewedAt: reviewedAt,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LocalSubmissionsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LocalSubmissionsTable,
      LocalSubmission,
      $$LocalSubmissionsTableFilterComposer,
      $$LocalSubmissionsTableOrderingComposer,
      $$LocalSubmissionsTableAnnotationComposer,
      $$LocalSubmissionsTableCreateCompanionBuilder,
      $$LocalSubmissionsTableUpdateCompanionBuilder,
      (
        LocalSubmission,
        BaseReferences<_$AppDatabase, $LocalSubmissionsTable, LocalSubmission>,
      ),
      LocalSubmission,
      PrefetchHooks Function()
    >;
typedef $$LocalPhotosTableCreateCompanionBuilder =
    LocalPhotosCompanion Function({
      required String id,
      Value<String?> draftId,
      Value<String?> submissionLocalId,
      required String filePath,
      required String sha256,
      required int sizeBytes,
      required String mimeType,
      required DateTime capturedAtDevice,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<double?> accuracyM,
      Value<DateTime?> locationFixAtDevice,
      required String locationStatus,
      Value<String?> locationSource,
      Value<String> uploadState,
      Value<int> rowid,
    });
typedef $$LocalPhotosTableUpdateCompanionBuilder =
    LocalPhotosCompanion Function({
      Value<String> id,
      Value<String?> draftId,
      Value<String?> submissionLocalId,
      Value<String> filePath,
      Value<String> sha256,
      Value<int> sizeBytes,
      Value<String> mimeType,
      Value<DateTime> capturedAtDevice,
      Value<double?> latitude,
      Value<double?> longitude,
      Value<double?> accuracyM,
      Value<DateTime?> locationFixAtDevice,
      Value<String> locationStatus,
      Value<String?> locationSource,
      Value<String> uploadState,
      Value<int> rowid,
    });

class $$LocalPhotosTableFilterComposer
    extends Composer<_$AppDatabase, $LocalPhotosTable> {
  $$LocalPhotosTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get draftId => $composableBuilder(
    column: $table.draftId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get submissionLocalId => $composableBuilder(
    column: $table.submissionLocalId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get filePath => $composableBuilder(
    column: $table.filePath,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get sha256 => $composableBuilder(
    column: $table.sha256,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get sizeBytes => $composableBuilder(
    column: $table.sizeBytes,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get mimeType => $composableBuilder(
    column: $table.mimeType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get capturedAtDevice => $composableBuilder(
    column: $table.capturedAtDevice,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get accuracyM => $composableBuilder(
    column: $table.accuracyM,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get locationFixAtDevice => $composableBuilder(
    column: $table.locationFixAtDevice,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get locationStatus => $composableBuilder(
    column: $table.locationStatus,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get locationSource => $composableBuilder(
    column: $table.locationSource,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get uploadState => $composableBuilder(
    column: $table.uploadState,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LocalPhotosTableOrderingComposer
    extends Composer<_$AppDatabase, $LocalPhotosTable> {
  $$LocalPhotosTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get draftId => $composableBuilder(
    column: $table.draftId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get submissionLocalId => $composableBuilder(
    column: $table.submissionLocalId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get filePath => $composableBuilder(
    column: $table.filePath,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get sha256 => $composableBuilder(
    column: $table.sha256,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get sizeBytes => $composableBuilder(
    column: $table.sizeBytes,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get mimeType => $composableBuilder(
    column: $table.mimeType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get capturedAtDevice => $composableBuilder(
    column: $table.capturedAtDevice,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get latitude => $composableBuilder(
    column: $table.latitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get longitude => $composableBuilder(
    column: $table.longitude,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get accuracyM => $composableBuilder(
    column: $table.accuracyM,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get locationFixAtDevice => $composableBuilder(
    column: $table.locationFixAtDevice,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get locationStatus => $composableBuilder(
    column: $table.locationStatus,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get locationSource => $composableBuilder(
    column: $table.locationSource,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get uploadState => $composableBuilder(
    column: $table.uploadState,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LocalPhotosTableAnnotationComposer
    extends Composer<_$AppDatabase, $LocalPhotosTable> {
  $$LocalPhotosTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get draftId =>
      $composableBuilder(column: $table.draftId, builder: (column) => column);

  GeneratedColumn<String> get submissionLocalId => $composableBuilder(
    column: $table.submissionLocalId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get filePath =>
      $composableBuilder(column: $table.filePath, builder: (column) => column);

  GeneratedColumn<String> get sha256 =>
      $composableBuilder(column: $table.sha256, builder: (column) => column);

  GeneratedColumn<int> get sizeBytes =>
      $composableBuilder(column: $table.sizeBytes, builder: (column) => column);

  GeneratedColumn<String> get mimeType =>
      $composableBuilder(column: $table.mimeType, builder: (column) => column);

  GeneratedColumn<DateTime> get capturedAtDevice => $composableBuilder(
    column: $table.capturedAtDevice,
    builder: (column) => column,
  );

  GeneratedColumn<double> get latitude =>
      $composableBuilder(column: $table.latitude, builder: (column) => column);

  GeneratedColumn<double> get longitude =>
      $composableBuilder(column: $table.longitude, builder: (column) => column);

  GeneratedColumn<double> get accuracyM =>
      $composableBuilder(column: $table.accuracyM, builder: (column) => column);

  GeneratedColumn<DateTime> get locationFixAtDevice => $composableBuilder(
    column: $table.locationFixAtDevice,
    builder: (column) => column,
  );

  GeneratedColumn<String> get locationStatus => $composableBuilder(
    column: $table.locationStatus,
    builder: (column) => column,
  );

  GeneratedColumn<String> get locationSource => $composableBuilder(
    column: $table.locationSource,
    builder: (column) => column,
  );

  GeneratedColumn<String> get uploadState => $composableBuilder(
    column: $table.uploadState,
    builder: (column) => column,
  );
}

class $$LocalPhotosTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LocalPhotosTable,
          LocalPhoto,
          $$LocalPhotosTableFilterComposer,
          $$LocalPhotosTableOrderingComposer,
          $$LocalPhotosTableAnnotationComposer,
          $$LocalPhotosTableCreateCompanionBuilder,
          $$LocalPhotosTableUpdateCompanionBuilder,
          (
            LocalPhoto,
            BaseReferences<_$AppDatabase, $LocalPhotosTable, LocalPhoto>,
          ),
          LocalPhoto,
          PrefetchHooks Function()
        > {
  $$LocalPhotosTableTableManager(_$AppDatabase db, $LocalPhotosTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LocalPhotosTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LocalPhotosTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LocalPhotosTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> id = const Value.absent(),
                Value<String?> draftId = const Value.absent(),
                Value<String?> submissionLocalId = const Value.absent(),
                Value<String> filePath = const Value.absent(),
                Value<String> sha256 = const Value.absent(),
                Value<int> sizeBytes = const Value.absent(),
                Value<String> mimeType = const Value.absent(),
                Value<DateTime> capturedAtDevice = const Value.absent(),
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<double?> accuracyM = const Value.absent(),
                Value<DateTime?> locationFixAtDevice = const Value.absent(),
                Value<String> locationStatus = const Value.absent(),
                Value<String?> locationSource = const Value.absent(),
                Value<String> uploadState = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LocalPhotosCompanion(
                id: id,
                draftId: draftId,
                submissionLocalId: submissionLocalId,
                filePath: filePath,
                sha256: sha256,
                sizeBytes: sizeBytes,
                mimeType: mimeType,
                capturedAtDevice: capturedAtDevice,
                latitude: latitude,
                longitude: longitude,
                accuracyM: accuracyM,
                locationFixAtDevice: locationFixAtDevice,
                locationStatus: locationStatus,
                locationSource: locationSource,
                uploadState: uploadState,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String id,
                Value<String?> draftId = const Value.absent(),
                Value<String?> submissionLocalId = const Value.absent(),
                required String filePath,
                required String sha256,
                required int sizeBytes,
                required String mimeType,
                required DateTime capturedAtDevice,
                Value<double?> latitude = const Value.absent(),
                Value<double?> longitude = const Value.absent(),
                Value<double?> accuracyM = const Value.absent(),
                Value<DateTime?> locationFixAtDevice = const Value.absent(),
                required String locationStatus,
                Value<String?> locationSource = const Value.absent(),
                Value<String> uploadState = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => LocalPhotosCompanion.insert(
                id: id,
                draftId: draftId,
                submissionLocalId: submissionLocalId,
                filePath: filePath,
                sha256: sha256,
                sizeBytes: sizeBytes,
                mimeType: mimeType,
                capturedAtDevice: capturedAtDevice,
                latitude: latitude,
                longitude: longitude,
                accuracyM: accuracyM,
                locationFixAtDevice: locationFixAtDevice,
                locationStatus: locationStatus,
                locationSource: locationSource,
                uploadState: uploadState,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LocalPhotosTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LocalPhotosTable,
      LocalPhoto,
      $$LocalPhotosTableFilterComposer,
      $$LocalPhotosTableOrderingComposer,
      $$LocalPhotosTableAnnotationComposer,
      $$LocalPhotosTableCreateCompanionBuilder,
      $$LocalPhotosTableUpdateCompanionBuilder,
      (
        LocalPhoto,
        BaseReferences<_$AppDatabase, $LocalPhotosTable, LocalPhoto>,
      ),
      LocalPhoto,
      PrefetchHooks Function()
    >;
typedef $$KeyValuesTableCreateCompanionBuilder =
    KeyValuesCompanion Function({
      required String key,
      required String value,
      Value<int> rowid,
    });
typedef $$KeyValuesTableUpdateCompanionBuilder =
    KeyValuesCompanion Function({
      Value<String> key,
      Value<String> value,
      Value<int> rowid,
    });

class $$KeyValuesTableFilterComposer
    extends Composer<_$AppDatabase, $KeyValuesTable> {
  $$KeyValuesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnFilters(column),
  );
}

class $$KeyValuesTableOrderingComposer
    extends Composer<_$AppDatabase, $KeyValuesTable> {
  $$KeyValuesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$KeyValuesTableAnnotationComposer
    extends Composer<_$AppDatabase, $KeyValuesTable> {
  $$KeyValuesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get key =>
      $composableBuilder(column: $table.key, builder: (column) => column);

  GeneratedColumn<String> get value =>
      $composableBuilder(column: $table.value, builder: (column) => column);
}

class $$KeyValuesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $KeyValuesTable,
          KeyValue,
          $$KeyValuesTableFilterComposer,
          $$KeyValuesTableOrderingComposer,
          $$KeyValuesTableAnnotationComposer,
          $$KeyValuesTableCreateCompanionBuilder,
          $$KeyValuesTableUpdateCompanionBuilder,
          (KeyValue, BaseReferences<_$AppDatabase, $KeyValuesTable, KeyValue>),
          KeyValue,
          PrefetchHooks Function()
        > {
  $$KeyValuesTableTableManager(_$AppDatabase db, $KeyValuesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$KeyValuesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$KeyValuesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$KeyValuesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> key = const Value.absent(),
                Value<String> value = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => KeyValuesCompanion(key: key, value: value, rowid: rowid),
          createCompanionCallback:
              ({
                required String key,
                required String value,
                Value<int> rowid = const Value.absent(),
              }) => KeyValuesCompanion.insert(
                key: key,
                value: value,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$KeyValuesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $KeyValuesTable,
      KeyValue,
      $$KeyValuesTableFilterComposer,
      $$KeyValuesTableOrderingComposer,
      $$KeyValuesTableAnnotationComposer,
      $$KeyValuesTableCreateCompanionBuilder,
      $$KeyValuesTableUpdateCompanionBuilder,
      (KeyValue, BaseReferences<_$AppDatabase, $KeyValuesTable, KeyValue>),
      KeyValue,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$CachedFormsTableTableManager get cachedForms =>
      $$CachedFormsTableTableManager(_db, _db.cachedForms);
  $$DraftsTableTableManager get drafts =>
      $$DraftsTableTableManager(_db, _db.drafts);
  $$LocalSubmissionsTableTableManager get localSubmissions =>
      $$LocalSubmissionsTableTableManager(_db, _db.localSubmissions);
  $$LocalPhotosTableTableManager get localPhotos =>
      $$LocalPhotosTableTableManager(_db, _db.localPhotos);
  $$KeyValuesTableTableManager get keyValues =>
      $$KeyValuesTableTableManager(_db, _db.keyValues);
}

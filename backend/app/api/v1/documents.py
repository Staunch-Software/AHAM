from datetime import datetime, timezone
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user_any, require_perm
from app.api.v1.entries import get_scoped_entry
from app.core.config import get_settings
from app.core.db import get_session
from app.models.documents import EntryDocument
from app.models.org import User
from app.storage.base import get_storage, sign_document_url, verify_document_sig

router = APIRouter(tags=["documents"])


def _doc_dict(d: EntryDocument, uploader_name: str | None = None) -> dict:
    return {
        "id": str(d.id),
        "entry_id": str(d.entry_id),
        "category": d.category,
        "sub_type": d.sub_type,
        "file_name": d.file_name,
        "mime_type": d.mime_type,
        "size_bytes": d.size_bytes,
        "notes": d.notes,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "uploaded_by": str(d.uploaded_by),
        "uploaded_by_name": uploader_name,
        "url": sign_document_url(str(d.id)),
    }


@router.get("/entries/{entry_id}/documents")
async def list_documents(
    entry_id: uuid.UUID,
    user: User = Depends(require_perm("documents.view")),
    session: AsyncSession = Depends(get_session),
):
    """List all attached customer documents and certificates for this entry."""
    e = await get_scoped_entry(session, user, entry_id)
    q = (
        select(EntryDocument, User.full_name)
        .outerjoin(User, User.id == EntryDocument.uploaded_by)
        .where(EntryDocument.entry_id == e.id, EntryDocument.company_id == user.company_id)
        .order_by(EntryDocument.created_at.desc())
    )
    rows = (await session.execute(q)).all()
    return [_doc_dict(d, name) for d, name in rows]


@router.post("/entries/{entry_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    entry_id: uuid.UUID,
    file: UploadFile = File(...),
    category: str = Form("other"),
    sub_type: str | None = Form(None),
    notes: str | None = Form(None),
    user: User = Depends(require_perm("documents.manage")),
    session: AsyncSession = Depends(get_session),
):
    """Upload or scan a document (KYC, income proof, property doc) and attach to entry."""
    e = await get_scoped_entry(session, user, entry_id)

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")
    max_bytes = get_settings().max_upload_bytes
    if len(content) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {max_bytes // (1024 * 1024)}MB limit")

    doc_id = uuid.uuid4()
    filename = file.filename or f"doc_{doc_id}.jpg"
    clean_filename = "".join(c for c in filename if c.isalnum() or c in ".-_ ")
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry_ref = "".join(c for c in (e.entry_code or str(e.id)) if c.isalnum() or c in "-_")
    storage_key = f"entries/{entry_ref}/{today_str}/{doc_id}_{clean_filename}"

    store = get_storage()
    store.put(storage_key, content)

    mime = file.content_type or "application/octet-stream"
    doc = EntryDocument(
        id=doc_id,
        company_id=user.company_id,
        entry_id=e.id,
        uploaded_by=user.id,
        category=category.lower().strip(),
        sub_type=sub_type.strip() if sub_type else None,
        file_name=clean_filename,
        mime_type=mime,
        size_bytes=len(content),
        storage_key=storage_key,
        notes=notes.strip() if notes else None,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    return _doc_dict(doc, user.full_name)


@router.delete("/entries/{entry_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    entry_id: uuid.UUID,
    doc_id: uuid.UUID,
    user: User = Depends(require_perm("documents.manage")),
    session: AsyncSession = Depends(get_session),
):
    """Delete an attached document."""
    e = await get_scoped_entry(session, user, entry_id)
    doc = await session.get(EntryDocument, doc_id)
    if not doc or doc.entry_id != e.id or doc.company_id != user.company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    try:
        get_storage().delete(doc.storage_key)
    except Exception:
        pass  # best-effort storage cleanup

    await session.delete(doc)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/documents/{doc_id}/view")
async def view_document(
    doc_id: uuid.UUID,
    exp: int | None = Query(None),
    sig: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """View an attached document or certificate (inline display). Verified via signed token."""
    if exp is None or sig is None or not verify_document_sig(str(doc_id), exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid or expired document link")

    doc = await session.get(EntryDocument, doc_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    store = get_storage()
    if not store.exists(doc.storage_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file missing from storage")

    data = store.read(doc.storage_key)
    return Response(
        content=data,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.file_name}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: uuid.UUID,
    exp: int | None = Query(None),
    sig: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Download an attached document or certificate."""
    if exp is None or sig is None or not verify_document_sig(str(doc_id), exp, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid or expired document link")

    doc = await session.get(EntryDocument, doc_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    store = get_storage()
    if not store.exists(doc.storage_key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document file missing from storage")

    data = store.read(doc.storage_key)
    return Response(
        content=data,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.file_name}"',
            "Cache-Control": "private, max-age=60",
        },
    )

"""Tests for Document role permissions and access controls."""
import io
import pytest
from tests.conftest import as_
from tests.test_calling_flow import Flow, clock  # noqa: F401


@pytest.mark.asyncio
async def test_document_rbac_restrictions(client, tenant_a, clock):
    f = Flow(client, tenant_a)

    # Create an entry
    e = await f.entry("so1", day="2026-10-20")
    eid = e["id"]

    # 1. Branch Manager can upload a document
    file_bytes = b"%PDF-1.4 test document content"
    files = {"file": ("aadhaar.pdf", io.BytesIO(file_bytes), "application/pdf")}
    res_upload = await client.post(
        f"/api/v1/entries/{eid}/documents",
        headers=await f("bm1"),
        files=files,
        data={"category": "kyc", "sub_type": "Aadhaar Card", "notes": "Verified"},
    )
    assert res_upload.status_code == 201, res_upload.text
    doc = res_upload.json()
    doc_id = doc["id"]

    # 2. View/List allowed for Region Manager, Cluster Manager, Business Manager, Admin, BM, SO
    for key in ("rm1", "cm1", "bizm", "admin", "bm1", "so1"):
        res_list = await client.get(f"/api/v1/entries/{eid}/documents", headers=await f(key))
        assert res_list.status_code == 200, f"Role {key} failed to list documents: {res_list.text}"
        docs = res_list.json()
        assert len(docs) >= 1
        assert docs[0]["id"] == doc_id

    # 3. Upload/Manage is REFUSED for Region Manager, Cluster Manager, Business Manager, Admin (403 Forbidden)
    for key in ("rm1", "cm1", "bizm", "admin"):
        bad_files = {"file": ("test.pdf", io.BytesIO(b"data"), "application/pdf")}
        res_bad_upload = await client.post(
            f"/api/v1/entries/{eid}/documents",
            headers=await f(key),
            files=bad_files,
            data={"category": "other"},
        )
        assert res_bad_upload.status_code == 403, f"Key {key} should be forbidden from uploading documents"

        res_bad_delete = await client.delete(
            f"/api/v1/entries/{eid}/documents/{doc_id}",
            headers=await f(key),
        )
        assert res_bad_delete.status_code == 403, f"Key {key} should be forbidden from deleting documents"

    # 4. Branch Manager can delete the document
    res_delete = await client.delete(
        f"/api/v1/entries/{eid}/documents/{doc_id}",
        headers=await f("bm1"),
    )
    assert res_delete.status_code == 204

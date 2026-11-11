"""Excel copies of the tables on screen: the browser sends the rows it shows (CSV files are made in the browser)."""
import io
import re

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import current_user
from app.models import User

router = APIRouter(prefix="/exports", tags=["exports"])

Cell = str | int | float | bool | None


class TableIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    header: list[str] = Field(min_length=1, max_length=80)
    rows: list[list[Cell]] = Field(max_length=100_000)


@router.post("/xlsx")
async def table_to_xlsx(body: TableIn, user: User = Depends(current_user)):
    from openpyxl import Workbook  # noqa: PLC0415 - only needed here
    from openpyxl.styles import Font

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(re.sub(r"[\[\]:*?/\\]", " ", body.name)[:31])
    ws.freeze_panes = "A2"
    widths = [len(h) for h in body.header]
    for row in body.rows[:2000]:
        for i, v in enumerate(row[:len(widths)]):
            widths[i] = max(widths[i], len(str(v or "")))
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i) if i < 26 else "A" + chr(65 + i - 26)].width = min(max(w + 2, 8), 60)
    bold = Font(bold=True)
    ws.append([_cell(ws, h, bold) for h in body.header])
    for row in body.rows:
        # a value Excel would run as a formula is kept as text
        ws.append([f"'{v}" if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v for v in row])
    buf = io.BytesIO()
    wb.save(buf)
    name = re.sub(r"[^\w-]+", "_", body.name).strip("_") or "export"
    return StreamingResponse(iter([buf.getvalue()]), headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _cell(ws, value, font):
    from openpyxl.cell import WriteOnlyCell  # noqa: PLC0415

    c = WriteOnlyCell(ws, value=value)
    c.font = font
    return c

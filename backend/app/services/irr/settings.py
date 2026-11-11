"""IRR settings: product mapping (product name -> HL / NHL), reasonableness bands, financial-year start, decimals.

Defaults are the answers we assumed while the client's questions are open (docs/irr-module.md, "Assumptions to
confirm with Aham").
"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.tabular import norm_header

ProductClass = Literal["HL", "NHL"]
# Seeded mapping; the MIS adds every other product name of the register under IRR settings.
DEFAULT_PRODUCT_MAP: dict[str, ProductClass] = {"Home Loan": "HL", "LAP": "NHL", "Loan Against Property": "NHL"}


def product_key(name: str) -> str:
    """How a product name is matched: case, spaces and punctuation do not matter ("Home-Loan" = "home loan")."""
    return norm_header(name)[:100]


class Band(BaseModel):
    """Expected range of the weighted average IRR (%). Outside it the report shows a warning; it never blocks."""

    model_config = ConfigDict(extra="forbid")
    min: float = Field(ge=0, le=100)
    max: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _order(self):
        if self.min >= self.max:
            raise ValueError("The lowest rate of a band must be below its highest rate")
        return self


class IrrConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_map: dict[str, ProductClass] = Field(default_factory=lambda: dict(DEFAULT_PRODUCT_MAP))
    bands: dict[ProductClass, Band | None] = Field(default_factory=dict)
    fy_start_month: int = Field(4, ge=1, le=12)  # 4 = the financial year starts on 1 April
    decimals: int = Field(2, ge=0, le=4)  # shown on screen and in exports

    @model_validator(mode="after")
    def _check(self):
        clean: dict[str, ProductClass] = {}
        seen: dict[str, str] = {}
        for name, cls in self.product_map.items():
            name = " ".join(name.split())
            key = product_key(name)
            if not key:
                raise ValueError("A product name in the mapping is empty")
            if key in seen:
                raise ValueError(f"'{name}' and '{seen[key]}' are the same product name; keep one")
            seen[key] = name
            clean[name] = cls
        self.product_map = clean
        self.bands = {k: v for k, v in self.bands.items() if v is not None}
        return self

    def class_by_key(self) -> dict[str, ProductClass]:
        return {product_key(n): c for n, c in self.product_map.items()}

    def band(self, product_class: str) -> tuple[Decimal, Decimal] | None:
        b = self.bands.get(product_class)  # type: ignore[call-overload]
        return (Decimal(str(b.min)), Decimal(str(b.max))) if b else None

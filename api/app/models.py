from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Firm(Base):
    """A law firm that borrows."""

    __tablename__ = "firms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    state: Mapped[str] = mapped_column(String(2))

    facilities: Mapped[list["Facility"]] = relationship(back_populates="firm")
    cases: Mapped[list["Case"]] = relationship(back_populates="firm")


class Facility(Base):
    """A credit line extended to a firm."""

    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firms.id"))
    commitment_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    outstanding_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0")
    )
    min_coverage_ratio: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("1.50")
    )

    firm: Mapped["Firm"] = relationship(back_populates="facilities")


class Case(Base):
    """One case, which is one piece of collateral."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    firm_id: Mapped[int] = mapped_column(ForeignKey("firms.id"))
    case_type: Mapped[str] = mapped_column(String(30))  # mass_tort, class_action, pi
    stage: Mapped[str] = mapped_column(String(30))  # e.g. filed, discovery, settled
    filed_date: Mapped[date] = mapped_column(Date)
    projected_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    jurisdiction: Mapped[str] = mapped_column(String(50))

    firm: Mapped["Firm"] = relationship(back_populates="cases")

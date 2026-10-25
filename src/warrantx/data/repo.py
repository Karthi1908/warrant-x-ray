"""SQLAlchemy 2.0 async models and repository interface for Warrant X-Ray."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    delete,
    event,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# Set WAL mode and turn on foreign keys for SQLite connections
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


class Base(DeclarativeBase):
    """Base declarative class."""

    pass


class Snapshot(Base):
    """Append-only snapshot record of warrant market data."""

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    source_last_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    collector_source: Mapped[str] = mapped_column(
        String(32), default="direct_screener"
    )
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, default="")
    quality_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    rows: Mapped[list[WarrantRow]] = relationship(
        "WarrantRow", back_populates="snapshot", cascade="all, delete-orphan"
    )


class WarrantRow(Base):
    """Single warrant row within a market snapshot."""

    __tablename__ = "warrant_rows"

    snapshot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("snapshots.id", ondelete="CASCADE"), primary_key=True
    )
    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    issuer: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(10))  # "call" | "put"
    underlying_ticker: Mapped[str] = mapped_column(String(32), index=True)
    expiry_date: Mapped[str] = mapped_column(String(16))  # YYYY-MM-DD
    strike: Mapped[float] = mapped_column(Float)
    ratio_raw: Mapped[float] = mapped_column(Float)
    underlying_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    bid_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ask_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    traded_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    issuer_iv: Mapped[float | None] = mapped_column(Float, nullable=True)
    issuer_eg: Mapped[float | None] = mapped_column(Float, nullable=True)
    issuer_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    issuer_premium: Mapped[float | None] = mapped_column(Float, nullable=True)
    issuer_theta_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensitivity_ticks: Mapped[float | None] = mapped_column(Float, nullable=True)
    moneyness: Mapped[float | None] = mapped_column(Float, nullable=True)
    indicators: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    snapshot: Mapped[Snapshot] = relationship("Snapshot", back_populates="rows")


class Underlying(Base):
    """Underlying share / asset metadata."""

    __tablename__ = "underlyings"

    ticker: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(128), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class PriceHistory(Base):
    """Historical daily close price for an underlying ticker."""

    __tablename__ = "price_history"

    ticker: Mapped[str] = mapped_column(String(32), primary_key=True)
    day: Mapped[str] = mapped_column(String(16), primary_key=True)  # YYYY-MM-DD
    close: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="snapshot")


class Evidence(Base):
    """Evidence record produced during a chat turn."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String(32))  # e.g. E1, E2
    turn_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # snapshot|metrics|card|scenario|news|health
    source: Mapped[str] = mapped_column(String(64))
    as_of: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)


class LlmCall(Base):
    """Audit log for LLM invocations (no PII or raw IPs)."""

    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    turn_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str] = mapped_column(String(64))
    tier: Mapped[str] = mapped_column(String(32))
    purpose: Mapped[str] = mapped_column(String(64))
    in_tokens: Mapped[int] = mapped_column(Integer, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, default=0)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="ok")


class Budget(Base):
    """Daily service budget tracker."""

    __tablename__ = "budgets"

    day: Mapped[str] = mapped_column(String(16), primary_key=True)  # YYYY-MM-DD
    kind: Mapped[str] = mapped_column(String(32), primary_key=True)  # llm_usd | tavily_credits
    used: Mapped[float] = mapped_column(Float, default=0.0)


class UsageMetrics(Base):
    """Aggregated anonymous daily usage metrics."""

    __tablename__ = "usage_metrics"

    day: Mapped[str] = mapped_column(String(16), primary_key=True)  # YYYY-MM-DD
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_visitor_count: Mapped[int] = mapped_column(Integer, default=0)
    interactive_query_count: Mapped[int] = mapped_column(Integer, default=0)


class NewsCache(Base):
    """Short-lived 30-minute news cache."""

    __tablename__ = "news_cache"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)


class StoredNewsSet(Base):
    """Persisted news set for replay mode and outage resilience."""

    __tablename__ = "stored_news_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    window_days: Mapped[int] = mapped_column(Integer, default=7)
    snapshot_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("snapshots.id", ondelete="SET NULL"), nullable=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    items_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)


class Report(Base):
    """Cached deep risk report."""

    __tablename__ = "reports"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("snapshots.id", ondelete="CASCADE"), primary_key=True
    )
    holding_days: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON)


class AsyncRepository:
    """Async repository providing access to all persisted tables."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self.session_factory = async_sessionmaker(engine, expire_on_commit=False)
        self._initialized: bool = False

    async def _ensure_init(self) -> None:
        """Lazily ensure tables exist."""
        if not self._initialized:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

                def _migrate(connection: Any) -> None:
                    try:
                        cursor = connection.connection.cursor()
                        cursor.execute("PRAGMA table_info(snapshots)")
                        cols = [row[1] for row in cursor.fetchall()]
                        if "collector_source" not in cols and "id" in cols:
                            cursor.execute("ALTER TABLE snapshots ADD COLUMN collector_source VARCHAR(32) DEFAULT 'direct_screener'")
                        cursor.close()
                    except Exception:
                        pass

                await conn.run_sync(_migrate)
            self._initialized = True

    async def init_tables(self) -> None:
        """Create tables if they do not exist."""
        await self._ensure_init()

    # --- Snapshots and WarrantRows ---

    async def save_snapshot(
        self,
        snapshot_data: dict[str, Any],
        rows_data: list[dict[str, Any]],
    ) -> Snapshot:
        """Append a new market snapshot and its rows."""
        await self._ensure_init()
        raw_fetched = snapshot_data.get("fetched_at", datetime.now(timezone.utc))
        if isinstance(raw_fetched, str):
            try:
                fetched_at_dt = datetime.fromisoformat(raw_fetched.replace("Z", "+00:00"))
            except Exception:
                fetched_at_dt = datetime.now(timezone.utc)
        else:
            fetched_at_dt = raw_fetched

        raw_update = snapshot_data.get("source_last_update")
        if isinstance(raw_update, str):
            try:
                update_dt = datetime.fromisoformat(raw_update.replace("Z", "+00:00"))
            except Exception:
                update_dt = None
        else:
            update_dt = raw_update

        async with self.session_factory() as session:
            async with session.begin():
                snapshot = Snapshot(
                    fetched_at=fetched_at_dt,
                    source_last_update=update_dt,
                    row_count=len(rows_data),
                    collector_source=snapshot_data.get(
                        "collector_source", "direct_screener"
                    ),
                    ok=snapshot_data.get("ok", True),
                    note=snapshot_data.get("note", ""),
                    quality_json=snapshot_data.get("quality_json"),
                )
                session.add(snapshot)
                await session.flush()
                seen_codes: set[str] = set()
                for row_dict in rows_data:
                    code = str(row_dict["code"]).strip().upper()
                    if code in seen_codes:
                        continue
                    seen_codes.add(code)

                    row = WarrantRow(
                        snapshot_id=snapshot.id,
                        code=code,
                        issuer=row_dict["issuer"],
                        type=row_dict["type"],
                        underlying_ticker=row_dict["underlying_ticker"],
                        expiry_date=row_dict["expiry_date"],
                        strike=float(row_dict["strike"]),
                        ratio_raw=float(row_dict["ratio_raw"]),
                        underlying_bid=row_dict.get("underlying_bid"),
                        bid=row_dict.get("bid"),
                        ask=row_dict.get("ask"),
                        bid_volume=row_dict.get("bid_volume"),
                        ask_volume=row_dict.get("ask_volume"),
                        traded_volume=row_dict.get("traded_volume"),
                        last_price=row_dict.get("last_price"),
                        last_time=row_dict.get("last_time"),
                        issuer_iv=row_dict.get("issuer_iv"),
                        issuer_eg=row_dict.get("issuer_eg"),
                        issuer_delta=row_dict.get("issuer_delta"),
                        issuer_premium=row_dict.get("issuer_premium"),
                        issuer_theta_raw=row_dict.get("issuer_theta_raw"),
                        sensitivity_ticks=row_dict.get("sensitivity_ticks"),
                        moneyness=row_dict.get("moneyness"),
                        indicators=row_dict.get("indicators"),
                        valid=row_dict.get("valid", True),
                        raw_json=row_dict.get("raw_json"),
                    )
                    session.add(row)

                await session.commit()
                return snapshot

    async def get_latest_good_snapshot(self) -> Snapshot | None:
        """Get the most recent snapshot that has ok=True."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = select(Snapshot).where(Snapshot.ok == True).order_by(Snapshot.id.desc()).limit(1)  # noqa: E712
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def get_snapshot_by_id(self, snapshot_id: int) -> Snapshot | None:
        """Get snapshot by ID."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = select(Snapshot).where(Snapshot.id == snapshot_id)
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def list_snapshots(self, limit: int = 50) -> list[Snapshot]:
        """List stored snapshots ordered newest first."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = select(Snapshot).order_by(Snapshot.id.desc()).limit(limit)
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def get_warrant(self, code: str, snapshot_id: int | None = None) -> WarrantRow | None:
        """Get a warrant row by code for a snapshot (default: latest good snapshot)."""
        async with self.session_factory() as session:
            if snapshot_id is None:
                latest = await self.get_latest_good_snapshot()
                if not latest:
                    return None
                snapshot_id = latest.id

            stmt = select(WarrantRow).where(
                WarrantRow.snapshot_id == snapshot_id,
                WarrantRow.code == code,
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def list_warrants_for_underlying(
        self, ticker: str, snapshot_id: int | None = None, valid_only: bool = True
    ) -> list[WarrantRow]:
        """List all warrants for a given underlying ticker."""
        async with self.session_factory() as session:
            if snapshot_id is None:
                latest = await self.get_latest_good_snapshot()
                if not latest:
                    return []
                snapshot_id = latest.id

            stmt = select(WarrantRow).where(
                WarrantRow.snapshot_id == snapshot_id,
                WarrantRow.underlying_ticker == ticker,
            )
            if valid_only:
                stmt = stmt.where(WarrantRow.valid == True)  # noqa: E712
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def list_all_warrants(
        self, snapshot_id: int | None = None, valid_only: bool = True
    ) -> list[WarrantRow]:
        """List all warrants in a snapshot."""
        async with self.session_factory() as session:
            if snapshot_id is None:
                latest = await self.get_latest_good_snapshot()
                if not latest:
                    return []
                snapshot_id = latest.id

            stmt = select(WarrantRow).where(WarrantRow.snapshot_id == snapshot_id)
            if valid_only:
                stmt = stmt.where(WarrantRow.valid == True)  # noqa: E712
            res = await session.execute(stmt)
            return list(res.scalars().all())

    # --- Underlyings ---

    async def upsert_underlying(self, ticker: str, code: str, name: str) -> Underlying:
        """Insert or update an underlying asset."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(Underlying).where(Underlying.ticker == ticker)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj is None:
                    obj = Underlying(
                        ticker=ticker,
                        code=code,
                        name=name,
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(obj)
                else:
                    obj.code = code
                    obj.name = name
                    obj.updated_at = datetime.now(timezone.utc)
                await session.commit()
                return obj

    async def get_underlying(self, ticker: str) -> Underlying | None:
        """Retrieve underlying metadata by ticker."""
        async with self.session_factory() as session:
            stmt = select(Underlying).where(Underlying.ticker == ticker)
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def list_underlyings(self) -> list[Underlying]:
        """List all recorded underlying assets."""
        async with self.session_factory() as session:
            stmt = select(Underlying).order_by(Underlying.ticker.asc())
            res = await session.execute(stmt)
            return list(res.scalars().all())

    # --- Price History ---

    async def save_price_history(
        self, ticker: str, day: str, close: float, source: str = "snapshot"
    ) -> None:
        """Record or update a close price."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(PriceHistory).where(
                    PriceHistory.ticker == ticker,
                    PriceHistory.day == day,
                )
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()
                if existing:
                    existing.close = close
                    existing.source = source
                else:
                    session.add(PriceHistory(ticker=ticker, day=day, close=close, source=source))
                await session.commit()

    async def get_recent_closes(self, ticker: str, limit: int = 35) -> list[float]:
        """Return the most recent close prices ordered oldest to newest."""
        async with self.session_factory() as session:
            stmt = (
                select(PriceHistory.close)
                .where(PriceHistory.ticker == ticker)
                .order_by(PriceHistory.day.desc())
                .limit(limit)
            )
            res = await session.execute(stmt)
            rows = list(res.scalars().all())
            return list(reversed(rows))

    # --- Evidence ---

    async def save_evidence(
        self,
        turn_id: str,
        evidence_id: str,
        kind: str,
        source: str,
        payload_json: dict[str, Any],
        as_of: datetime | None = None,
    ) -> Evidence:
        """Persist an evidence entry."""
        async with self.session_factory() as session:
            async with session.begin():
                record = Evidence(
                    turn_id=turn_id,
                    evidence_id=evidence_id,
                    kind=kind,
                    source=source,
                    as_of=as_of or datetime.now(timezone.utc),
                    payload_json=payload_json,
                )
                session.add(record)
                await session.commit()
                return record

    async def get_turn_evidence(self, turn_id: str) -> list[Evidence]:
        """Get all evidence records associated with a chat turn."""
        async with self.session_factory() as session:
            stmt = select(Evidence).where(Evidence.turn_id == turn_id).order_by(Evidence.id.asc())
            res = await session.execute(stmt)
            return list(res.scalars().all())

    # --- LLM Call Audit ---

    async def log_llm_call(
        self,
        model: str,
        tier: str,
        purpose: str,
        in_tokens: int = 0,
        out_tokens: int = 0,
        reasoning_tokens: int = 0,
        latency_ms: int = 0,
        cost_usd: float = 0.0,
        status: str = "ok",
        turn_id: str | None = None,
        session_hash: str | None = None,
    ) -> LlmCall:
        """Log LLM invocation metadata for cost and audit."""
        async with self.session_factory() as session:
            async with session.begin():
                record = LlmCall(
                    ts=datetime.now(timezone.utc),
                    turn_id=turn_id,
                    session_hash=session_hash,
                    model=model,
                    tier=tier,
                    purpose=purpose,
                    in_tokens=in_tokens,
                    out_tokens=out_tokens,
                    reasoning_tokens=reasoning_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost_usd,
                    status=status,
                )
                session.add(record)
                await session.commit()
                return record

    async def list_llm_calls(self, limit: int = 1000) -> list[LlmCall]:
        """List recent LLM call audit records."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = select(LlmCall).order_by(LlmCall.id.desc()).limit(limit)
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def get_cost_report_data(self, days: int = 30) -> dict[str, Any]:
        """Aggregate LLM cost metrics by day, tier, and purpose."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = select(LlmCall).order_by(LlmCall.ts.asc())
            res = await session.execute(stmt)
            calls = list(res.scalars().all())

        by_day: dict[str, dict[str, Any]] = {}
        by_tier: dict[str, dict[str, Any]] = {}
        by_purpose: dict[str, dict[str, Any]] = {}
        total_calls = len(calls)
        total_cost_usd = 0.0
        total_in_tokens = 0
        total_out_tokens = 0

        for c in calls:
            day_str = c.ts.strftime("%Y-%m-%d") if c.ts else "unknown"
            cost = float(c.cost_usd or 0.0)
            in_t = int(c.in_tokens or 0)
            out_t = int(c.out_tokens or 0)
            lat = int(c.latency_ms or 0)

            total_cost_usd += cost
            total_in_tokens += in_t
            total_out_tokens += out_t

            if day_str not in by_day:
                by_day[day_str] = {
                    "calls": 0,
                    "in_tokens": 0,
                    "out_tokens": 0,
                    "cost_usd": 0.0,
                    "latencies": [],
                }
            by_day[day_str]["calls"] += 1
            by_day[day_str]["in_tokens"] += in_t
            by_day[day_str]["out_tokens"] += out_t
            by_day[day_str]["cost_usd"] += cost
            by_day[day_str]["latencies"].append(lat)

            tier = c.tier or "unknown"
            if tier not in by_tier:
                by_tier[tier] = {
                    "calls": 0,
                    "in_tokens": 0,
                    "out_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_tier[tier]["calls"] += 1
            by_tier[tier]["in_tokens"] += in_t
            by_tier[tier]["out_tokens"] += out_t
            by_tier[tier]["cost_usd"] += cost

            purpose = c.purpose or "unknown"
            if purpose not in by_purpose:
                by_purpose[purpose] = {
                    "calls": 0,
                    "cost_usd": 0.0,
                }
            by_purpose[purpose]["calls"] += 1
            by_purpose[purpose]["cost_usd"] += cost

        formatted_days = []
        for d, data in sorted(by_day.items()):
            avg_lat = sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else 0
            formatted_days.append({
                "day": d,
                "calls": data["calls"],
                "in_tokens": data["in_tokens"],
                "out_tokens": data["out_tokens"],
                "avg_latency_ms": round(avg_lat, 1),
                "cost_usd": round(data["cost_usd"], 6),
            })

        formatted_tiers = [
            {
                "tier": t,
                "calls": data["calls"],
                "in_tokens": data["in_tokens"],
                "out_tokens": data["out_tokens"],
                "cost_usd": round(data["cost_usd"], 6),
            }
            for t, data in sorted(by_tier.items())
        ]

        formatted_purposes = [
            {
                "purpose": p,
                "calls": data["calls"],
                "cost_usd": round(data["cost_usd"], 6),
            }
            for p, data in sorted(by_purpose.items())
        ]

        return {
            "total_calls": total_calls,
            "total_cost_usd": round(total_cost_usd, 6),
            "total_in_tokens": total_in_tokens,
            "total_out_tokens": total_out_tokens,
            "by_day": formatted_days,
            "by_tier": formatted_tiers,
            "by_purpose": formatted_purposes,
        }

    # --- Daily Budget ---

    async def get_budget_usage(self, day: str, kind: str) -> float:
        """Retrieve total consumed budget for a given day and kind."""
        async with self.session_factory() as session:
            stmt = select(Budget.used).where(Budget.day == day, Budget.kind == kind)
            res = await session.execute(stmt)
            val = res.scalar_one_or_none()
            return float(val) if val is not None else 0.0

    async def increment_budget(self, day: str, kind: str, amount: float) -> float:
        """Atomically increment daily budget usage and return the new total."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(Budget).where(Budget.day == day, Budget.kind == kind)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj is None:
                    obj = Budget(day=day, kind=kind, used=amount)
                    session.add(obj)
                else:
                    obj.used += amount
                await session.commit()
                return obj.used

    async def record_budget_spend(
        self, day: str, kind: str, amount: float
    ) -> float:
        """Alias for increment_budget."""
        return await self.increment_budget(day=day, kind=kind, amount=amount)

    async def reset_budget(self, day: str, kind: str = "llm_usd") -> None:
        """Reset budget counter for a given day."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(Budget).where(Budget.day == day, Budget.kind == kind)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj is not None:
                    obj.used = 0.0
                await session.commit()

    # --- Anonymous Usage Metrics ---

    async def record_visit(
        self, session_or_day: str = "", is_new_unique: bool = False
    ) -> UsageMetrics:
        """Increment daily visit counter (and unique counter if new daily hash)."""
        await self._ensure_init()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day = (
            session_or_day
            if len(session_or_day) == 10 and session_or_day.count("-") == 2
            else today
        )

        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(UsageMetrics).where(UsageMetrics.day == day)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj is None:
                    obj = UsageMetrics(
                        day=day,
                        visit_count=1,
                        unique_visitor_count=1 if is_new_unique else 0,
                        interactive_query_count=0,
                    )
                    session.add(obj)
                else:
                    obj.visit_count += 1
                    if is_new_unique:
                        obj.unique_visitor_count += 1
                await session.commit()
                return obj

    async def record_daily_unique(
        self, subnet_or_hash: str = "", ua: str = "", day: str | None = None
    ) -> UsageMetrics:
        """Increment unique daily visitor counter."""
        await self._ensure_init()
        if not day or len(day) != 10:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(UsageMetrics).where(UsageMetrics.day == day)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj is None:
                    obj = UsageMetrics(
                        day=day,
                        visit_count=1,
                        unique_visitor_count=1,
                        interactive_query_count=0,
                    )
                    session.add(obj)
                else:
                    obj.unique_visitor_count += 1
                await session.commit()
                return obj

    async def record_interactive_query(self, day: str | None = None) -> UsageMetrics:
        """Increment interactive query count (sum of chat turns, scenarios, explain-move)."""
        await self._ensure_init()
        if not day or len(day) != 10:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(UsageMetrics).where(UsageMetrics.day == day)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj is None:
                    obj = UsageMetrics(
                        day=day,
                        visit_count=0,
                        unique_visitor_count=0,
                        interactive_query_count=1,
                    )
                    session.add(obj)
                else:
                    obj.interactive_query_count += 1
                await session.commit()
                return obj

    async def get_usage_metrics(self, day: str | None = None) -> UsageMetrics | None:
        """Retrieve usage metrics for a given day (defaults to today)."""
        await self._ensure_init()
        if not day or len(day) != 10:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        async with self.session_factory() as session:
            stmt = select(UsageMetrics).where(UsageMetrics.day == day)
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def list_usage_metrics(self, days: int = 30) -> list[UsageMetrics]:
        """Retrieve usage metrics for the last N days ordered by day desc."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = select(UsageMetrics).order_by(UsageMetrics.day.desc()).limit(days)
            res = await session.execute(stmt)
            return list(res.scalars().all())

    async def load_synthetic_sample_database(self) -> Snapshot:
        """Load synthetic sample market data into the repository (T081)."""
        await self._ensure_init()
        try:
            from scripts.make_fixtures import generate_synthetic_fixture
            fixture = generate_synthetic_fixture()
        except ImportError:
            import json
            import sys
            from pathlib import Path
            p = Path("tests/fixtures/synthetic_snapshot.json")
            if p.exists():
                fixture = json.loads(p.read_text(encoding="utf-8"))
            else:
                sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
                from scripts.make_fixtures import generate_synthetic_fixture
                fixture = generate_synthetic_fixture()
        snap_meta = {
            "fetched_at": fixture["fetched_at"],
            "source_last_update": fixture["source_last_update"],
            "ok": True,
            "note": "Complete synthetic test fixture for offline / sample mode",
            "quality_json": fixture.get("quality_json", {}),
        }

        snapshot = await self.save_snapshot(snap_meta, fixture["rows"])

        for und in fixture.get("underlyings", []):
            await self.upsert_underlying(
                ticker=und["ticker"],
                code=und.get("code", ""),
                name=und.get("name", und["ticker"]),
            )

        return snapshot

    # --- News Cache & Stored News Sets ---

    async def get_news_cache(self, key: str, max_age_seconds: int = 1800) -> dict[str, Any] | None:
        """Retrieve cached news payload if within max_age_seconds."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = select(NewsCache).where(NewsCache.key == key)
            res = await session.execute(stmt)
            entry = res.scalar_one_or_none()
            if not entry:
                return None
            age = (
                datetime.now(timezone.utc) - entry.created_at.replace(tzinfo=timezone.utc)
            ).total_seconds()
            if age > max_age_seconds:
                return None
            return entry.payload_json

    async def set_news_cache(self, key: str, payload: dict[str, Any]) -> None:
        """Set short-term news cache."""
        await self._ensure_init()
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(NewsCache).where(NewsCache.key == key)
                res = await session.execute(stmt)
                entry = res.scalar_one_or_none()
                if entry:
                    entry.created_at = datetime.now(timezone.utc)
                    entry.payload_json = payload
                else:
                    session.add(
                        NewsCache(
                            key=key,
                            created_at=datetime.now(timezone.utc),
                            payload_json=payload,
                        )
                    )
                await session.commit()

    async def clear_news_cache(self) -> int:
        """Clear all temporary entries from news_cache."""
        await self._ensure_init()
        async with self.session_factory() as session:
            async with session.begin():
                stmt = delete(NewsCache)
                res = await session.execute(stmt)
                await session.commit()
                return int(res.rowcount or 0)

    async def save_stored_news_set(
        self,
        ticker: str,
        items: list[dict[str, Any]],
        snapshot_id: int | None = None,
        window_days: int = 7,
    ) -> StoredNewsSet:
        """Save a 7-day news set for persistent replay mode."""
        await self._ensure_init()
        async with self.session_factory() as session:
            async with session.begin():
                record = StoredNewsSet(
                    ticker=ticker,
                    window_days=window_days,
                    snapshot_id=snapshot_id,
                    retrieved_at=datetime.now(timezone.utc),
                    items_json=items,
                )
                session.add(record)
                await session.commit()
                return record

    async def get_stored_news_set(self, ticker: str) -> StoredNewsSet | None:
        """Get the latest stored news set for an underlying ticker."""
        await self._ensure_init()
        async with self.session_factory() as session:
            stmt = (
                select(StoredNewsSet)
                .where(StoredNewsSet.ticker == ticker)
                .order_by(StoredNewsSet.id.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    # --- Reports ---

    async def get_report(
        self, code: str, snapshot_id: int, holding_days: int
    ) -> dict[str, Any] | None:
        """Get cached risk report for (code, snapshot_id, holding_days)."""
        async with self.session_factory() as session:
            stmt = select(Report).where(
                Report.code == code,
                Report.snapshot_id == snapshot_id,
                Report.holding_days == holding_days,
            )
            res = await session.execute(stmt)
            obj = res.scalar_one_or_none()
            return obj.report_json if obj else None

    async def save_report(
        self, code: str, snapshot_id: int, holding_days: int, report: dict[str, Any]
    ) -> Report:
        """Cache a generated risk report."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = select(Report).where(
                    Report.code == code,
                    Report.snapshot_id == snapshot_id,
                    Report.holding_days == holding_days,
                )
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj:
                    obj.report_json = report
                    obj.created_at = datetime.now(timezone.utc)
                else:
                    obj = Report(
                        code=code,
                        snapshot_id=snapshot_id,
                        holding_days=holding_days,
                        created_at=datetime.now(timezone.utc),
                        report_json=report,
                    )
                    session.add(obj)
                await session.commit()
                return obj


def create_repo(db_path_or_url: str | Path = "data/warrantx.db") -> AsyncRepository:
    """Factory creating an AsyncRepository connected to a SQLite database."""
    url = str(db_path_or_url)
    if ":///" in url and ":memory:" not in url:
        path_str = url.split(":///", 1)[1]
        if path_str:
            Path(path_str).parent.mkdir(parents=True, exist_ok=True)
    elif not url.startswith("sqlite"):
        if ":memory:" not in url:
            Path(url).parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite+aiosqlite:///{url}"
    engine = create_async_engine(url, echo=False)
    return AsyncRepository(engine)

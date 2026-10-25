import asyncio
from warrantx.data.repo import create_repo

async def main():
    repo = create_repo("data/warrantx.db")
    await repo.init_tables()
    snapshot = await repo.load_synthetic_sample_database()
    print(f"Loaded snapshot id={snapshot.id} with {snapshot.row_count} rows.")
    
    underlyings = await repo.list_underlyings()
    print(f"Total underlyings in DB: {len(underlyings)}")

if __name__ == "__main__":
    asyncio.run(main())

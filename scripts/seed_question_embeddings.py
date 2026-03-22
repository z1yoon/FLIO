"""
Seed question text embeddings into the questions table.

Run once after applying migration 011_question_embeddings.sql.
Re-run only when question texts change (very rare).

Usage:
    cd /path/to/FLIO
    python scripts/seed_question_embeddings.py
"""

import asyncio
import os
import sys

from openai import AsyncAzureOpenAI
from supabase import create_client, Client


AZURE_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_EMBEDDING_MODEL = os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

EMBEDDING_DIMENSIONS = 1024


async def embed(client: AsyncAzureOpenAI, text: str) -> list[float]:
    response = await client.embeddings.create(
        model=AZURE_EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


async def main() -> None:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    azure = AsyncAzureOpenAI(
        azure_endpoint=AZURE_ENDPOINT,
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
    )

    result = supabase.table("questions").select("id, text_ko, text_embedding").execute()
    rows = result.data or []

    skip = [r for r in rows if r.get("text_embedding")]
    todo = [r for r in rows if not r.get("text_embedding")]

    print(f"Total questions: {len(rows)}")
    print(f"Already embedded: {len(skip)} — skipping")
    print(f"To embed: {len(todo)}")

    if not todo:
        print("Nothing to do.")
        return

    for i, row in enumerate(todo, 1):
        qid = row["id"]
        text = row["text_ko"]
        print(f"  [{i}/{len(todo)}] {qid}: {text[:50]}...", end=" ", flush=True)

        embedding = await embed(azure, text)

        supabase.table("questions").update(
            {"text_embedding": embedding}
        ).eq("id", qid).execute()

        print("done")

    print(f"\nSeeded {len(todo)} question embeddings.")


if __name__ == "__main__":
    missing = [
        v for v in [
            "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY",
            "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
        ]
        if not os.environ.get(v)
    ]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(main())

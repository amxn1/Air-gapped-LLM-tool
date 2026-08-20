"""
Integration tests for the complete ingestion, vector storage, and RAG retrieval pipeline.
"""
import asyncio
import tempfile
from pathlib import Path
from apps.api.database import SessionLocal
from services.ingestion.worker import IngestionWorker
from services.retrieval.service import RetrievalService
from services.retrieval.vector_store import VectorStore
from apps.api.services.llama_service import LlamaService


def test_end_to_end_rag_pipeline():
    async def _test():
        db = SessionLocal()
        sample_doc_content = (
            "# Air-Gap Policy\n\n"
            "All model artifacts and software updates must undergo SHA-256 validation prior to importation. "
            "Runtime telemetry and public network egress are strictly prohibited under system security standards."
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(sample_doc_content)
            temp_file_path = f.name

        try:
            vector_store = VectorStore()
            
            # 1. Ingest document
            worker = IngestionWorker(db_session=db, vector_store=vector_store)
            result = await worker.process_file_async(
                file_path=temp_file_path,
                user_id=1
            )
            assert result["success"] is True
            assert result["chunks_created"] > 0

            # 2. Retrieve relevant evidence
            retrieval_svc = RetrievalService(db_session=db, vector_store=vector_store)
            chunks = await retrieval_svc.retrieve_relevant_chunks(
                query="What is the policy on runtime telemetry and air-gap imports?",
                limit=3
            )
            assert len(chunks) > 0
            assert any("telemetry" in c["text"].lower() or "air-gap" in c["text"].lower() for c in chunks)

            # 3. Verify LlamaService RAG prompt building
            llama_svc = LlamaService()
            rag_prompt = llama_svc.prompt_manager.build_rag_prompt(
                query="What is prohibited?",
                chunks=chunks
            )
            assert "<retrieved_context>" in rag_prompt["user_prompt"]

            await retrieval_svc.close()
            await llama_svc.close()
        finally:
            db.close()
            Path(temp_file_path).unlink()

    asyncio.run(_test())

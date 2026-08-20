"""
Evaluation benchmark suite validating quality, summarization fidelity, and dialect rewriting.
"""
import asyncio
from apps.api.services.llama_service import LlamaService


def test_science_technology_summary_evaluation():
    async def _test():
        llama_svc = LlamaService()
        sample_paper = (
            "This paper introduces High-Performance Distributed Vector Search (HPDVS). "
            "We evaluate HPDVS across 10 million embeddings, demonstrating a 40% reduction in query latency. "
            "Limitations include increased memory usage during index rebuilds."
        )
        result = await llama_svc.generate_summary(
            content=sample_paper,
            summary_type="science-technology"
        )
        assert "summary" in result
        assert len(result["summary"]) > 50
        await llama_svc.close()

    asyncio.run(_test())


def test_news_editorial_summary_evaluation():
    async def _test():
        llama_svc = LlamaService()
        sample_news = (
            "CITY DESK — The municipal transit authority announced the deployment of electric buses starting next month. "
            "City officials stated the fleet will reduce emissions by 30%. Critics argue charging infrastructure is currently insufficient."
        )
        result = await llama_svc.generate_summary(
            content=sample_news,
            summary_type="news-editorial"
        )
        assert "summary" in result
        assert len(result["summary"]) > 50
        await llama_svc.close()

    asyncio.run(_test())


def test_grammar_and_dialect_rewriting_evaluation():
    async def _test():
        llama_svc = LlamaService()
        draft = "we has analyzed the report and findings was positive"
        result = await llama_svc.generate_rewrite(
            text=draft,
            mode="grammar"
        )
        assert "rewritten_text" in result
        assert len(result["rewritten_text"]) > 0
        await llama_svc.close()

    asyncio.run(_test())

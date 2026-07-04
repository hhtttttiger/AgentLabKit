from retrieval.model import GraphExtractorConfig
from retrieval.engines.local_engine.graph.extractors.base import BaseGraphExtractor
from retrieval.engines.local_engine.graph.extractors.hybrid import HybridGraphExtractor
from retrieval.engines.local_engine.graph.extractors.llm import LlmGraphExtractor
from retrieval.engines.local_engine.graph.extractors.rule_based import RuleGraphExtractor


def create_graph_extractor(config: GraphExtractorConfig) -> BaseGraphExtractor:
    mode = config.mode.lower()
    if mode == "rule":
        return RuleGraphExtractor(
            max_triplets_per_segment=config.max_triplets_per_segment,
            confidence=max(config.confidence_threshold, 0.7),
        )
    if mode == "llm":
        return LlmGraphExtractor()

    return HybridGraphExtractor(
        enable_llm_enrichment=config.enable_llm_enrichment,
        max_triplets_per_segment=config.max_triplets_per_segment,
    )

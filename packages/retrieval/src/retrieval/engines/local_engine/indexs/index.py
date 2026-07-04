from dataclasses import dataclass
from functools import partial
from typing import Callable, List, Optional
from retrieval import model
from retrieval.engines.local_engine.stopWordHandler import stop_word_handler

@dataclass
class IndexStrategyConfig:
    is_md: bool = False

IndexStrategyFunc = Callable[[List[model.Segment], IndexStrategyConfig], List[model.Index]]

def index_factory(index_name: str, mode: str = '', is_md: bool = False) -> Optional[IndexStrategyFunc]:
    config = IndexStrategyConfig(is_md=is_md)

    if mode != '' and index_name.lower() == 'embedding':
        index_name = index_name + '_' + mode

    switcher = {
        'embedding': default_index,
        'embedding_default': default_index,
        'embedding_semantic': default_index,
        'embedding_refine': default_index,
        'full_text': full_text_index,
    }

    strategy = switcher.get(index_name.lower())
    if strategy is None:
        return None

    return partial(strategy, config=config)

def default_index(doc_segment: List[model.Segment], config: IndexStrategyConfig) -> List[model.Index]:
    """embedding 索引策略：将 segment 文本准备为 embedding 输入"""
    index_list: List[model.Index] = []
    for item in doc_segment:
        index_list.append(
            model.Index(
                segment_id=item.id,
                type='embedding',
                index=item.text,
                context=item.text,
                metadata={
                    "embedding_input": item.text,
                    "detected_script": item.detected_script or "",
                },
            )
        )

    return index_list

def full_text_index(doc_segment: List[model.Segment], config: IndexStrategyConfig) -> List[model.Index]:
    """全文索引策略：使用分词结果和关键词构建索引"""
    index_list: List[model.Index] = []

    for i, item in enumerate(doc_segment):
        content = item.word_segmentation if item.word_segmentation else item.text
        index_list.append(
            model.Index(
                segment_id=item.id,
                type='full_text',
                index=content,
                context=item.text,
                metadata={
                    "keywords": list(item.keywords or []),
                    "detected_script": item.detected_script or "",
                },
            )
        )

    return index_list

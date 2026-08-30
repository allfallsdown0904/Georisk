import math

from app.rag.embeddings import HashEmbedder, cosine_similarity


def test_hash_embedder_deterministic_and_dimension():
    embedder = HashEmbedder(dim=1024)
    v1 = embedder.embed("哈萨克斯坦汇率风险与制裁合规")
    v2 = embedder.embed("哈萨克斯坦汇率风险与制裁合规")
    assert v1 == v2
    assert len(v1) == 1024
    norm = math.sqrt(sum(x * x for x in v1))
    assert abs(norm - 1.0) < 1e-6


def test_hash_embedder_chinese_similarity():
    embedder = HashEmbedder()
    a = embedder.embed("塞尔维亚大规模抗议与政治不稳定")
    b = embedder.embed("塞尔维亚持续反政府抗议政局动荡")
    c = embedder.embed("尼日利亚奈拉汇率与外汇改革")
    assert cosine_similarity(a, b) > cosine_similarity(a, c)


def test_cosine_similarity_edge_cases():
    embedder = HashEmbedder()
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity(embedder.embed(""), embedder.embed("")) == 0.0

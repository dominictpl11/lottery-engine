"""加权抽奖算法（NFR-4）。

算法刻意不依赖 FastAPI / MySQL / Redis，所以这里可以纯内存测试。
"""

import random
from collections import Counter
from dataclasses import dataclass

import pytest

from app.domain.strategy.draw_algorithm import WeightedDrawAlgorithm


@dataclass
class FakeAward:
    """算法只用到 weight，不需要真的 ORM 对象。"""
    award_id: int
    weight: int


@pytest.fixture
def algo():
    return WeightedDrawAlgorithm()


def test_empty_list_returns_none(algo):
    """空奖品列表应正常返回未中奖，而不是抛异常。"""
    assert algo.draw([]) is None


def test_single_award_always_wins(algo):
    award = FakeAward(1, 10)
    assert all(algo.draw([award]) is award for _ in range(50))


def test_returns_one_of_the_candidates(algo):
    awards = [FakeAward(i, i + 1) for i in range(5)]
    for _ in range(200):
        assert algo.draw(awards) in awards


def test_zero_total_weight_returns_none(algo):
    """权重全为 0 时不应除零或死循环。"""
    assert algo.draw([FakeAward(1, 0), FakeAward(2, 0)]) is None


def test_deterministic_with_fixed_seed(algo):
    """固定种子下结果可复现——否则统计测试失败时无法定位。"""
    awards = [FakeAward(i, 10) for i in range(5)]
    random.seed(12345)
    first = [algo.draw(awards).award_id for _ in range(20)]
    random.seed(12345)
    second = [algo.draw(awards).award_id for _ in range(20)]
    assert first == second


@pytest.mark.parametrize("n", [100_000])
def test_distribution_matches_weights(algo, n):
    """统计测试：10 万次模拟，实际分布与配置权重基本一致。

    允许随机误差，不能要求精确相等。这里用相对误差 5%——按二项分布，
    p=0.01 时 10 万次的标准差约 0.03%，5% 的相对容差足够宽松到不会偶发失败，
    又足够紧到能抓出"权重没生效"这类真问题。
    """
    weights = {"一等奖": 1, "二等奖": 9, "三等奖": 20, "谢谢参与": 70}
    awards = [FakeAward(i, w) for i, w in enumerate(weights.values())]
    total = sum(weights.values())

    random.seed(2026)
    counts = Counter(algo.draw(awards).award_id for _ in range(n))

    for i, (name, w) in enumerate(weights.items()):
        expected = w / total
        actual = counts[i] / n
        rel_err = abs(actual - expected) / expected
        assert rel_err < 0.05, (
            f"{name}: 期望 {expected:.4f}, 实际 {actual:.4f}, 相对误差 {rel_err:.2%}"
        )


def test_weight_ordering_is_respected(algo):
    """权重大的奖品必须被抽中得更多。"""
    awards = [FakeAward(0, 1), FakeAward(1, 99)]
    random.seed(7)
    counts = Counter(algo.draw(awards).award_id for _ in range(10_000))
    assert counts[1] > counts[0] * 10

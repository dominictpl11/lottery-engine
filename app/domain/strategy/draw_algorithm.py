import random

from app.domain.models import Award


class WeightedDrawAlgorithm:
    def draw(self, awards: list[Award]) -> Award | None:
        if not awards:
            return None

        total_weight = sum(award.weight for award in awards)
        if total_weight <= 0:
            return None

        cursor = random.uniform(0, total_weight)
        cumulative = 0.0
        for award in awards:
            cumulative += award.weight
            if cursor <= cumulative:
                return award

        return None

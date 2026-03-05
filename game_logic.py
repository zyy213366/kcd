import random
from collections import Counter


def roll_dice(n):
    """Rolls n dice and returns a list of their values."""
    return sorted([random.randint(1, 6) for _ in range(n)])


def calculate_score(dice_values):
    """
    Calculates the score for a set of dice values according to KCD Farkle rules.
    Returns (score, list_of_scoring_dice_indices).
    """
    if not dice_values:
        return 0, []

    score = 0
    scoring_indices = []
    counts = Counter(dice_values)

    # Check for straight 1-6 (1500 points)
    if len(dice_values) == 6 and set(dice_values) == {1, 2, 3, 4, 5, 6}:
        return 1500, list(range(6))

    # Process multiples
    for val, count in counts.items():
        if count >= 3:
            # Base score for 3 of a kind
            base = 1000 if val == 1 else val * 100

            # Multiplier for 4, 5, 6 of a kind
            multiplier = 2 ** (count - 3)
            score += base * multiplier

            # Add indices
            scoring_indices.extend([i for i, v in enumerate(dice_values) if v == val])

            # Remove from counts so we don't score individual 1s or 5s again
            counts[val] = 0

    # Process remaining 1s and 5s
    for val, count in counts.items():
        if count > 0:
            if val == 1:
                score += count * 100
                scoring_indices.extend(
                    [i for i, v in enumerate(dice_values) if v == val]
                )
            elif val == 5:
                score += count * 50
                scoring_indices.extend(
                    [i for i, v in enumerate(dice_values) if v == val]
                )

    return score, sorted(scoring_indices)


def is_farkle(dice_values):
    """Returns True if the dice roll yields no points (a Farkle)."""
    score, _ = calculate_score(dice_values)
    return score == 0

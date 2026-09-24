"""Pure transitions for one Farkle turn."""

from copy import deepcopy

from game_logic import calculate_score, is_farkle


def selection_score(dice, selected, confirmed):
    """Score newly selected dice only if every new selection contributes."""
    if len(selected) != len(dice):
        return 0
    new_values = [
        value
        for index, value in enumerate(dice)
        if selected[index] and not (index < len(confirmed) and confirmed[index])
    ]
    score, scoring_indices = calculate_score(new_values)
    return score if len(scoring_indices) == len(new_values) else 0


def _clear_dice(turn_state):
    turn_state.update(
        current_dice=[], locked_dice=[], previously_locked=[], dice_remaining=6
    )


def roll_turn(turn_state, selected, new_dice):
    """Return the updated turn and whether the new throw Farkled."""
    next_state = deepcopy(turn_state)
    dice = turn_state["current_dice"]
    if dice:
        points = selection_score(dice, selected, turn_state.get("previously_locked", []))
        if points <= 0:
            raise ValueError("Select scoring dice before rolling again")
        expected_count = 6 if all(selected) else len(dice) - sum(selected)
        next_state["round_score"] += points
    else:
        expected_count = 6
        selected = []
    if len(new_dice) != expected_count:
        raise ValueError("Incorrect number of dice for this roll")

    if is_farkle(new_dice):
        next_state["round_score"] = 0
        next_state["current_player"] = 2 if turn_state["current_player"] == 1 else 1
        _clear_dice(next_state)
        return next_state, True

    if expected_count == 6:
        next_state["current_dice"] = list(new_dice)
        next_state["locked_dice"] = [False] * 6
        next_state["previously_locked"] = [False] * 6
    else:
        fresh = iter(new_dice)
        next_state["current_dice"] = [
            value if selected[index] else next(fresh)
            for index, value in enumerate(dice)
        ]
        next_state["locked_dice"] = list(selected)
        next_state["previously_locked"] = list(selected)
    next_state["dice_remaining"] = expected_count
    return next_state, False


def bank_turn(scores, turn_state, selected):
    """Bank the round and either pass the turn or finish the game."""
    next_scores = dict(scores)
    next_state = deepcopy(turn_state)
    points = selection_score(
        turn_state["current_dice"], selected, turn_state.get("previously_locked", [])
    )
    if points == 0 and next_state["round_score"] == 0:
        raise ValueError("Select scoring dice before banking")
    next_state["round_score"] += points
    player = turn_state["current_player"]
    score_key = f"p{player}"
    next_scores[score_key] += next_state["round_score"]
    if next_scores[score_key] >= turn_state.get("target_score", 10000):
        next_state["game_over"] = True
        next_state["winner"] = player
    else:
        next_state["current_player"] = 2 if player == 1 else 1
    next_state["round_score"] = 0
    _clear_dice(next_state)
    return next_scores, next_state

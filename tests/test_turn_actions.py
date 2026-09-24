import copy
import unittest

from turn_actions import bank_turn, roll_turn, selection_score


def state(**overrides):
    result = {
        "current_player": 1,
        "round_score": 0,
        "current_dice": [],
        "locked_dice": [],
        "previously_locked": [],
        "dice_remaining": 6,
        "target_score": 10000,
        "game_over": False,
        "winner": 0,
    }
    result.update(overrides)
    return result


class TurnActionsTest(unittest.TestCase):
    def test_selection_rejects_unscoring_die(self):
        self.assertEqual(selection_score([1, 2, 3], [True, True, False], []), 0)

    def test_selection_excludes_confirmed_dice(self):
        self.assertEqual(
            selection_score([1, 5, 3], [True, True, False], [True, False, False]),
            50,
        )

    def test_first_roll_starts_new_six_die_throw(self):
        next_state, farkled = roll_turn(state(), [], [1, 2, 3, 4, 5, 6])
        self.assertFalse(farkled)
        self.assertEqual(next_state["current_dice"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(next_state["locked_dice"], [False] * 6)

    def test_roll_keeps_selected_die_and_adds_its_score(self):
        original = state(current_dice=[1, 2, 3, 4, 5, 6], locked_dice=[False] * 6)
        snapshot = copy.deepcopy(original)
        next_state, farkled = roll_turn(original, [True, False, False, False, False, False], [2, 3, 4, 5, 6])
        self.assertFalse(farkled)
        self.assertEqual(next_state["round_score"], 100)
        self.assertEqual(next_state["current_dice"], [1, 2, 3, 4, 5, 6])
        self.assertTrue(next_state["previously_locked"][0])
        self.assertEqual(original, snapshot)

    def test_farkle_loses_round_score_and_passes_turn(self):
        original = state(round_score=500, current_dice=[1, 2, 3, 4, 5, 6], locked_dice=[False] * 6)
        next_state, farkled = roll_turn(original, [True, False, False, False, False, False], [2, 2, 3, 3, 4])
        self.assertTrue(farkled)
        self.assertEqual(next_state["round_score"], 0)
        self.assertEqual(next_state["current_player"], 2)
        self.assertEqual(next_state["current_dice"], [])

    def test_hot_dice_rolls_all_six_again(self):
        original = state(current_dice=[1] * 6, locked_dice=[False] * 6)
        next_state, farkled = roll_turn(original, [True] * 6, [1, 2, 3, 4, 5, 6])
        self.assertFalse(farkled)
        self.assertEqual(next_state["round_score"], 8000)
        self.assertEqual(next_state["current_dice"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(next_state["previously_locked"], [False] * 6)

    def test_bank_adds_score_and_marks_winner(self):
        original = state(current_dice=[1, 2, 3, 4, 5, 6], locked_dice=[False] * 6, round_score=200, target_score=300)
        scores, next_state = bank_turn({"p1": 0, "p2": 0}, original, [True, False, False, False, False, False])
        self.assertEqual(scores["p1"], 300)
        self.assertTrue(next_state["game_over"])
        self.assertEqual(next_state["winner"], 1)

    def test_bank_allows_saved_round_points_after_a_hot_dice_roll(self):
        original = state(current_dice=[2, 3, 4, 5, 6, 2], round_score=8000)
        scores, next_state = bank_turn({"p1": 0, "p2": 0}, original, [False] * 6)
        self.assertEqual(scores["p1"], 8000)
        self.assertEqual(next_state["current_player"], 2)


if __name__ == "__main__":
    unittest.main()

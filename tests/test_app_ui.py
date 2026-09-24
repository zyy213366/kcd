import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from db_manager import ConcurrentUpdateError


APP = Path(__file__).resolve().parents[1] / "app.py"


def room():
    return {
        "room_code": "KCD888",
        "player1": "甲",
        "player2": "乙",
        "scores": {"p1": 0, "p2": 0},
        "last_action": "v1",
        "turn_state": {
            "current_player": 1,
            "round_score": 0,
            "current_dice": [1, 2, 3, 4, 5, 6],
            "locked_dice": [False] * 6,
            "previously_locked": [False] * 6,
            "dice_remaining": 6,
            "target_score": 1000,
            "game_over": False,
            "winner": 0,
        },
    }


def saved_room(client, code, scores, turn_state, expected_action):
    result = room()
    result["scores"] = scores
    result["turn_state"] = turn_state
    result["last_action"] = "v2"
    return result


class AppUiTest(unittest.TestCase):
    def test_selecting_die_uses_local_state_without_remote_calls(self):
        with patch("db_manager.init_connection", return_value=object()), \
             patch("db_manager.get_room", return_value=room()) as get_room, \
             patch("db_manager.update_game_state", side_effect=saved_room) as update:
            app = AppTest.from_file(str(APP))
            app.session_state["room_code"] = "KCD888"
            app.session_state["player_num"] = 1
            app.run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(get_room.call_count, 1)
            app.button(key="die_0").click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(get_room.call_count, 1)
            update.assert_not_called()
            self.assertEqual(app.session_state["_dice_selection"][0], True)

    def test_banking_selected_die_writes_once(self):
        with patch("db_manager.init_connection", return_value=object()), \
             patch("db_manager.get_room", return_value=room()) as get_room, \
             patch("db_manager.update_game_state", side_effect=saved_room) as update:
            app = AppTest.from_file(str(APP))
            app.session_state["room_code"] = "KCD888"
            app.session_state["player_num"] = 1
            app.run()
            app.button(key="die_0").click().run()
            next(button for button in app.button if button.label == "存入 100 分").click().run()
            self.assertEqual(len(app.exception), 0)
            update.assert_called_once()
            self.assertEqual(update.call_args.args[2]["p1"], 100)
            self.assertEqual(app.session_state["_room_snapshot"]["turn_state"]["current_player"], 2)
            self.assertEqual(update.call_args.args[4], "v1")
            self.assertLessEqual(get_room.call_count, 2)

    def test_rolling_selected_die_writes_once(self):
        with patch("db_manager.init_connection", return_value=object()), \
             patch("db_manager.get_room", return_value=room()), \
             patch("db_manager.update_game_state", side_effect=saved_room) as update, \
             patch("game_logic.roll_dice", return_value=[1, 2, 3, 4, 5]):
            app = AppTest.from_file(str(APP))
            app.session_state["room_code"] = "KCD888"
            app.session_state["player_num"] = 1
            app.run()
            app.button(key="die_0").click().run()
            next(button for button in app.button if button.label == "🎲 继续掷骰").click().run()
            self.assertEqual(len(app.exception), 0)
            update.assert_called_once()
            self.assertEqual(update.call_args.args[3]["round_score"], 100)

    def test_stale_bank_reloads_room_instead_of_claiming_success(self):
        fresh = room()
        fresh["scores"] = {"p1": 800, "p2": 0}
        fresh["last_action"] = "v2"
        with patch("db_manager.init_connection", return_value=object()), \
             patch("db_manager.get_room", side_effect=[room(), fresh]), \
             patch("db_manager.update_game_state", side_effect=ConcurrentUpdateError("stale")) as update:
            app = AppTest.from_file(str(APP))
            app.session_state["room_code"] = "KCD888"
            app.session_state["player_num"] = 1
            app.run()
            app.button(key="die_0").click().run()
            next(button for button in app.button if button.label == "存入 100 分").click().run()
            self.assertEqual(len(app.exception), 0)
            update.assert_called_once()
            self.assertEqual(app.session_state["_room_snapshot"]["scores"]["p1"], 800)


if __name__ == "__main__":
    unittest.main()

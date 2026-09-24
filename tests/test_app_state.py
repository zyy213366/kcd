import unittest

from app_state import load_room_snapshot, selection_for, clear_selection, should_poll_room


class AppStateTest(unittest.TestCase):
    def test_poll_starts_while_first_room_fetch_is_pending(self):
        self.assertTrue(should_poll_room(None, 1))

    def test_poll_only_while_waiting_for_another_player_or_turn(self):
        room = {"player2": "乙", "turn_state": {"current_player": 1, "game_over": False}}
        self.assertFalse(should_poll_room(room, 1))
        self.assertTrue(should_poll_room(room, 2))
        room["player2"] = None
        self.assertTrue(should_poll_room(room, 1))
        room["turn_state"]["game_over"] = True
        self.assertFalse(should_poll_room(room, 1))

    def test_same_poll_tick_reuses_room_without_fetch(self):
        session = {}
        calls = []

        def fetch(code):
            calls.append(code)
            return {"room_code": code, "last_action": "v1"}

        first, error = load_room_snapshot(session, "ROOM", 0, fetch)
        second, error2 = load_room_snapshot(session, "ROOM", 0, fetch)
        self.assertIs(first, second)
        self.assertEqual(calls, ["ROOM"])
        self.assertIsNone(error)
        self.assertIsNone(error2)

    def test_new_poll_tick_fetches_remote_room(self):
        session = {}
        versions = iter([1, 2])
        fetch = lambda code: {"room_code": code, "version": next(versions)}
        load_room_snapshot(session, "ROOM", 0, fetch)
        room, error = load_room_snapshot(session, "ROOM", 1, fetch)
        self.assertEqual(room["version"], 2)
        self.assertIsNone(error)

    def test_failed_poll_keeps_previous_snapshot(self):
        session = {}
        load_room_snapshot(session, "ROOM", 0, lambda code: {"room_code": code})

        def fail(code):
            raise ConnectionError("offline")

        room, error = load_room_snapshot(session, "ROOM", 1, fail)
        self.assertEqual(room["room_code"], "ROOM")
        self.assertIn("offline", error)

    def test_selection_resets_when_roll_changes(self):
        session = {}
        room = {
            "last_action": "v1",
            "turn_state": {"current_player": 1, "current_dice": [1, 2], "previously_locked": [False, False]},
        }
        selected = selection_for(session, room)
        selected[0] = True
        self.assertEqual(selection_for(session, room), [True, False])
        room["last_action"] = "v2"
        self.assertEqual(selection_for(session, room), [False, False])

    def test_confirmed_dice_stay_selected_after_reset(self):
        session = {}
        room = {
            "last_action": "v1",
            "turn_state": {"current_player": 1, "current_dice": [1, 2], "previously_locked": [True, False]},
        }
        self.assertEqual(selection_for(session, room), [True, False])
        clear_selection(session)
        self.assertEqual(selection_for(session, room), [True, False])


if __name__ == "__main__":
    unittest.main()

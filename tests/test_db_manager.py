import unittest
from unittest.mock import MagicMock

from db_manager import ConcurrentUpdateError, create_room, join_room, update_game_state


class DbManagerTest(unittest.TestCase):
    def test_create_room_inserts_without_a_second_lookup(self):
        client = MagicMock()
        create_room(client, "ROOM", "甲", 1000)
        query = client.table.return_value
        query.insert.assert_called_once()
        query.select.assert_not_called()
        payload = query.insert.call_args.args[0]
        self.assertEqual(payload["room_code"], "ROOM")
        self.assertEqual(payload["turn_state"]["target_score"], 1000)
        self.assertNotEqual(payload["last_action"], "now()")

    def test_create_room_reports_database_failure(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = ConnectionError("offline")
        with self.assertRaises(ConnectionError):
            create_room(client, "ROOM", "甲", 1000)

    def test_join_room_reports_database_failure(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.execute.side_effect = ConnectionError("offline")
        with self.assertRaises(ConnectionError):
            join_room(client, "ROOM", "乙")

    def test_game_update_matches_the_room_version_and_returns_saved_row(self):
        client = MagicMock()
        saved = {"room_code": "ROOM", "last_action": "new", "scores": {"p1": 100}, "turn_state": {}}
        query = client.table.return_value.update.return_value.eq.return_value.eq.return_value
        query.execute.return_value.data = [saved]
        result = update_game_state(client, "ROOM", {"p1": 100}, {}, "old")
        self.assertEqual(result, saved)
        client.table.return_value.update.return_value.eq.return_value.eq.assert_called_once_with("last_action", "old")

    def test_game_update_rejects_zero_affected_rows(self):
        client = MagicMock()
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        with self.assertRaises(ConcurrentUpdateError):
            update_game_state(client, "ROOM", {"p1": 100}, {}, "old")


if __name__ == "__main__":
    unittest.main()

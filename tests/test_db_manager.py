import unittest
from unittest.mock import MagicMock

from db_manager import create_room, join_room


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


if __name__ == "__main__":
    unittest.main()

"""Small session-state helpers for the Streamlit game screen."""


def should_poll_room(room, player_num):
    if room is None:
        return True
    turn = room["turn_state"]
    return not turn.get("game_over", False) and (
        not room.get("player2") or turn["current_player"] != player_num
    )


def load_room_snapshot(session, room_code, poll_tick, fetch):
    """Fetch once per poll tick and reuse the last room for local UI reruns."""
    needs_fetch = (
        session.get("_room_code") != room_code
        or "_room_snapshot" not in session
        or (poll_tick is not None and session.get("_room_poll_tick") != poll_tick)
    )
    if not needs_fetch:
        return session["_room_snapshot"], None
    try:
        room = fetch(room_code)
    except Exception as exc:
        session["_room_poll_tick"] = poll_tick
        return session.get("_room_snapshot"), str(exc)
    session["_room_code"] = room_code
    session["_room_poll_tick"] = poll_tick
    session["_room_snapshot"] = room
    return room, None


def selection_for(session, room):
    """Keep local picks until the server publishes another room action."""
    turn = room["turn_state"]
    dice = turn.get("current_dice", [])
    confirmed = turn.get("previously_locked", [])
    signature = (
        room.get("last_action"),
        turn.get("current_player"),
        tuple(dice),
        tuple(confirmed),
    )
    if session.get("_dice_signature") != signature:
        session["_dice_signature"] = signature
        session["_dice_selection"] = [
            index < len(confirmed) and bool(confirmed[index])
            for index in range(len(dice))
        ]
    return session["_dice_selection"]


def clear_selection(session):
    session.pop("_dice_signature", None)
    session.pop("_dice_selection", None)

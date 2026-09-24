import streamlit as st
from datetime import datetime, timezone
from supabase import create_client, Client


class ConcurrentUpdateError(RuntimeError):
    """The room was changed before this action was saved."""


@st.cache_resource
def init_connection():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)


def get_room(supabase: Client, room_code: str):
    response = (
        supabase.table("games")
        .select("room_code,player1,player2,scores,turn_state,last_action")
        .eq("room_code", room_code)
        .execute()
    )
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def create_room(supabase: Client, room_code: str, player1: str, target_score: int):
    data = {
        "room_code": room_code,
        "player1": player1,
        "player2": None,
        "scores": {"p1": 0, "p2": 0},
        "turn_state": {
            "current_player": 1,
            "round_score": 0,
            "current_dice": [],
            "locked_dice": [],
            "previously_locked": [],
            "dice_remaining": 6,
            "target_score": target_score,
            "game_over": False,
            "winner": 0,
        },
        "last_action": datetime.now(timezone.utc).isoformat(),
    }
    return supabase.table("games").insert(data).execute()


def join_room(supabase: Client, room_code: str, player2: str):
    data = {"player2": player2, "last_action": datetime.now(timezone.utc).isoformat()}
    return supabase.table("games").update(data).eq("room_code", room_code).execute()


def update_game_state(
    supabase: Client,
    room_code: str,
    scores: dict,
    turn_state: dict,
    expected_action: str,
):
    updates = {
        "scores": scores,
        "turn_state": turn_state,
        "last_action": datetime.now(timezone.utc).isoformat(),
    }
    query = supabase.table("games").update(updates).eq("room_code", room_code)
    query = (
        query.eq("last_action", expected_action)
        if expected_action is not None
        else query.is_("last_action", "null")
    )
    rows = query.execute().data or []
    if len(rows) != 1:
        raise ConcurrentUpdateError("Room changed or is no longer writable")
    return rows[0]

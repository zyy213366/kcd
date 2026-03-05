import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def init_connection():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)


def get_room(supabase: Client, room_code: str):
    response = supabase.table("games").select("*").eq("room_code", room_code).execute()
    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def create_room(supabase: Client, room_code: str, player1: str, target_score: int):
    # Try to insert first. If it fails due to conflict, we catch it and ignore it
    # to avoid overwriting player2 if they already joined in a weird race condition
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
        "last_action": "now()",
    }

    try:
        # First check if the room exists
        existing = (
            supabase.table("games").select("*").eq("room_code", room_code).execute()
        )
        if existing.data and len(existing.data) > 0:
            # Room exists, just update player 1 name in case it changed
            supabase.table("games").update({"player1": player1}).eq(
                "room_code", room_code
            ).execute()
        else:
            # Room doesn't exist, insert it
            supabase.table("games").insert(data).execute()
    except Exception as e:
        print(f"Db create room error: {e}")

    return True


def join_room(supabase: Client, room_code: str, player2: str):
    data = {"player2": player2, "last_action": "now()"}
    try:
        supabase.table("games").update(data).eq("room_code", room_code).execute()
    except Exception as e:
        print(f"Db join room error: {e}")
    return True


def update_game_state(supabase: Client, room_code: str, scores: dict, turn_state: dict):
    updates = {"scores": scores, "turn_state": turn_state, "last_action": "now()"}
    response = (
        supabase.table("games").update(updates).eq("room_code", room_code).execute()
    )
    return response

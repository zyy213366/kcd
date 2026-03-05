import streamlit as st
import time
from game_logic import roll_dice, calculate_score, is_farkle
from streamlit_autorefresh import st_autorefresh
from db_manager import (
    init_connection,
    get_room,
    create_room,
    join_room,
    update_game_state,
)

# Supabase Initialization
try:
    supabase = init_connection()
except Exception as e:
    st.error(f"Failed to connect to Supabase. Check secrets. Error: {e}")
    st.stop()

# Session State Initialization
if "room_code" not in st.session_state:
    st.session_state.room_code = ""
if "player_num" not in st.session_state:
    st.session_state.player_num = 0
if "animating" not in st.session_state:
    st.session_state.animating = False
if "anim_flip" not in st.session_state:
    st.session_state.anim_flip = False


# --- UI Functions ---
def show_login():
    st.title("🎲 KCD Farkle (Online)")

    st.write("Join or create a room to play.")

    room = st.text_input("Room Code")
    name = st.text_input("Your Name")
    target_score = st.number_input(
        "Target Score (Create Room)", min_value=1000, max_value=50000, value=10000
    )

    col1, col2 = st.columns(2)
    if col1.button("Create Room"):
        if room and name:
            existing = get_room(supabase, room)
            if existing:
                p1_name = existing.get("player1")
                p2_name = existing.get("player2")
                if p1_name == name:
                    st.session_state.player_num = 1
                elif p2_name == name:
                    st.session_state.player_num = 2
                elif not p2_name:
                    join_room(supabase, room, name)
                    st.session_state.player_num = 2
                else:
                    st.error("Room is full.")
                    return
            else:
                create_room(supabase, room, name, int(target_score))
                st.session_state.player_num = 1

            st.session_state.room_code = room
            st.session_state.player_name = name
            st.rerun()

    if col2.button("Join Room"):
        if room and name:
            existing = get_room(supabase, room)
            if not existing:
                st.error("Room not found.")
                return

            p1_name = existing.get("player1")
            p2_name = existing.get("player2")
            if p1_name == name:
                st.session_state.player_num = 1
            elif p2_name == name:
                st.session_state.player_num = 2
            elif not p2_name:
                # When Player 2 clicks join, force an update in the database
                join_room(supabase, room, name)
                st.session_state.player_num = 2
            else:
                st.error("Room is full.")
                return

            st.session_state.room_code = room
            st.session_state.player_name = name
            st.rerun()


def show_game(room_data):
    st.title(f"Room: {room_data['room_code']}")

    p1_name = room_data["player1"]
    p2_name = room_data["player2"] or "Waiting..."
    target_score = room_data["turn_state"].get("target_score", 10000)
    is_game_over = room_data["turn_state"].get("game_over", False)
    winner = room_data["turn_state"].get("winner", 0)

    col1, col2 = st.columns(2)
    col1.metric(p1_name, room_data["scores"]["p1"])
    col2.metric(p2_name, room_data["scores"]["p2"])

    current_player = room_data["turn_state"]["current_player"]
    is_my_turn = current_player == st.session_state.player_num

    st.subheader(
        f"Current Turn: {'You' if is_my_turn else ('Player ' + str(current_player))}"
    )
    st.caption(f"Target Score: {target_score}")
    st.write(f"Round Score: {room_data['turn_state']['round_score']}")
    if is_game_over:
        winner_name = p1_name if winner == 1 else p2_name
        st.success(f"Game Over! Winner: {winner_name}")

    # --- Dice Rendering ---
    dice_results = room_data["turn_state"].get("current_dice", [])
    locked_dice = room_data["turn_state"].get("locked_dice", [])
    previously_locked = room_data["turn_state"].get("previously_locked", [])
    remaining = room_data["turn_state"].get("dice_remaining", 6)

    if dice_results:
        st.write("Current Dice:")
        cols = st.columns(len(dice_results))
        new_locked = []
        for i, val in enumerate(dice_results):
            with cols[i]:
                # 渲染 GIF
                # Use query params to break cache to restart gif animation
                if st.session_state.anim_flip:
                    st.write(" ")
                placeholder = st.empty()
                placeholder.image(f"assets/{val}.gif", width=80)
                if not st.session_state.anim_flip:
                    st.write(" ")

                # Checkbox
                if is_my_turn:
                    is_locked = i < len(locked_dice) and locked_dice[i]
                    is_confirmed = i < len(previously_locked) and previously_locked[i]
                    if is_confirmed:
                        st.checkbox(
                            "Lock",
                            value=True,
                            key=f"dice_{i}",
                            disabled=True,
                        )
                        new_locked.append(True)
                    else:
                        if st.checkbox("Lock", value=is_locked, key=f"dice_{i}"):
                            new_locked.append(True)
                        else:
                            new_locked.append(False)
                else:
                    st.write(
                        "Locked" if (i < len(locked_dice) and locked_dice[i]) else ""
                    )

        if is_my_turn and new_locked != locked_dice:
            room_data["turn_state"]["locked_dice"] = new_locked
            room_data["turn_state"]["dice_remaining"] = 6 - sum(
                1 for x in new_locked if x
            )
            update_game_state(
                supabase,
                st.session_state.room_code,
                room_data["scores"],
                room_data["turn_state"],
            )
            st.rerun()

    # Auto-refresh mechanism
    if not is_my_turn:
        # Run the autorefresh about every 2 seconds (2000 milliseconds)
        st_autorefresh(interval=2000, key="datarefresh")
    else:
        # IMPORTANT: When it IS your turn, you still need to refresh if p2_name is waiting
        if p2_name == "Waiting...":
            st_autorefresh(interval=2000, key="datarefresh_waiting")

    if is_my_turn:
        col1, col2, col3 = st.columns(3)

        # Calculate potential score currently selected
        newly_locked = []
        if dice_results:
            newly_locked = [
                dice_results[i]
                for i, locked in enumerate(locked_dice)
                if locked
                and not (
                    room_data["turn_state"].get("previously_locked")
                    and i < len(room_data["turn_state"].get("previously_locked", []))
                    and room_data["turn_state"]["previously_locked"][i]
                )
            ]
        temp_score, remaining_after_score = calculate_score(newly_locked)

        can_roll = False
        if not dice_results:
            can_roll = True  # First roll
        elif temp_score > 0:
            can_roll = True  # Has scored something this roll, can push luck

        if col1.button(
            "Roll Dice",
            disabled=not p2_name
            or p2_name == "Waiting..."
            or not can_roll
            or is_game_over,
        ):
            # 如果是回合的第一次掷骰子或者全部被锁定
            if not dice_results or all(locked_dice) or any(locked_dice):
                # We need to bank the temp score to round score before re-rolling
                if temp_score > 0:
                    room_data["turn_state"]["round_score"] += temp_score

                # 重新掷所有剩余的未锁定骰子 (或者如果全部锁定，重置 6 个)
                dice_to_roll = 6 if (all(locked_dice) and dice_results) else remaining
                new_dice = roll_dice(dice_to_roll)

                # Check Farkle
                if is_farkle(new_dice):
                    st.error("Farkle! You lose your round score.")
                    room_data["turn_state"]["round_score"] = 0
                    room_data["turn_state"]["current_player"] = (
                        2 if current_player == 1 else 1
                    )
                    room_data["turn_state"]["current_dice"] = []
                    room_data["turn_state"]["locked_dice"] = []
                    room_data["turn_state"]["previously_locked"] = []
                    room_data["turn_state"]["dice_remaining"] = 6

                    try:
                        update_game_state(
                            supabase,
                            st.session_state.room_code,
                            room_data["scores"],
                            room_data["turn_state"],
                        )
                    except Exception as e:
                        pass
                    time.sleep(2)  # Show farkle message briefly
                    st.rerun()
                else:
                    # 只有部分被重新掷了
                    if dice_to_roll < 6:
                        # 组合旧的锁定骰子和新骰子
                        # Keep locked dice in their original positions, put new dice in unlocked positions
                        combined_dice = [0] * 6
                        new_dice_idx = 0
                        for i in range(6):
                            if locked_dice[i]:
                                combined_dice[i] = dice_results[i]
                            else:
                                combined_dice[i] = new_dice[new_dice_idx]
                                new_dice_idx += 1

                        room_data["turn_state"]["current_dice"] = combined_dice
                        # Mark previously locked dice as locked, and the new ones as unlocked
                        room_data["turn_state"]["locked_dice"] = list(locked_dice)
                        room_data["turn_state"]["previously_locked"] = list(locked_dice)
                    else:
                        room_data["turn_state"]["current_dice"] = new_dice
                        room_data["turn_state"]["locked_dice"] = [False] * 6
                        room_data["turn_state"]["previously_locked"] = [False] * 6

                    room_data["turn_state"]["dice_remaining"] = dice_to_roll

                try:
                    update_game_state(
                        supabase,
                        st.session_state.room_code,
                        room_data["scores"],
                        room_data["turn_state"],
                    )
                except Exception as e:
                    st.error(f"Failed to update game state: {e}")

                # Set a unique animation key per roll to force gif to restart
                import uuid

                st.session_state.anim_key = str(uuid.uuid4())
                st.session_state.animating = True
                st.session_state.anim_flip = not st.session_state.anim_flip

                # Using rerun at the end of the action
                st.rerun()

        if st.session_state.animating:
            time.sleep(1.0)  # Wait for GIF to "finish"
            st.session_state.animating = False
            try:
                st.rerun()
            except Exception:
                pass

        if dice_results:
            if col2.button(
                f"Pass & Bank ({temp_score + room_data['turn_state']['round_score']})",
                disabled=(
                    temp_score == 0 and room_data["turn_state"]["round_score"] == 0
                )
                or st.session_state.animating
                or is_game_over,
            ):
                # When banking, add the temporary score of currently locked dice to the round score before banking it
                room_data["turn_state"]["round_score"] += temp_score

                if current_player == 1:
                    room_data["scores"]["p1"] += room_data["turn_state"]["round_score"]
                else:
                    room_data["scores"]["p2"] += room_data["turn_state"]["round_score"]

                if room_data["scores"]["p1"] >= target_score:
                    room_data["turn_state"]["game_over"] = True
                    room_data["turn_state"]["winner"] = 1
                elif room_data["scores"]["p2"] >= target_score:
                    room_data["turn_state"]["game_over"] = True
                    room_data["turn_state"]["winner"] = 2

                room_data["turn_state"]["round_score"] = 0
                if not room_data["turn_state"].get("game_over", False):
                    room_data["turn_state"]["current_player"] = (
                        2 if current_player == 1 else 1
                    )
                room_data["turn_state"]["current_dice"] = []
                room_data["turn_state"]["locked_dice"] = []
                room_data["turn_state"]["previously_locked"] = []
                room_data["turn_state"]["dice_remaining"] = 6

                try:
                    update_game_state(
                        supabase,
                        st.session_state.room_code,
                        room_data["scores"],
                        room_data["turn_state"],
                    )
                except Exception as e:
                    st.error(f"Failed to update game state: {e}")

                try:
                    st.rerun()
                except Exception:
                    pass


# --- Main App ---
if "room_code" not in st.session_state or not st.session_state.room_code:
    show_login()
else:
    try:
        room_data = get_room(supabase, st.session_state.room_code)
        if room_data:
            show_game(room_data)
        else:
            st.error("Room lost or does not exist.")
            if st.button("Back to login"):
                st.session_state.room_code = ""
                st.rerun()
    except Exception as e:
        st.error(f"Network error getting room: {e}")
        st_autorefresh(interval=2000, key="datarefresh_error")

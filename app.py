"""KCD Farkle: a small two-player room game."""

from html import escape

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from app_state import clear_selection, load_room_snapshot, selection_for, should_poll_room
from db_manager import ConcurrentUpdateError, create_room, get_room, init_connection, join_room, update_game_state
from game_logic import roll_dice
from turn_actions import bank_turn, roll_turn, selection_score


st.set_page_config(page_title="KCD 骰子对决", page_icon="🎲", layout="centered")

st.markdown(
    """
<style>
  .stApp { background: #f7f9f6; color: #18251c; }
  .block-container { max-width: 820px; padding-top: 1.4rem; padding-bottom: 5rem; }
  h1, h2, h3 { color: #162e20; letter-spacing: -.025em; }
  h1 { font-size: clamp(2rem, 6vw, 3rem) !important; }
  div[data-testid="stForm"], .st-key-dice_grid {
    background: white; border: 1px solid #e5ebe5; border-radius: 22px;
    padding: 1rem 1.15rem; box-shadow: 0 8px 30px rgba(16, 48, 27, .04);
  }
  .eyebrow { color: #5b7563; font-size: .78rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
  .intro { color: #5d6e61; font-size: 1.04rem; margin: -.3rem 0 1.5rem; }
  .room-id { color: #66816d; font-size: .88rem; font-weight: 700; letter-spacing: .06em; }
  .score-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; margin: 1rem 0; }
  .score-card { background: #fff; border: 1px solid #e5ebe5; border-radius: 20px; padding: 1rem 1.1rem; min-width: 0; }
  .score-card.active { border-color: #9ac5a5; background: #f0f9f1; }
  .score-name { color: #607363; font-size: .9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .score-value { color: #183621; font-size: clamp(1.8rem, 6vw, 2.6rem); font-weight: 800; line-height: 1.15; margin: .35rem 0 .6rem; }
  .score-track { height: 7px; background: #e8eee8; border-radius: 100px; overflow: hidden; }
  .score-progress { height: 100%; background: #3d8d59; border-radius: inherit; }
  .turn-panel { background: #e9f3eb; border-radius: 18px; padding: .9rem 1.1rem; margin: .9rem 0 1.2rem; }
  .turn-title { font-weight: 800; font-size: 1.1rem; color: #1d5631; }
  .turn-detail { color: #54705b; margin-top: .2rem; font-size: .92rem; }
  .score-preview { color: #42624b; font-size: 1rem; margin: .6rem 0 1rem; }
  .st-key-dice_grid [data-testid="stButton"] button { min-height: 4.2rem; width: 100%; font-size: 1.15rem; border-radius: 16px; }
  .st-key-actions [data-testid="stButton"] button { min-height: 3.4rem; width: 100%; border-radius: 13px; font-weight: 700; }
  div[data-testid="stFormSubmitButton"] button { min-height: 3rem; width: 100%; border-radius: 12px; }
  @media (max-width: 600px) {
    .block-container { padding: .9rem .85rem 4rem; }
    .score-grid { gap: .5rem; }
    .score-card { padding: .85rem; border-radius: 16px; }
    .st-key-dice_grid { padding: .75rem; }
    .st-key-dice_grid [data-testid="stHorizontalBlock"] { gap: .45rem; flex-wrap: nowrap; }
    .st-key-dice_grid [data-testid="stColumn"] { min-width: 0; flex: 1 1 0; }
    .st-key-dice_grid [data-testid="stButton"] button { min-height: 3.7rem; font-size: 1rem; padding: .35rem; }
  }
</style>
""",
    unsafe_allow_html=True,
)


try:
    supabase = init_connection()
except Exception as exc:
    st.error(f"无法连接游戏服务，请检查 Supabase 配置：{exc}")
    st.stop()


def enter_room(room_code, name, player_num):
    st.session_state.room_code = room_code
    st.session_state.player_name = name
    st.session_state.player_num = player_num
    st.session_state.pop("_room_snapshot", None)
    clear_selection(st.session_state)
    st.rerun()


def show_login():
    st.markdown('<div class="eyebrow">KCD · ONLINE FARKLE</div>', unsafe_allow_html=True)
    st.title("🎲 骰子对决")
    st.markdown('<p class="intro">创建房间，邀请朋友，轮流掷骰冲向目标分数。</p>', unsafe_allow_html=True)

    with st.form("room_form"):
        room = st.text_input("房间码", placeholder="例如 KCD888", max_chars=20).strip().upper()
        name = st.text_input("你的名字", placeholder="输入玩家昵称", max_chars=24).strip()
        target_score = st.number_input("目标分数（创建房间时使用）", min_value=1000, max_value=50000, value=10000, step=1000)
        create_col, join_col = st.columns(2, gap="small")
        create_clicked = create_col.form_submit_button("创建房间", type="primary", use_container_width=True)
        join_clicked = join_col.form_submit_button("加入房间", use_container_width=True)

    if not (create_clicked or join_clicked):
        return
    if not room or not name:
        st.warning("请填写房间码和昵称。")
        return
    try:
        existing = get_room(supabase, room)
        if not existing and join_clicked:
            st.error("找不到这个房间，请确认房间码。")
            return
        if not existing:
            create_room(supabase, room, name, int(target_score))
            enter_room(room, name, 1)
            return
        if existing.get("player1") == name:
            player_num = 1
        elif existing.get("player2") == name:
            player_num = 2
        elif not existing.get("player2"):
            join_room(supabase, room, name)
            player_num = 2
        else:
            st.error("房间已满，请换一个房间码。")
            return
        enter_room(room, name, player_num)
    except Exception as exc:
        st.error(f"进入房间失败，请重试：{exc}")


def score_card(name, score, target, active):
    safe_name = escape(str(name))
    progress = min(100, max(0, score / target * 100))
    active_class = " active" if active else ""
    return f"""<div class="score-card{active_class}">
      <div class="score-name">{safe_name}</div>
      <div class="score-value">{score:,}</div>
      <div class="score-track"><div class="score-progress" style="width:{progress:.1f}%"></div></div>
    </div>"""


def save_action(room_data, scores, turn_state):
    """Persist once, then show the new state without another immediate read."""
    saved = update_game_state(
        supabase,
        st.session_state.room_code,
        scores,
        turn_state,
        room_data.get("last_action"),
    )
    st.session_state._room_snapshot = saved
    st.session_state._room_poll_tick = 0
    clear_selection(st.session_state)


def reload_after_conflict():
    """Show the latest turn when another session saved first."""
    try:
        st.session_state._room_snapshot = get_room(supabase, st.session_state.room_code)
        st.session_state._room_poll_tick = 0
        clear_selection(st.session_state)
        st.session_state.game_notice = "房间状态已在另一窗口更新，已为你重新载入。"
    except Exception as exc:
        st.error(f"房间状态已变化，但重新载入失败：{exc}")
        return
    st.rerun()


def show_game(room_data):
    turn = room_data["turn_state"]
    scores = room_data["scores"]
    player_num = st.session_state.player_num
    current_player = turn["current_player"]
    is_my_turn = current_player == player_num
    game_over = turn.get("game_over", False)
    player1 = room_data["player1"]
    player2 = room_data.get("player2")
    target = max(1, turn.get("target_score", 10000))

    top_col, leave_col = st.columns([4, 1])
    with top_col:
        st.markdown('<div class="eyebrow">KCD · 骰子对决</div>', unsafe_allow_html=True)
        st.title("游戏进行中" if not game_over else "本局结束")
        st.markdown(f'<div class="room-id">房间码 · {escape(st.session_state.room_code)}</div>', unsafe_allow_html=True)
    if leave_col.button("退出", use_container_width=True):
        st.session_state.room_code = ""
        st.session_state.pop("_room_snapshot", None)
        clear_selection(st.session_state)
        st.rerun()

    st.markdown(
        '<div class="score-grid">'
        + score_card(player1, scores["p1"], target, current_player == 1 and not game_over)
        + score_card(player2 or "等待玩家加入", scores["p2"], target, current_player == 2 and not game_over)
        + '</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"目标分数 {target:,} · 两人轮流掷骰，选出可得分的骰子")

    if game_over:
        winner_name = player1 if turn.get("winner") == 1 else player2
        st.success(f"🏆 {winner_name} 获胜！")
        return
    if not player2:
        title, detail = "等待另一位玩家", "将房间码发给朋友，加入后即可开始。"
    elif is_my_turn:
        title, detail = "轮到你了", "选中有分的骰子，然后继续掷骰或存分。"
    else:
        title, detail = f"等待 {player1 if current_player == 1 else player2}", "对方行动后，棋盘会自动更新。"
    st.markdown(
        f'<div class="turn-panel"><div class="turn-title">{escape(title)}</div>'
        f'<div class="turn-detail">{escape(detail)}</div></div>',
        unsafe_allow_html=True,
    )

    notice = st.session_state.pop("game_notice", None)
    if notice:
        st.warning(notice)

    dice = turn.get("current_dice", [])
    confirmed = turn.get("previously_locked", [])
    selected = selection_for(st.session_state, room_data)
    st.subheader("本轮骰子")
    if dice:
        with st.container(key="dice_grid"):
            for start in range(0, len(dice), 3):
                columns = st.columns(3, gap="small")
                for index in range(start, min(start + 3, len(dice))):
                    value = dice[index]
                    fixed = index < len(confirmed) and confirmed[index]
                    label = f"{value} 点 · {'已保留' if fixed else '已选' if selected[index] else '选择'}"
                    if columns[index - start].button(
                        label,
                        key=f"die_{index}",
                        type="primary" if selected[index] else "secondary",
                        disabled=not is_my_turn or fixed or not player2,
                        use_container_width=True,
                    ):
                        selected[index] = not selected[index]
                        st.rerun()
    else:
        st.info("点击“掷骰子”开始本轮。" if is_my_turn else "等待对方掷骰。")

    temporary = selection_score(dice, selected, confirmed)
    round_score = turn.get("round_score", 0)
    st.markdown(
        f'<div class="score-preview">本轮已得 <b>{round_score:,}</b>　·　当前选择 '
        f'<b>+{temporary:,}</b>　·　可存入 <b>{round_score + temporary:,}</b></div>',
        unsafe_allow_html=True,
    )
    if not is_my_turn or not player2:
        return

    with st.container(key="actions"):
        roll_col, bank_col = st.columns(2, gap="small")
        roll_clicked = roll_col.button(
            "🎲 掷骰子" if not dice else "🎲 继续掷骰",
            type="primary",
            disabled=bool(dice) and temporary == 0,
            use_container_width=True,
        )
        bank_clicked = bank_col.button(
            f"存入 {round_score + temporary:,} 分",
            disabled=not dice or round_score + temporary == 0,
            use_container_width=True,
        )

    if roll_clicked:
        count = 6 if not dice or all(selected) else len(dice) - sum(selected)
        next_dice = roll_dice(count)
        try:
            next_turn, farkled = roll_turn(turn, selected, next_dice)
            save_action(room_data, scores, next_turn)
        except ConcurrentUpdateError:
            reload_after_conflict()
            return
        except Exception as exc:
            st.error(f"掷骰结果未保存，请重试：{exc}")
            return
        if farkled:
            st.session_state.game_notice = "爆骰！本轮分数清零，轮到对方。"
        st.rerun()

    if bank_clicked:
        try:
            next_scores, next_turn = bank_turn(scores, turn, selected)
            save_action(room_data, next_scores, next_turn)
        except ConcurrentUpdateError:
            reload_after_conflict()
            return
        except Exception as exc:
            st.error(f"分数未保存，请重试：{exc}")
            return
        st.rerun()


if not st.session_state.get("room_code"):
    show_login()
else:
    previous = st.session_state.get("_room_snapshot")
    should_poll = should_poll_room(previous, st.session_state.player_num)
    poll_tick = st_autorefresh(interval=2000, key="room_poll") if should_poll else None
    room_data, fetch_error = load_room_snapshot(
        st.session_state,
        st.session_state.room_code,
        poll_tick,
        lambda code: get_room(supabase, code),
    )
    if fetch_error:
        st.warning(f"连接暂时中断，显示上次游戏状态：{fetch_error}")
    if room_data:
        show_game(room_data)
    else:
        st.error("房间不存在或暂时无法读取。")
        if st.button("返回房间入口"):
            st.session_state.room_code = ""
            st.rerun()

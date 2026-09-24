# Faster Mobile UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce game interaction latency and make the KCD Streamlit interface clear on mobile.

**Architecture:** Keep Streamlit and Supabase. Move turn transitions into testable pure functions. Keep dice selection and a room snapshot in Streamlit session state; synchronize only when an action is committed or a poll tick changes.

**Tech Stack:** Python, Streamlit, Supabase, unittest.

---

### Task 1: Turn transitions

**Files:** Create `turn_actions.py`; create `tests/test_turn_actions.py`.

1. Write failing tests for selection validation, roll, Farkle, hot dice, and banking.
2. Run `python -m unittest discover -s tests -v` and confirm the new tests fail for missing behavior.
3. Implement pure state transitions while preserving the current room JSON shape.
4. Run the tests again and confirm they pass.
5. Commit the change.

### Task 2: Local selection and fewer remote calls

**Files:** Modify `app.py`; create `tests/test_app_state.py` as needed.

1. Write failing tests for selection reset on new roll and unchanged poll tick reusing the cached room.
2. Run the focused tests and confirm the expected failure.
3. Implement session-state snapshot and local dice selection; write once per roll or bank.
4. Remove blocking sleeps and GIF flip reruns.
5. Run the tests and app import check, then commit.

### Task 3: Responsive visual design

**Files:** Modify `app.py`; optionally add `.streamlit/config.toml`.

1. Define page theme and custom CSS for responsive score cards, dice, and actions.
2. Reorder the screen into score, turn, dice, and actions with Chinese labels.
3. Check desktop and narrow viewport rendering in a browser.
4. Run the full test suite and commit.

### Task 4: Final verification and delivery

**Files:** Update `requirements.txt` if a minimum Streamlit version is required; update docs if needed.

1. Run tests, compile checks, and a local smoke check with stub data.
2. Review the diff and verify the database update and polling paths.
3. Push the branch and open a pull request.

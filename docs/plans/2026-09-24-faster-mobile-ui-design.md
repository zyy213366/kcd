# Faster, clearer KCD game UI

## Goal

Make the existing two-player Streamlit Farkle game feel responsive and legible on a phone without changing its rules or room data format.

## Approach

Keep Streamlit and Supabase. The game screen uses a local room snapshot between polling ticks. Selecting dice updates only local session state and previews the score immediately. Rolling, banking, and a Farkle each produce one database write. A 2-second poll remains for remote turns and the waiting room; local selections do not cause a network read. Remove blocking sleeps and GIF playback. Render dice as clear, selectable buttons.

The interface puts room identity and score progress first, then the current turn, dice selection, score preview, and actions. Use a light neutral background, restrained green accents, large tap targets, short Chinese labels, and a layout that works at narrow widths. Show waiting, network failure, Farkle, and game-over states in the same hierarchy.

## Data and error handling

The existing `scores` and `turn_state` JSON remain compatible. Dice selection is transient session state, reset when a new roll or turn arrives. Fetching a room updates a session snapshot on the first render and each poll tick. A failed action keeps the current screen and shows an error; it does not silently claim success. A failed poll keeps the previous snapshot and displays a retry message.

## Verification

Add tests for pure turn transitions and selection scoring, including hot dice, Farkle, and banking. Verify the app imports and renders with a fake in-memory room service, then manually check desktop and narrow layouts. Compare database calls and intentional waits before and after the change.

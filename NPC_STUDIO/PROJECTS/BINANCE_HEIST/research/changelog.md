# Changelog

Every phase appends a 3-line status. Fact changes after Nov 3, 2026 are listed under Phase 1.

## Phase 0 — Setup · 2026-11-03
- Built inside NPC_STUDIO (PROJECTS/BINANCE_HEIST + shared RENDER_ENGINE): Node 22, Python 3.11 venv, ffmpeg 6.1; all @remotion/* pinned to 4.0.537 (+ zod 4.5.4); 1920×1080 still render verified.
- Narration locked to NPC_VOICE_V1 only (no ElevenLabs/Kokoro). BLOCKER for Phase 2: reference audio absent in this container and profile reports ready_for_cloning=false (1.9 s of speech, needs ≥ 8 s).
- Skipped: Remotion Agent Skills install (blocked by session permissions), AI-influencer and TikTok/auto-publish features (out of scope). No .env → stock/data fallbacks apply.

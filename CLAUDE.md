# Project notes for Claude

This repo produces **SPACE SECRETS** space-science videos (TikTok/Shorts in `shorts/`, plus long-form YouTube).

- **Every new Space Secrets TikTok/Short must follow `SPACE_SECRETS_RETENTION_SYSTEM.md`** (Viral Retention System V3):
  an unmissable first frame, three hooks before editing, story-driven retention beats, a quality gate on the first 3 s,
  and the deliverables `FINAL_VIDEO.mp4`, `THREE_HOOK_OPTIONS.txt`, `FINAL_SCRIPT.txt` and `RETENTION_QA_REPORT.txt`.
- Don't re-edit already published videos unless asked; the rules apply to new incoming videos.
- Brand: Inter Black captions, white with yellow (#FFD400) emphasis and a black stroke; Kokoro voice `am_puck`; mix to -14 LUFS.
- YouTube agent skills (MIT, github.com/Jakeschincariol/youtube-agent-skill) are installed in `.claude/skills/yt-*`.
  At session start, copy `.claude/youtube/voice.md` to `~/.claude/youtube/voice.md` (the skills read it there).
  **Every new video runs the full agent pipeline:**
  1. `/yt-script` writes the script: 5 hooks from the 21 formulas, scored with hookscore.py; the opening line must score
     ≥72 (STRONG) and pass a fact check (the /yt-audit fix: put the viewer and a number at stake). If the user supplies a
     script, keep its body but run the hook through the same scoring and report it.
  2. `/yt-package` gives title + thumbnail text as one pairing (≤40 characters for mobile, ≤3 thumbnail words, no repeats).
  3. Production per SPACE_SECRETS_RETENTION_SYSTEM.md (frame-0 event, gate on the first 3 s).
  4. `/yt-edit` runs deadair.py on the narration SRT; `/yt-chapters` covers long-form; `/yt-seo` writes the description, tags and queries.
  5. `/yt-shorts` cuts Shorts from any long-form video.
  6. After posting: `/yt-retention` (retention CSV), `/yt-comment` (comments), `/yt-viral` (competitor lists),
     `/yt-plan` (hours and best day), `/yt-audit` (monthly). These need user data; never invent numbers.

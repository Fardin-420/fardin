# Project notes for Claude

This repo produces **SPACE SECRETS** space-science videos (TikTok/Shorts in `shorts/`, plus long-form YouTube).

- **Every new Space Secrets TikTok/Short must follow `SPACE_SECRETS_RETENTION_SYSTEM.md`** (Viral Retention System V3):
  an unmissable first frame, three hooks before editing, story-driven retention beats, a quality gate on the first 3 s,
  and the deliverables `FINAL_VIDEO.mp4`, `THREE_HOOK_OPTIONS.txt`, `FINAL_SCRIPT.txt` and `RETENTION_QA_REPORT.txt`.
- Don't re-edit already published videos unless asked; the rules apply to new incoming videos.
- Brand: Inter Black captions, white with yellow (#FFD400) emphasis and a black stroke; Kokoro voice `am_puck`; mix to -14 LUFS.
- YouTube agent skills (MIT, from github.com/Jakeschincariol/youtube-agent-skill) are installed in `.claude/skills/yt-*`.
  For each new video: score hooks with `python3 .claude/skills/yt-script/hookscore.py --hook "..."` (a heuristic, not a
  prediction), lint title + thumbnail together with `python3 .claude/skills/yt-package/title.py --title "..." --thumb "..."`,
  and use `/yt-retention` on any retention CSV the user sends.

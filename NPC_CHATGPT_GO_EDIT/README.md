# NPC — ChatGPT Go, 1 month via Rappi (edit package)

The user's real phone screen recording (two uploaded parts, 92 s), edited in code into a
37.7 s vertical tutorial. No timeline editor was used.

| Path | Contents |
|---|---|
| `FINAL/NPC_CHATGPT_GO_FINAL.mp4` | 1080x1920, H.264 + AAC, 30 fps |
| `PREVIEW/NPC_CHATGPT_GO_PREVIEW.mp4` | 540x960 preview of the same cut |
| `CAPTIONS/NPC_CHATGPT_GO_CAPTIONS.srt` | step captions (the recording has no speech) |
| `THUMBNAIL/NPC_CHATGPT_GO_THUMBNAIL.png` | 1080x1920 cover from the real result frame |
| `NPC_EDIT_REPORT.txt` | durations, cuts, speed ramps, zooms, privacy results, QC |
| `EDITING_PROJECT/` | all code + `edl.json` (edit decision list) / `edl_resolved.json` |
| `PRIVACY_MASKS/masks.json` | per-frame mask rectangles (geometry only) |
| `ANALYSIS/qc_final.json` | measured QC of the final file |

## Rebuild

```bash
cd NPC_CHATGPT_GO_EDIT/EDITING_PROJECT
SRC=/private/source.mp4; PRIV=/private/dir   # joined recording (kept private) + OCR scratch
python ocr_scan.py $SRC $PRIV/ocr --only <(python -c "from timeline import Timeline;import json;print(json.dumps(Timeline().used_source_frames(0)))")
python privacy.py $PRIV/ocr $PRIV
python resolve_edl.py $SRC && python audio.py ../AUDIO/NPC_CHATGPT_GO_MIX.wav
python render.py $SRC --out ../PREVIEW/.v.mp4 && ffmpeg -i ../PREVIEW/.v.mp4 -i ../AUDIO/NPC_CHATGPT_GO_MIX.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest ../FINAL/NPC_CHATGPT_GO_FINAL.mp4
python qc.py ../FINAL/NPC_CHATGPT_GO_FINAL.mp4 $PRIV ../ANALYSIS/qc_final.json
python make_srt.py && python thumbnail.py $SRC && python report.py
```

Shared libraries: `NPC_STUDIO/SOUND_ENGINE` (sound primitives) and `NPC_STUDIO/BRAND/fonts`.

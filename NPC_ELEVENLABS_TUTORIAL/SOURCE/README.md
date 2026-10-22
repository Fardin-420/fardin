# SOURCE

The original screen recording is **not stored in this repository**: it shows private data
(account email, birthday, profile answers) before masking, and this repository is public.

| Property | Value |
|---|---|
| File | `lv_0_20261022212502.mp4` (uploaded to the editing session) |
| Video | H.264, 882 x 1920 portrait, 30 fps, 122.63 s (3679 frames) |
| Audio | 44.1 kHz stereo track containing digital silence (-91 dBFS throughout): no narration |

The source file is only ever read. Every edit is reproduced from it by `EDITING_PROJECT/build.py`.
Keep the original in a private location and pass its path to the build:

```bash
cd NPC_ELEVENLABS_TUTORIAL/EDITING_PROJECT
python build.py /path/to/lv_0_20261022212502.mp4 /private/scratch/dir
```

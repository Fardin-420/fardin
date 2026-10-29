# PERSIAN_TWO_DIALECTS_EN — Iranian vs Afghan Persian (English)

English remake of a 70-second Persian explainer about Iranian Farsi and Afghan Dari.
It was rebuilt from code, not dubbed: new English narration, the same scenes redrawn
as SVG, and on-screen labels that keep the original Persian words with transliterations.

```bash
cd NPC_STUDIO
pip install kokoro-onnx soundfile scipy pyloudnorm    # + Kokoro model files, see VOICE_ENGINE/guest_voice.py
python produce_explainer.py PROJECTS/PERSIAN_TWO_DIALECTS_EN           # -> final/PERSIAN_TWO_DIALECTS_EN.mp4
python produce_explainer.py PROJECTS/PERSIAN_TWO_DIALECTS_EN --stills  # -> previews/contact_sheet.jpg
```

| Scene | Narration (EN) | Persian on screen |
|---|---|---|
| intro | Iranians and Afghans both speak Persian. So what's the difference? | — |
| tomato | Afghans never eat tomatoes… because over there, they call it a Roman eggplant! | گوجه‌فرنگی / بادنجان رومی |
| words | sib-zamini / kachalu · car: motar · ice cream: shir-yakh | سیب‌زمینی / کچالو · ماشین / موتر · بستنی / شیریخ |
| maqbul | If an Afghan calls you maqbul… it means you're good-looking! | مقبول |
| greet | khaste nabashi / mande nabashi · merci / zinda bashi | خسته نباشی / مانده نباشی · مرسی / زنده باشی |
| taarof | Cliché 1: Iranians are champions of taarof… | تعارف · بفرمایید |
| hospitality | Cliché 2: a five-minute tea becomes three rounds of Kabuli pulao | قابلی پلو |
| slipper | Cliché 3: the moms' secret weapon, the slipper | دمپایی |
| shir | shīr = lion and milk in Iran; Afghans say shēr for the lion, the older pronunciation | شیر · حافظ · مولانا |
| rumi | Who does Rumi belong to? Iran, Afghanistan (Balkh), Turkey (Konya) | — |
| outro | One language, one table. Only the tomato goes by a different name. | — |

* `source/script.json`: lines, the spoken spelling of Persian words (`say`), caption highlights, scene labels and cue → word bindings.
* `source/timeline.json`: built from the measured narration. Every animation and sound reads its timing from this file.
* Voice: Kokoro-82M, a fixed `am_michael`/`am_puck` blend. It is a stand-in narrator, not NPC_VOICE_V1.
* Map outlines: Natural Earth via `world-atlas` (public domain), projected by `RENDER_ENGINE/flat2d/build_geo.mjs`.

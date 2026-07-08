YouTube Curation Utility

This script fetches metadata using `yt-dlp` and filters videos according to curation rules.

Quick start

1. Install:

```bash
pip install -r yt_curation/requirements.txt
# optional: if using playwright rendering for tricky pages
python -m playwright install
```

2. Prepare a `source_urls.txt` with one URL per line (example file not provided).

3. Run:

```bash
python yt_curation/filter_videos.py \
  --source source_urls.txt \
  --min-duration-seconds 300 \
  --max-duration-seconds 2400 \
  -r python -r tutorial \
  -f "live" -f "short" \
  --limit 20 \
  --output output.json
```

Output

- `output.json` will contain a JSON object: {"urls": [ ... ]}

Notes

- The script calls the `yt-dlp` CLI (`--dump-json`) to get metadata; ensure `yt-dlp` is installed and in your PATH.
- If the site blocks requests, try running `yt-dlp` with cookies or use a headful browser to authenticate, then re-run the script.

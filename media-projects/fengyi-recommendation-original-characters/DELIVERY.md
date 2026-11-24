# Video loading and download update

The approved historical Bologna recommendation keeps its original artwork, dialogue, duration, audio and native watermark. Web playback uses a smaller H.264/AAC MP4, with the MP4 index first so playback can begin before the whole file downloads. The original remains available separately.

- Web file: 3,373,266 bytes; original: 8,023,125 bytes (58.0% reduction).
- Both are 1344 by 768 at 24 fps, duration 12.333344 seconds.
- Audio packet hash unchanged; complete decode of the delivery file succeeded.
- Web H.264 profile High, level 3.2. No image rescaling or new generation.
- The player does not autoplay. The user asked not to replay audio during this update.
- Download buttons use same-origin URLs and an attachment response, saving an ordinary MP4 suitable for importing into an editor.
- Owned alias domains resolve video and poster paths on the current origin to preserve the existing security policy.
- Media cache lifetime is one day; versioned filenames prevent old video content replacing new releases.

Validation: three Node URL tests, two backend video tests (draft privacy, publication, streaming variant, invalid input and legacy edits), JavaScript syntax check, Git whitespace check, FFmpeg full decode and audio identity. Static frame inspection preserved the selected two characters and background. No audible playback was performed.

Deployment uses publish_delivery.py with delivery-manifest.json and a pinned Git revision. Deployed file hashes are checked before any overwrite. Changed files and the catalogue are backed up; failure restores them. Only the web service restarts, and Caddy reloads. The data worker is not restarted.

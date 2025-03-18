import os
import re
import random
import string

from flask import Flask, request, render_template_string, send_from_directory, url_for, redirect
from moviepy.editor import VideoFileClip, concatenate_videoclips

app = Flask(__name__)

# Folders for storing files
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
OUTPUT_FOLDER = os.path.join(app.root_path, 'outputs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Your original scene holders
SCENE_HOLDERS = [
    [0.2, 0.2, 0.3, 0.7],
    [1.1, 0.9, 0.9, 0.9],
    [0.2, 0.2, 0.3, 0.7],
    [1.1, 0.9, 0.9, 0.9],
    [0.2, 0.2, 0.3, 0.7],
    [1.1, 0.9, 0.9, 0.9],
    [0.2, 0.2, 0.3, 0.7],
    [1.1, 0.9, 0.9, 0.9],
    [0.2, 0.2, 0.3, 0.7],
    [1.1, 0.9, 0.9, 0.9]
]


def sanitize_filename(filename, max_length=50):
    """Remove potentially unsafe characters and truncate for OS safety."""
    sanitized = re.sub(r'[^a-zA-Z0-9_\-\. ]', '', filename)
    return sanitized[:max_length]


def get_random_non_overlapping_clip(video, duration, used_intervals, min_gap=1):
    """
    Pick a random subclip of 'duration' that doesn't overlap
    existing intervals in used_intervals (list of (start, end)).
    """
    video_duration = video.duration
    max_start_time = video_duration - duration

    for _ in range(100):
        start_time = random.uniform(0, max_start_time)
        end_time = start_time + duration

        overlap = any(s < end_time and start_time < e for (s, e) in used_intervals)
        if not overlap:
            used_intervals.append((start_time, end_time + min_gap))
            return video.subclip(start_time, end_time)

    raise ValueError("Unable to find a suitable non-overlapping clip after 100 tries.")


def process_scene_holders(video, scene_holders):
    """
    Based on SCENE_HOLDERS: for each duration, pick a random subclip.
    Returns a list of subclip objects.
    """
    used_intervals = []
    selected_clips = []
    for durations_group in scene_holders:
        for duration in durations_group:
            try:
                subclip = get_random_non_overlapping_clip(video, duration, used_intervals)
                selected_clips.append(subclip)
            except ValueError as e:
                print(f"Warning: {e}")
                continue
    return selected_clips


def generate_scenes_highlight(video_path, desired_final_length, output_filename):
    """
    1. Loads the video.
    2. Extracts subclips per SCENE_HOLDERS.
    3. Concatenates them => highlight.
    4. Loop or truncate => exactly desired_final_length.
    5. Mutes. Saves to output_filename.
    """
    video = VideoFileClip(video_path)

    subclips = process_scene_holders(video, SCENE_HOLDERS)
    if not subclips:
        raise RuntimeError("No subclips were produced from SCENE_HOLDERS.")

    highlight_clip = concatenate_videoclips(subclips)
    highlight_len = highlight_clip.duration

    # Loop if shorter
    if highlight_len < desired_final_length:
        loops = [highlight_clip]
        total = highlight_len
        while total < desired_final_length:
            loops.append(highlight_clip)
            total += highlight_len
        highlight_clip = concatenate_videoclips(loops)

    # Truncate if longer
    if highlight_clip.duration > desired_final_length:
        highlight_clip = highlight_clip.subclip(0, desired_final_length)

    # Mute final
    highlight_clip = highlight_clip.without_audio()
    highlight_clip.write_videofile(output_filename, fps=30, codec='libx264', audio_codec='aac', verbose=False)

    return output_filename


# ----------------------------------------------------------------------
# HTML template with custom "iOS-like" styling
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>iOS-Style Scene Highlight Generator</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    /* 
      iOS-like styling:
      - system font stack 
      - gradient background 
      - card with rounded corners, shadow 
      - rounded inputs & button 
    */
    body {
      margin: 0;
      padding: 0;
      background: linear-gradient(135deg, #ece9e6, #ffffff);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell,
                   "Helvetica Neue", Helvetica, Arial, sans-serif;
    }
    .container {
      max-width: 500px;
      background: #fff;
      margin: 40px auto;
      padding: 20px;
      border-radius: 18px;
      box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    h2 {
      text-align: center;
      margin-bottom: 10px;
      font-weight: 600;
    }
    label {
      display: block;
      margin-bottom: 6px;
      margin-top: 20px;
      font-weight: 500;
    }
    input[type="file"],
    input[type="number"] {
      display: block;
      width: 100%%;
      font-size: 1rem;
      padding: 8px;
      border: 1px solid #ccc;
      border-radius: 10px;
      outline: none;
      transition: border-color 0.2s;
    }
    input[type="file"]:focus,
    input[type="number"]:focus {
      border-color: #007bff;
    }
    .note {
      font-size: 0.9em;
      color: #666;
      text-align: center;
    }
    button {
      margin-top: 30px;
      width: 100%%;
      font-size: 1.1rem;
      padding: 12px;
      background: #007aff;
      color: #fff;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      font-weight: 600;
      transition: background 0.3s;
    }
    button:hover {
      background: #005bb5;
    }
    .message {
      margin-top: 20px;
      text-align: center;
      font-weight: 500;
      line-height: 1.4;
    }
    .success { color: #28a745; }
    .error { color: #dc3545; }
    a {
      display: inline-block;
      margin-top: 10px;
      color: #007aff;
      text-decoration: none;
      font-weight: 500;
      transition: color 0.2s;
    }
    a:hover {
      color: #005bb5;
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>iOS-Style Scene Highlight Generator</h2>
    <p class="note">
      Upload a video and specify your final highlight length (in seconds).
      We'll build a highlight from random subclips defined by your <em>Scene Holders</em>.
    </p>
    <form method="POST" action="/process" enctype="multipart/form-data">
      <label>Select Video:</label>
      <input type="file" name="video_file" accept="video/*" required />

      <label>Desired Final Highlight Length (seconds):</label>
      <input type="number" step="0.1" name="final_length" value="45.0" required />

      <button type="submit">Generate Highlight</button>
    </form>

    {% if message %}
      <div class="message {{status_class}}">
        {{message}}
        {% if download_link %}
          <p><a href="{{download_link}}">Download your highlight</a></p>
        {% endif %}
      </div>
    {% endif %}
  </div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    """Display the iOS-style form."""
    return render_template_string(INDEX_HTML)


@app.route("/process", methods=["POST"])
def process():
    """
    1. Receive user-uploaded video.
    2. Desired final highlight length.
    3. Generate highlight with SCENE_HOLDERS logic.
    4. Let user download final with original name + '_highlights'.
    """
    try:
        # Retrieve the file
        video_file = request.files.get("video_file")
        if not video_file:
            raise ValueError("No video file uploaded.")

        # Get desired final length
        final_length_str = request.form.get("final_length")
        if not final_length_str:
            raise ValueError("No final length specified.")
        final_length = float(final_length_str)
        if final_length <= 0:
            raise ValueError("Final highlight length must be positive.")

        # Sanitize original filename
        original_filename = sanitize_filename(video_file.filename)
        if not original_filename:
            original_filename = "uploaded_video.mp4"

        # Save the uploaded file in uploads/ with random prefix to avoid collisions
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        saved_video_path = os.path.join(UPLOAD_FOLDER, f"{random_suffix}_{original_filename}")
        video_file.save(saved_video_path)

        # Build final output name with original name + '_highlights'
        base_name, ext = os.path.splitext(original_filename)
        final_name = f"{base_name}_highlights{ext}"
        output_path = os.path.join(OUTPUT_FOLDER, final_name)

        # Generate highlight
        generate_scenes_highlight(
            video_path=saved_video_path,
            desired_final_length=final_length,
            output_filename=output_path
        )

        # Provide link to download
        download_link = url_for("download_file", filename=final_name)
        message = f"Success! Your highlight is ready: {final_name}"
        status_class = "success"
        return render_template_string(
            INDEX_HTML,
            message=message,
            status_class=status_class,
            download_link=download_link
        )

    except Exception as e:
        message = f"Error: {str(e)}"
        status_class = "error"
        return render_template_string(
            INDEX_HTML,
            message=message,
            status_class=status_class,
            download_link=None
        )


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    """Serve the processed highlight from OUTPUT_FOLDER for download."""
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


# If you GET /process directly in your browser, you'll get a 405 error because this route only accepts POST.
# If you want to avoid that altogether, you could do something like redirect in GET.
# For example:
# @app.route("/process", methods=["GET"])
# def process_get():
#     return redirect(url_for("index"))  # If you ever do GET /process, go back to root.

if __name__ == "__main__":
    # Use host='0.0.0.0' so you can access from phone if on same network
    app.run(host="0.0.0.0", port=5000, debug=False)

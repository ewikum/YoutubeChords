import os
import gzip
import json
import hashlib
import requests

from PIL import Image
from mutagen.mp3 import MP3

import make_guitar_chart
import make_piano_chart
import make_subtitle_file

import subprocess

this_dir = os.path.dirname(os.path.abspath(__file__))

def save_combined_img(piano_file,guitar_file,out_file):
    full_width = 1080
    guitar_width = 748

    a = Image.open(piano_file).convert("RGBA")
    b = Image.open(guitar_file).convert("RGBA")

    # --- Resize to desired widths ---
    a_width, b_width = guitar_width, (full_width-guitar_width)
    a_height = int(a.height * (a_width / a.width))
    b_height = int(b.height * (b_width / b.width))

    a = a.resize((a_width, a_height), Image.LANCZOS)
    b = b.resize((b_width, b_height), Image.LANCZOS)

    # --- Determine final size ---
    final_width = a_width + b_width
    final_height = max(a_height, b_height)

    # --- Create transparent background ---
    combined = Image.new("RGBA", (final_width, final_height), (0, 0, 0, 0))

    # --- Paste both images, aligned at bottom ---
    combined.paste(a, (0, final_height - a_height), mask=a)
    combined.paste(b, (a_width, final_height - b_height), mask=b)


    # --- Reduce overall opacity to 90% ---
    alpha = combined.getchannel('A')
    alpha = alpha.point(lambda p: int(p * 0.9))  # scale alpha by 0.9
    combined.putalpha(alpha)

    # --- Save result ---
    combined.save(out_file)

def chord_img_file(c):
    return os.path.join(this_dir, "tmp", hashlib.md5(c.encode()).hexdigest() + "_combined.png")

def do(content_gz_file,source_gz_file,mp3_file=None):
    with gzip.open(content_gz_file, "rt", encoding="utf-8") as f:
        content = json.load(f)
    id = content["id"]

    output_file = os.path.join(this_dir, 'tmp',f"{id}.mp4")
    if os.path.exists(output_file):
        print(f"{output_file} is already there")
        return

    tonality_name = content["tonality_name"]
    # tuning = content["tuning"].split(" ")
    if content["tuning"] != "E A D G B E":
        print("Non standard tuning")
        return

    if mp3_file is None:
        mp3_file = os.path.join(this_dir, 'tmp',f"{id}_backing_track_mix.mp3")
        if not os.path.exists(mp3_file):
            response = requests.get(content["backing_track_mix"], stream=True)
            response.raise_for_status()
            with open(mp3_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
    audio_seconds = MP3(mp3_file).info.length


    ass_file = os.path.join(this_dir, 'tmp',f"{id}.ass")
    used_chords = make_subtitle_file.write_ass_file(source_gz_file,tonality_name,ass_file,audio_seconds)

    # create missing chord charts
    need_chord_charts = [c for c in used_chords if not os.path.exists(chord_img_file(c))]
    piano_files = make_piano_chart.draw_chord_files(need_chord_charts,os.path.join(this_dir, "tmp"))
    guitar_files = make_guitar_chart.draw_chord_files(need_chord_charts,os.path.join(this_dir, "tmp"))
    for c_i in range(len(need_chord_charts)):
        save_combined_img(piano_files[c_i],guitar_files[c_i],chord_img_file(need_chord_charts[c_i]))
        os.remove(piano_files[c_i])
        os.remove(guitar_files[c_i])


    audio_start_at = 3
    video_seconds = audio_start_at + audio_seconds

    ffmpeg_chord_img_inputs = ""
    ffmpeg_overlays = ""
    i_i = 2
    for chord, times in used_chords.items():
        ffmpeg_chord_img_inputs += f" -i '{chord_img_file(chord)}'"
        ffmpeg_overlays += f"{'[base]' if i_i == 2 else f'[vo{i_i-1}]'}[{i_i}:v]overlay=W-w:H-h:enable='{'+'.join([f"between(t,{t["start_t"]},{t["end_t"]})" for t in times])}':alpha=0.9[vo{i_i}];"
        i_i += 1


    subprocess.run(f"ffmpeg -f lavfi -i color=c=#111318:s=1080x1920:d={video_seconds} -i '{mp3_file}' {ffmpeg_chord_img_inputs} -filter_complex \"[1:a]adelay={audio_start_at*1000}|{audio_start_at*1000}[a];[0:v]ass='{ass_file}'[base];{ffmpeg_overlays}\" -map \"[vo{i_i-1}]\" -map \"[a]\" -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -y '{output_file}'", shell=True, check=True)

    print(f"{output_file} saved.")


do("./tmp/contents_1910943.json.gz","./tmp/sources_1910943.json.gz","test_h.mp3")













# ffmpeg -f lavfi -i color=c=#111318:s=1080x1920:d=600 \
# -i h.mp3 \
# -i combined.png \
# -filter_complex "[1:a]adelay=3000|3000[a];[2:v]format=rgba,colorchannelmixer=aa=0.9[overlay];[0:v]ass=chords.ass[base];[base][overlay]overlay=W-w:H-h:enable='between(t,5,15)'[vout]" \
# -map "[vout]" -map "[a]" \
# -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest -y ass_test6.mp4






# import sqlite3
# import os
# import re
# import glob

# from PIL import Image, ImageDraw, ImageFont
# import textwrap

# import subprocess

# import gdown

# import upload


# def draw_text_centered(img_path, text, font_path, rect, output_path, fill=(84,17,6)):
#     img = Image.open(img_path)
#     draw = ImageDraw.Draw(img)

#     rect_x, rect_y, rect_w, rect_h = rect
#     max_font_size = 100
#     font = ImageFont.truetype(font_path, max_font_size)

#     # Split into blocks by manual \n first
#     paragraphs = text.split("\n")

#     # Wrap each block individually
#     wrapped_lines = []
#     for para in paragraphs:
#         wrapped_lines.extend(textwrap.wrap(para, width=20))  # auto-wrap
#         wrapped_lines.append("")  # add blank line between paragraphs

#     if wrapped_lines and wrapped_lines[-1] == "":
#         wrapped_lines.pop()  # remove trailing blank line

#     # Measure function
#     def measure(text_line, font):
#         bbox = draw.textbbox((0,0), text_line, font=font)
#         width = bbox[2] - bbox[0]
#         height = bbox[3] - bbox[1]
#         return width, height

#     # Measure wrapped text block
#     line_sizes = [measure(line, font) for line in wrapped_lines]
#     text_w = max((w for w,h in line_sizes), default=0)
#     text_h = sum(h for w,h in line_sizes)

#     # Scale down if needed
#     while (text_w > rect_w or text_h > rect_h) and max_font_size > 10:
#         max_font_size -= 2
#         font = ImageFont.truetype(font_path, max_font_size)
#         line_sizes = [measure(line, font) for line in wrapped_lines]
#         text_w = max((w for w,h in line_sizes), default=0)
#         text_h = sum(h for w,h in line_sizes)

#     # Start Y to center vertically
#     y = rect_y + (rect_h - text_h) / 2

#     for line in wrapped_lines:
#         line_w, line_h = measure(line, font)
#         x = rect_x + (rect_w - line_w) / 2
#         draw.text((x, y), line, font=font, fill=fill)
#         y += line_h

#     img.save(output_path)


# # Usage
# # draw_text_centered(
# #     "podi_new_back.png",
# #     "පොඩි මල්ලිගෙ \nආදර සිංදු",
# #     "UN-Gurulugomi.ttf",
# #     (349, 32, 486, 221),  # rectangle
# #     "output.png"
# # )



# def get_video_length(path):
#     result = subprocess.run(
#         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
#          "-of", "default=noprint_wrappers=1:nokey=1", path],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#         text=True
#     )
#     return float(result.stdout.strip())


# def to_seconds_or_none(x):
#     x = x.strip()
#     if not x:
#         return None

#     parts = x.split(":")
#     try:
#         # Convert each part to int
#         parts = [int(p) for p in parts]
#     except ValueError:
#         return None  # invalid input

#     if len(parts) == 1:
#         # seconds only
#         return parts[0]
#     elif len(parts) == 2:
#         # MM:SS
#         minutes, seconds = parts
#         return minutes * 60 + seconds
#     elif len(parts) == 3:
#         # HH:MM:SS
#         hours, minutes, seconds = parts
#         return hours * 3600 + minutes * 60 + seconds
#     else:
#         return None  # invalid format





# # ffmpeg -i rc120111024.flv -i rc220111024.flv -i rc320111024.flv -i rc420111024.flv -loop 1 -i output.png \
# # -filter_complex "[0:a][1:a][2:a][3:a]concat=n=4:v=0:a=1[a]; \
# # [a]rubberband=tempo=1.02:pitch=1.02, equalizer=f=100:t=q:w=2:g=5[outa]" \
# # -map 4:v -map "[outa]" \
# # -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
# # -shortest output.mp4


# # ;


# conn = sqlite3.connect("chooty.db")
# cursor = conn.cursor()

# cursor.execute("SELECT id,song,youtube_title,my_yt_base,my_yt_part,my_yt_title_sl,my_yt_title_en,g_backup,my_yt_trim_s,my_yt_trim_e FROM songs WHERE my_yt_base = (SELECT my_yt_base FROM songs WHERE my_yt_youtube IS NULL LIMIT 1) ORDER BY my_yt_part")
# rows = cursor.fetchall()


# base_id = 0
# caption = ''
# title_en = ''
# title_sl = ''

# ffmpeg_files_str = ''
# ffmpeg_filter_complex_str = ''

# tempo_change = 1.1
# audio_duration = 0
# is_short = False

# current_i = 0
# for row in rows:
#     id,song,youtube_title,my_yt_base,my_yt_part,my_yt_title_sl,my_yt_title_en,g_backup,my_yt_trim_s,my_yt_trim_e = row

#     filename = f"./chooty_files/{id}"

#     if id == my_yt_base:
#         base_id = id
#         caption = song
#         title_en = my_yt_title_en
#         title_sl = my_yt_title_sl

#     if not os.path.exists(filename):
#         print(f"{filename} does not exist")
#         if g_backup is None:
#             print(f"{id}: even g backup is NULL")
#             exit(1)

#         filename = f"/tmp/gdrive_chooty_files_{id}"
#         if not os.path.exists(filename):
#             print(f"downloading gdrive to {filename}")
#             url = f"https://drive.google.com/uc?id={g_backup}"
#             gdown.download(url, f"{filename}.gz", quiet=False)
#             subprocess.run(["gunzip", "-f", f"{filename}.gz"], check=True)
#         else:
#             print(f"dowloaded gdrive file {filename} will be used")


#     current_audio_duration = get_video_length(filename)

#     # # if only one file was used
#     # if current_i==0 and len(rows)==1:
#     if my_yt_trim_s is None and my_yt_trim_e is None:
#         subprocess.run(["open", "-a", "VLC", filename])
#         print(f"{song} video duration of {filename} is {current_audio_duration} seconds.. give me trim values")
#         user_input = input("Enter two numbers separated by a comma for trim seconds: ").strip()
#         parts = user_input.split(",", 1)
#         # Ensure always two elements
#         if len(parts) != 2:
#             print("Invalid, need exacty two values sepearated by a comma")
#             exit(1)
#         my_yt_trim_s = to_seconds_or_none(parts[0])
#         my_yt_trim_e = to_seconds_or_none(parts[1])
#         cursor.execute("UPDATE songs SET my_yt_trim_s = ?, my_yt_trim_e= ? WHERE id = ?",(my_yt_trim_s, my_yt_trim_e, id))
#         conn.commit()


#     if my_yt_trim_s is not None:
#         ffmpeg_files_str += f" -ss {my_yt_trim_s}"

#     if my_yt_trim_e is not None:
#         ffmpeg_files_str += f" -to {my_yt_trim_e}"

#     ffmpeg_files_str += f" -i {filename}"
#     ffmpeg_filter_complex_str += f"[{current_i}:a]"

#     if my_yt_trim_e is not None:
#         current_audio_duration = my_yt_trim_e

#     if my_yt_trim_s is not None:
#         current_audio_duration -= my_yt_trim_s

#     audio_duration += current_audio_duration

#     current_i += 1

# audio_duration = round(audio_duration/tempo_change,6)

# is_short = audio_duration<60
# print(f"video duration is {audio_duration} seconds, is_short={is_short}")

# temp_img_file = f"/tmp/{base_id}.png"
# temp_mp4_file = f"/tmp/{base_id}.mp4"

# if title_en == '' or title_en is None:
#     title_en = re.sub(r'[\s-]*Part (\d+)$', '', caption)

# print(f"\n\033[92m {base_id}: {caption}\033[0m")

# title_en = input(f"Enter English Title: ({title_en}): ") or title_en
# title_count, = cursor.execute("SELECT COUNT(*) FROM songs WHERE id<? AND my_yt_title_en LIKE ?",(base_id,f"{title_en}%")).fetchone()
# if title_count>0:
#     print(f"{title_count} same title found before")
#     exit(1)
# cursor.execute("UPDATE songs SET my_yt_title_en = ? WHERE id = ?",(title_en, base_id))
# conn.commit()

# user_input = input(f"Enter Sinhala Title with line breaks ({title_sl}): ") or title_sl
# title_sl = user_input.replace("\\n", "\n").replace("|", "\n")
# cursor.execute("UPDATE songs SET my_yt_title_sl = ? WHERE id = ?",(title_sl, base_id))
# conn.commit()

# print(f"Creating IMG {temp_img_file}...")

# draw_text_centered(
#     "./podi_shorts.png" if is_short else "./podi_new_back.png",
#     title_sl,
#     "UN-Gurulugomi.ttf",
#     (10, 330, 250, 90) if is_short else (349, 32, 486, 221),  # rectangle
#     temp_img_file,
#     (254,254,254) if is_short else (84,17,6)
# )

# choice = (input("Do you want to verify the image? [y/N]: ")  or 'n').lower()
# if choice == "y" or choice == "|":
#     os.system(f"open {temp_img_file}")
#     choice = (input("OK? [Y/n]: ")  or 'y').lower()
#     if choice != "y" or choice == "|":
#         print("Aborting...")
#         os.remove(temp_img_file)
#         exit(1)

# print(f"Creating MP4 {temp_mp4_file}...")

# try:
#     if not os.path.exists(temp_mp4_file):

#         # Subscription animation stuff
#         sub_ani_real_duration=get_video_length("subscribe_animation_greenscreen.mp4")
#         start_after = 10
#         interval = 180

#         sub_ani_width = 764
#         sub_ani_x = -202
#         sub_ani_y = 107

#         if is_short:
#             sub_ani_width = 338
#             sub_ani_x = 18
#             sub_ani_y = 117

#         sub_animation_loop_video = f"./sub_loop_{sub_ani_width}_{interval}.tmp"
#         if not os.path.exists(sub_animation_loop_video):
#             subprocess.run(f"ffmpeg -f lavfi -i color=c=0x15CC00:s={sub_ani_width}x{sub_ani_width}:d={interval}:rate=30 -i subscribe_animation_greenscreen.mp4 -filter_complex \"[0:v] chromakey=0x15CC00:0.1:0.2,format=yuva444p[v0];[1:v] chromakey=0x15CC00:0.1:0.2,scale={sub_ani_width}:-1,format=yuva444p [v1];[v1][v0] overlay=0:0 [vout];[1:a] apad [aout];\" -t {interval} -map \"[vout]\" -map \"[aout]\" -c:v qtrle -c:a aac -f mov {sub_animation_loop_video}", shell=True, check=True)

#         ffmpeg_output_part = temp_mp4_file

#         if not is_short and audio_duration>start_after:

#             number_of_sub_ani = (audio_duration-start_after+3)//interval # allow 3 seconds to overflow for last sub ani
#             sub_ani_full_duration = start_after + (number_of_sub_ani*interval) + sub_ani_real_duration
#             audio_duration = max(audio_duration,sub_ani_full_duration)

#             # pipe output to add subscription animations to the video and then output to real file
#             ffmpeg_output_part = f"-f matroska - | ffmpeg -y -i - -itsoffset {start_after} -stream_loop {number_of_sub_ani} -i {sub_animation_loop_video} -filter_complex \"[0:v][1:v] overlay={sub_ani_x}:{sub_ani_y} [vout];[1:a] adelay={start_after}000|{start_after}000 [sub_a];[0:a][sub_a] amix=inputs=2:normalize=0[aout];\" -t {audio_duration} -map \"[vout]\" -map \"[aout]\" -c:v libx264 -c:a aac {temp_mp4_file}"

#         subprocess.run(f"ffmpeg{ffmpeg_files_str} -loop 1 -i {temp_img_file} -filter_complex \"{ffmpeg_filter_complex_str}concat=n={current_i}:v=0:a=1[a]; [a]rubberband=tempo={tempo_change}:pitch=1.02, equalizer=f=100:t=q:w=2:g=5[outa]\" -map {current_i}:v -map \"[outa]\" -c:v libx264 -tune stillimage -c:a aac -b:a 192k -shortest {ffmpeg_output_part}", shell=True, check=True)

#     else:
#         print(f"{temp_mp4_file} already there, using it")

#     print(f"Uploading to youtube MP4 {temp_mp4_file}...")

#     yt_title = title_en
#     yt_title_sl_part = f"({re.sub(r"[\r\n\s]+", " ", title_sl)})"
#     if ((len(yt_title) + len(yt_title_sl_part) + 2) < 100):
#         yt_title = f"{title_en} {yt_title_sl_part}"
#     if (len(yt_title) < 72):
#         yt_title = f"Chooty Malli Podi Malli : {yt_title}"

#     video_id = upload.upload_video(
#         file_path=temp_mp4_file,
#         title=yt_title,
#         description=f"Chooty Malli Podi Malli Radio Drama : {title_en} {yt_title_sl_part}\nBest Old Classics, Old Hits, Most popular episodes ( Sinhala Comedy/ Joke Radio Program )\nOriginals only can be found here.\n\n#CMPM #chuttepodde #chooty_malli_podi_malli #old_is_gold #api_nodanna_live",
#         category="24",
#         keywords="api nodanna live,chooty malli,podi malli,radio drama, sinhala jokes, old, classics" + (", shorts" if is_short else ""),
#         privacy="public",
#         playlist_id="PL2XF--xX9A033qiqLwNUwd6YVigkdsbeB",
#         thumbnail=temp_img_file
#     )

#     cursor.execute("UPDATE songs SET my_yt_youtube = ? WHERE my_yt_base = ?",(video_id, base_id))
#     conn.commit()

#     os.remove(temp_img_file)
#     os.remove(temp_mp4_file)

#     # remove any temp files
#     for f in glob.glob("/tmp/gdrive_chooty_*"):
#         try:
#             os.remove(f)
#         except FileNotFoundError:
#             pass

#     print("DONE!")

# except subprocess.CalledProcessError:
#     print("ffmpeg failed! Aborting further steps.")






# # Usage



# #     print(f"\n\033[92m{id} : {song}, {link}\033[0m")

# # ffmpeg -i rc120111024.flv -i rc220111024.flv -i rc320111024.flv -i rc420111024.flv -loop 1 -i output.png \
# # -filter_complex "[0:a][1:a][2:a][3:a]concat=n=4:v=0:a=1[a]; \
# # [a]rubberband=tempo=1.02:pitch=1.02, equalizer=f=100:t=q:w=2:g=5[outa]" \
# # -map 4:v -map "[outa]" \
# # -c:v libx264 -tune stillimage -c:a aac -b:a 192k \
# # -shortest output.mp4

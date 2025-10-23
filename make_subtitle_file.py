import re
import json
import gzip

ticks_per_beat = 960
audio_start_at = 3

def ticks_to_seconds(t,tempo):
    return (t / ticks_per_beat) * (60 / tempo)

def fmt(t,precision=3):
    total_seconds = int(t)
    decimals = int(round((t - total_seconds) * (10**precision)))
    s = total_seconds % 60
    m = (total_seconds // 60) % 60
    h = total_seconds // 3600
    return f"{h}:{m:02}:{s:02}.{decimals:0{precision}d}"

def is_chord_line(line):
    if not line.strip():
        return False
    line = line.replace("|", " ")
    pattern = r'^(?:\s*(?:\[ch.*?\].*?\[/ch\])\s*)*$'
    return bool(re.fullmatch(pattern, line.replace("[tab]", "").replace("[/tab]", "")))

def normalDialog(line,start_tf,end_tf,y_start,y_end,f_in=0,f_out=0):
    line = line.replace("[tab]", "").replace("[/tab]", "")
    style = "Heading" if bool(re.search(r"^\[[^]]+\]$", line)) else ("Chords" if is_chord_line(line) else "Lyrics")
    line = re.sub(r'\[syllable[^\]]*\](.*?)\[/syllable\]', r'\1', line)
    line = re.sub(r'\[ch[^\]]*\](.*?)\[/ch\]', r'\1', line)
    line = line.replace(" ", "\\h") # to keep leading spaces on .ass

    return f"Dialogue: 0,{start_tf},{end_tf},{style},,0,0,0,,{{\\move(20,{y_start},20,{y_end})\\fad({f_in},{f_out})}}{line}"

def highlightedChordDialog(line,start_tf,end_tf,y_start,y_end,h_chord_i):
    line = line.replace("[tab]", "").replace("[/tab]", "")

    count = [0]
    def replace_chord(match):
        text = match.group(1)
        count[0] += 1
        # Highlight the i-th chord
        if count[0] - 1 == h_chord_i:
            return '{\\c&H00101010&\\3c&H00FFE085&\\4c&H00FFE085&\\bord8&\\shad3&\\blur8}' + text + '{\\r}'
        else:
            return text

    line = re.sub(r'\[ch[^\]]*\](.*?)\[/ch\]', replace_chord, line.replace(" ", "\\h"))

    return f"Dialogue: 0,{start_tf},{end_tf},Chords,,0,0,0,,{{\\move(20,{y_start},20,{y_end})\\fad(0,0)}}{line}"


def shortenLines(lines,soft_width=40,hard_width=60):
    def split_chords_and_lyrics(chord_line,lyric_line, soft_width,hard_width):

        result = []
        if chord_line is None:
            current_chords = ''
        else:
            current_chords = re.sub(r'\[ch[^\]]*\](.*?)\[/ch\]', r'\1', chord_line.replace("[tab]", "").replace("[/tab]", "")).rstrip()
        current_lyrics = re.sub(r'\[ch[^\]]*\](.*?)\[/ch\]', r'\1', re.sub(r'\[syllable[^\]]*\](.*?)\[/syllable\]', r'\1', lyric_line).replace("[tab]", "").replace("[/tab]", "")).rstrip()

        if len(current_lyrics) <= soft_width:
            if chord_line is None:
                return  [lyric_line]
            return [chord_line, lyric_line]

        def find_break_point(current_lyrics: str, current_chords: str, break_str : str, width: int) -> int:
            pos = current_lyrics.rfind(break_str, 0, width)
            while pos != -1:
                # Check if at this position, chords have only whitespace for the same span
                if current_chords[pos:pos+1].strip() == '' and pos<len(current_lyrics)-1:
                    return pos  # Found valid match
                # Otherwise, look for the next (previous) double space
                pos = current_lyrics.rfind(break_str, 0, pos)
            return -1

        while len(current_lyrics) > soft_width:
            # find a good break point
            break_pos = -1
            for break_str in [". ", ", ", "; ","  ",".", ",", ";"]:
                break_pos = find_break_point(current_lyrics,current_chords,break_str,hard_width)
                if break_pos > -1:
                    break

            # if good breaking point was not found
            if break_pos == -1:
                # if its within hard_width, its acceptable
                if len(current_lyrics)<hard_width:
                    break
                else:
                    # find bad breaking pint to make it less than hard_width
                    break_pos = find_break_point(current_lyrics,current_chords," ",hard_width)
                    if break_pos == -1:
                        break_pos = hard_width


            # Split lines
            part_lyrics = current_lyrics[:break_pos+1].rstrip()
            part_chords = current_chords[:break_pos+1].rstrip()

            if part_chords.strip() != '':
                result.append(re.sub(r'(\S+)', r'[ch]\1[/ch]', part_chords))
            if part_lyrics.strip() != '':
                result.append(part_lyrics)

            # Remaining text
            current_lyrics = current_lyrics[break_pos+1:]
            current_chords = current_chords[break_pos+1:]

            strip_amount = len(current_lyrics) - len(current_lyrics.lstrip())
            if current_chords.strip() != '':
                strip_amount = min(strip_amount,len(current_chords) - len(current_chords.lstrip()))
                current_chords = current_chords[strip_amount:]
            current_lyrics = current_lyrics[strip_amount:]

        if current_chords.strip() != '':
            result.append(re.sub(r'(\S+)', r'[ch]\1[/ch]', current_chords))
        if current_lyrics.strip() != '':
            result.append(current_lyrics)
        return result

    out = []

    i = 0
    while i < len(lines):

        if is_chord_line(lines[i]):
            if i < len(lines) -1 and not is_chord_line(lines[i+1]):
                out.extend(split_chords_and_lyrics(lines[i],lines[i+1],soft_width,hard_width))
                i +=1
            else:
               out.append(lines[i])
        else:
            out.extend(split_chords_and_lyrics(None,lines[i],soft_width,hard_width))
        i +=1

    return out



def chordTabled(lines):
    out = []
    i = 0
    while i < len(lines):

        if is_chord_line(lines[i]):
            j = i
            while j < len(lines)-1:
                if not is_chord_line(lines[j+1]):
                    break
                j += 1
            if j == len(lines)-1 or (not lines[j+1].strip()):
                # process the tables
                col_widths = {}
                chord_items = []

                for k in range(i, j + 1):
                    chord_items_i = len(chord_items)
                    chord_items.append([])
                    matches = re.findall(r'\[ch[^\]]*\](.*?)\[/ch\]', lines[k])
                    for c in range(len(matches)):
                        chord_items[chord_items_i].append(matches[c])
                        col_widths[c] = max(col_widths.get(c, 0), len(matches[c]))
                for lcs in chord_items:
                    cs = []
                    for c in range(len(lcs)):
                        cs.append(f'[ch]{lcs[c]}[/ch]' + ' ' * (col_widths[c]-len(lcs[c])))
                    # out.append(" {\\c&H00E8E8E8&}|{\\r} ".join(cs))
                    out.append("  ".join(cs))

                i = j
            else:
                out.append(lines[i])
        else:
            out.append(lines[i])

        i +=1

    return out


def write_ass_file(tabs_gz_source_file,tonality_name,out_file,audio_seconds=None):
    # Open and read directly from the gzip file (in memory)
    with gzip.open(tabs_gz_source_file, "rt", encoding="utf-8") as f:
        data = json.load(f)

    song_name = data["name"]
    artist_name = data["artist"]
    capo = data["meta"]["capo"]
    tuning = data["meta"]["tuning"]
    if audio_seconds is None:
        audio_seconds = data["meta"]["duration"]/1000
    audio_end_second = audio_seconds+audio_start_at
    time_signature = ""

    tempo = data["tempo"]
    chords_in_track = []
    chords_start_times = []
    for track in data["tracks"]:
        if track["name"] == "@$Chords$@":
            for m in track["measures"]:

                if "tempo" in m:
                    tempo = m["tempo"]

                if time_signature == "" and "denominator" in m and "numerator" in m:
                    time_signature = f"{m["numerator"]}/{m["denominator"]}"

                for b in m["beats"]:
                    if "chord" in b:
                        chords_in_track.append(b["chord"]["name"])
                        chords_start_times.append(audio_start_at + ticks_to_seconds(b["start"]-ticks_per_beat,tempo))
            break


    chords_data = []
    lines = shortenLines(data["lyrics"].splitlines(),40,40)
    lines = chordTabled(lines)

    line_height = 50
    c_cnt = 0
    for i in range(len(lines)):
        matches = re.findall(r'\[ch[^\]]*\](.*?)\[/ch\]', lines[i])
        for j in range(len(matches)):
            if matches[j] != chords_in_track[c_cnt]:
                print("CHORDS IN TRACK DOES NOT MATCH LYRICS")
                exit(1)
            chords_data.append({"chord":chords_in_track[c_cnt],"start":chords_start_times[c_cnt],"line_i":i,"chord_i":j})
            c_cnt+=1


    chords_dialogs = []


    start_top_gap = 140
    # show all chords from 2.5 to 3 sec with animation
    for l_i in range(0,len(lines)):
        chords_dialogs.append(normalDialog(lines[l_i],fmt(2.5,2),fmt(audio_end_second if len(chords_data) == 0 else audio_start_at,2),start_top_gap + l_i* line_height,start_top_gap + l_i* line_height,500,0))

    starting_l_i = 0

    for c_i in range(len(chords_data)):

        start_tf = fmt(chords_data[c_i]["start"],2)
        end_tf = fmt(chords_data[c_i+1]["start"],2) if c_i<len(chords_data)-1 else fmt(audio_end_second,2)


        scroll_n = 0
        if c_i>0 and chords_data[c_i]["chord_i"] ==0: # new chord line after first
            scroll_n = max(chords_data[c_i]["line_i"] - max(chords_data[c_i-1]["line_i"],8),0) # chords will be always kept at around 8th line from top


        for l_i in range(starting_l_i,len(lines)):

            m_i = l_i-starting_l_i

            if chords_data[c_i]["line_i"] != l_i:
                chords_dialogs.append(normalDialog(lines[l_i],start_tf,end_tf,start_top_gap + m_i* line_height,start_top_gap + (m_i-scroll_n)* line_height))
            else:
                chords_dialogs.append(highlightedChordDialog(lines[l_i],start_tf,end_tf,start_top_gap + m_i* line_height,start_top_gap + (m_i-scroll_n)* line_height,chords_data[c_i]["chord_i"]))

        starting_l_i += scroll_n



    beats_dialogs = []
    if len(chords_start_times)>0:
        ts = re.match(r"(\d+)/(\d+)", time_signature)
        if ts:
            numerator = int(ts.group(1))
            seconds_per_beat = ticks_to_seconds(ticks_per_beat,tempo)
            i = 0
            while True:
                width =  (1080/numerator)*((i%numerator)+1)
                start_t = chords_start_times[0] + (i*seconds_per_beat)
                i += 1
                end_t = chords_start_times[0] + (i*seconds_per_beat)

                if end_t>audio_end_second:
                    break

                beats_dialogs.append(fr"Dialogue: 0,{fmt(start_t,2)},{fmt(end_t,2)},ProgressBarBG,,0,0,0,,{{\p1\an7\pos(0,92)\c&H000000FF&}}m 0 0 l {width} 0 l {width} 8 l 0 8")


    with open(out_file, "w", encoding="utf-8") as f:
        f.write(fr"""
[Script Info]
Title: {data["name"]}
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1080
PlayResY: 1920

;[V4+ Styles]
;Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, Bold, Italic, Underline, Alignment, MarginL, MarginR, MarginV, Encoding
;Style: Normal,Courier New,36,&HFFFFFF&, &HAAAAAA&,0,0,0,7,10,10,10,0


[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding

; === HEADINGS ===
Style: Heading, Montserrat SemiBold, 45, &H00D0E8F5, &H000000FF, &H32000000, &H00000000, -1, 0, 0, 0, 100, 100, 0, 0, 1, 2, 2, 7, 30, 30, 42, 1

; === LYRICS ===
Style: Lyrics,Inconsolata for Powerline, 50, &H00E8E8E8, &H000000FF, &H64000000, &H00000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 2, 1, 7, 20, 20, 60, 1

; === NORMAL CHORDS ===
; Soft bluish-gray with faint warmth — bridges Lyrics and Highlight glow.
Style: Chords,Inconsolata for Powerline, 50, &H006EC7E6, &H000000FF, &H64000000, &H00000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 2, 1, 7, 20, 20, 60, 1


; === MAIN TITLE ===
Style: Title,Montserrat SemiBold,105,&H00FFFFFF,&H000000FF,&H32000000,&H00000000,-1,0,0,0,100,100,2,0,1,3,3,2,8,40,40,300,1

; === ARTIST (By The Eagles) ===
Style: Artist,Montserrat Medium,60,&H00CBE4FA,&H000000FF,&H32000000,&H00000000,0,0,0,0,100,100,0,0,1,3,2,2,8,60,60,420,1

; === TAGLINE ("Chords · Lyrics") ===
Style: Tagline,Montserrat SemiBold,110,&H00AAC7FF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,3,0,1,3,3,2,8,40,40,700,1

; === SONG META INFO (Artist / Key / Capo / Tuning) ===
Style: Info,Montserrat Medium,42,&H00CBE4FA,&H000000FF,&H32000000,&H00000000,0,0,0,0,100,100,0,0,1,3,2,2,8,60,60,1400,1

; === CREDITS HEADING ===
Style: CreditHeading,Montserrat SemiBold,40,&H00A0C3E0,&H000000FF,&H32000000,&H00000000,0,0,0,0,100,100,0,0,1,3,2,2,8,60,60,1600,1

; === CREDITS TEXT ===
Style: Credits,Montserrat Light,36,&H00D0D0D0,&H000000FF,&H64000000,&H00000000,0,0,0,0,100,100,0,0,1,3,2,2,8,60,60,1650,1



; === TopBarBG ===
Style: TopBarBG,Arial,1,&H000F0D0D,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,8,980,40,150,1

; === SONG TITLE (on bar, left side) ===
Style: InfoTitle,Montserrat SemiBold,52,&H00FFFFFF,&H000000FF,&H00000000,&H00000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 2, 1, 7, 20, 20, 60, 1

; === RIGHT SIDE TEXT (artist or runtime) ===
Style: InfoRight,Montserrat Light,38,&H00CBE4FA,&H000000FF,&H00000000,&H00000000, 0, 0, 0, 0, 100, 100, 0, 0, 1, 2, 1, 7, 20, 20, 60, 1

; === ProgressBarBG ===
Style: ProgressBarBG,Arial,1,&HCC101010,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,2,0,0,0,1


[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text


""")

        f.write("\n".join(chords_dialogs))

        f.write(fr"""

; === MAIN TITLE ===
Dialogue: 0,0:00:00.00,0:00:02.50,Title,,0,0,0,,{{\fad(800,800)\blur2\pos(540,360)}}{song_name}

; === ARTIST ===
Dialogue: 0,0:00:00.10,0:00:02.50,Artist,,0,0,0,,{{\fad(800,800)\blur1\pos(540,460)}}By {artist_name}

; === TAGLINE ===
Dialogue: 0,0:00:00.30,0:00:02.50,Tagline,,0,0,0,,{{\fad(800,800)\blur1\pos(540,700)}}Chords & Lyrics

; === SONG META ===

Dialogue: 0,0:00:00.40,0:00:02.50,Info,,0,0,0,,{{\fad(800,800)\blur1\pos(540,1400)}}Key: Bm | Capo: {capo}
Dialogue: 0,0:00:00.40,0:00:02.50,Info,,0,0,0,,{{\fad(800,800)\blur1\pos(540,1460)}}Tuning: {tuning}
Dialogue: 0,0:00:00.40,0:00:02.50,Info,,0,0,0,,{{\fad(800,800)\blur1\pos(540,1520)}}Time Signature: {time_signature}

; === CREDITS ===
Dialogue: 0,0:00:00.50,0:00:02.50,Credits,,0,0,0,,{{\fad(800,800)\blur1\pos(540,1710)}}Original song © {artist_name} / Their Labels
Dialogue: 0,0:00:00.50,0:00:02.50,Credits,,0,0,0,,{{\fad(800,800)\blur1\pos(540,1770)}}For educational and practice purposes only


; == TOP INFO BAR AFTER 4 sec
Dialogue: 0,0:00:02.50,{fmt(audio_end_second,2)},TopBarBG,,0,0,0,,{{\p1\an7\pos(0,0)\c&H000F0D0D&}}m 0 0 l 1080 0 l 1080 100 l 0 100
Dialogue: 0,0:00:02.50,{fmt(audio_end_second,2)},InfoTitle,,0,0,0,,{{\fad(800,0)\q2\pos(20,20)}}{song_name}
Dialogue: 0,0:00:02.50,{fmt(audio_end_second,2)},TopBarBG,,0,0,0,,{{\p1\an7\pos(880,0)\c&H000F0D0D&}}m 0 0 l 1080 0 l 1080 100 l 0 100
Dialogue: 0,0:00:02.50,{fmt(audio_end_second,2)},InfoRight,,0,0,0,,{{\pos(910,10)}}{tonality_name} | {time_signature}
Dialogue: 0,0:00:02.50,{fmt(audio_end_second,2)},InfoRight,,0,0,0,,{{\pos(910,45)}}Capo: {capo}

; beat bar
;Dialogue: 0,0:00:03.00,{fmt(audio_end_second,2)},ProgressBarBG,,0,0,0,,{{\p1\an7\pos(0,92)\c&H000000FF&}}m 0 0 l 540 0 l 540 8 l 0 8

""")

        f.write("\n".join(beats_dialogs))


    used_chords = {}
    for c_i in range(len(chords_in_track)):
        if not chords_in_track[c_i] in used_chords:
            used_chords[chords_in_track[c_i]] = []
        used_chords[chords_in_track[c_i]].append({
            "start_t" : chords_start_times[c_i],
            "end_t" : chords_start_times[c_i+1] if c_i < len(chords_in_track)-1 else audio_end_second
        })
    return used_chords


# write_ass_file("t.json.gz","Bm","test.ass")
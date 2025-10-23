import matplotlib.pyplot as plt
import matplotlib.patches as patches

import os
import requests
import hashlib

background_c     = "#0D0D0F"
# background_c     = "#111318"
white_keys_c = "#C5C8CA"
black_keys_c = "#33353A"
finger_back_c = "#96C8FF"
finger_out_c    = "#0D0D0F"

def draw_piano_chord(chord_data,num_keys=24,out_file = None):

    notes = chord_data["notes"]
    baseDisplayNote = chord_data["baseDisplayNote"]


    if len(notes) == 0 :
        print("Notes are empty")
        exit(1)

    first_note_pos = notes[0] % 12

    if baseDisplayNote == "C":
        start_num = notes[0]-first_note_pos
    elif baseDisplayNote == "F":
        start_num = notes[0]-(first_note_pos-5) if first_note_pos >= 5 else notes[0]-(first_note_pos+7)
    else:
        print("ONLY C,F base note supported")
        exit(1)

    def is_white_key(midi_note):
        white_positions = [0, 2, 4, 5, 7, 9, 11]
        pos = midi_note % 12
        return pos in white_positions


    fig, ax = plt.subplots()
    fig.patch.set_facecolor(background_c)
    ax.set_facecolor(background_c)

    x = 0
    for midi in range(start_num, start_num + num_keys):
        if is_white_key(midi):
            rect = patches.Rectangle((x, 0), 1, 4, facecolor=white_keys_c, edgecolor=finger_out_c)
            x += 1
            if midi in notes:
                circle = plt.Circle((x-0.5, 3.5), 0.25, facecolor=finger_out_c, zorder=3,edgecolor=finger_back_c)
                ax.add_patch(circle)
        else:
            rect = patches.Rectangle((x-0.35, 0), 0.7, 2.5, facecolor=black_keys_c, edgecolor=finger_out_c, zorder=2)
            circle = plt.Circle((x, 2.3), 0.32, color=black_keys_c, zorder=3)
            ax.add_patch(circle)
            if midi in notes:
                circle = plt.Circle((x, 2.2), 0.25, facecolor=finger_back_c, zorder=3,edgecolor=finger_out_c)
                ax.add_patch(circle)
        ax.add_patch(rect)

    ax.plot([0, x], [0, 0], color=background_c, linewidth=5)

    # # Now draw black keys
    # for midi in range(start_num, start_num + num_keys):
    #     if not is_white_key(midi):
    #         # black key goes between the previous and next white key
    #         # find left white key
    #         left_white = max([w for i, w in enumerate(white_positions) if i + start_num <= midi])
    #         rect = patches.Rectangle((left_white + 0.65, 2), 0.7, 2.5, facecolor='black', edgecolor='black')
    #         ax.add_patch(rect)
    #         key_positions[midi] = left_white + 1  # approximate center

    fig.set_size_inches(x, 4)
    plt.subplots_adjust(left=0.05, top=0.85, right=0.95, bottom=0.0)
    # plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    # ax.margins(0)
    ax.set_xlim(0, x)  # exact x-range
    ax.set_ylim(0, 4)  # exact y-range
    ax.invert_yaxis()
    ax.axis('off')
    # plt.tight_layout(rect=(0.05, 0, 1, 0.95))
    if out_file is None:
        plt.show()
    else:
        plt.savefig(out_file, dpi=300, transparent=False)  # optional: transparent background
        plt.close(fig)  # close figure to free memory

def get_chords_data(chords):
    url = "https://tabs.ultimate-guitar.com/tab/applicature/piano-inversions"
    headers = {"referer": "https://tabs.ultimate-guitar.com"}
    params = {
        "chords[]": chords
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    out = []
    for c in chords:
        out.append(data["info"][c][c])
    return out

def draw_chord_files(chords,dir='./tmp/'):
    chords_data = get_chords_data(chords)
    out = []
    for c_i in range(len(chords)):
        file = os.path.join(dir, hashlib.md5(chords[c_i].encode()).hexdigest() + "_p.png")
        out.append(file)
        draw_piano_chord(chord_data=chords_data[c_i], out_file = file)
    return out


# print(draw_chord_files(["F#7","Em"]))
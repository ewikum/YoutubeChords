from matplotlib.offsetbox import AnchoredText
import matplotlib.pyplot as plt

import os
import requests
import hashlib

chord_title_c = "#F5E8D0"
background_c     = "#0D0D0F"  # main dark background
# background_c     = "#111318"  # main dark background
strings_c        = "#666A73"  # soft cool gray
nut_c            = "#C5C8CA"  # light silver-gray
frett_c          = "#33353A"  # subtle fret line gray
string_names_c   = "#D4D4D4"  # muted light gray for string names
frett_num_c      = "#999CA1"  # mid-gray for fret numbers
# finger_back_c    = "#85E0FF"  # muted teal for finger circles
finger_back_c = "#96C8FF"
finger_text_c    = "#0D0D0F"  # white text for contrast on teal

frett_r = 1.5

def draw_chord(chord_data, tuning=("E", "A", "D", "G", "B", "E"), num_frets=5, out_file = None):
    fingers = chord_data["fingers"]
    frets = chord_data["frets"]
    capos = chord_data.get("listCapos", [])

    num_strings = len(tuning)

    # === Determine fret range ===
    playable_frets = [f for f in frets if f > 0]
    capo_frets = [c["fret"] for c in capos]
    min_fret = min(playable_frets + capo_frets) if (playable_frets or capo_frets) else 1
    max_fret = max(playable_frets + capo_frets) if (playable_frets or capo_frets) else 1

    start_fret = 0
    if max_fret>5: # cannot use zero frett
        start_fret = min(max_fret-5,min_fret-1)
    num_frets = max(num_frets,max_fret-start_fret)

    fig, ax = plt.subplots()
    fig.patch.set_facecolor(background_c)
    ax.set_facecolor(background_c)

    # # titile
    # chord_name = "Bm"
    # ax.text(
    #     (num_strings-1)/2,-1.1, chord_name,
    #     ha='center', va='center',
    #     # transform=ax.transAxes,  # relative to axes coordinates
    #     color=chord_title_c,
    #     fontsize=24,
    #     fontweight='bold'
    # )

    string_names_gap = 0.5
    fret_num_gap = 0.7

    # === String names ===
    for s, name in enumerate(tuning):
        ax.text(fret_num_gap+s, 0, name, color=string_names_c, ha='center', va='center', fontsize=20, fontweight='bold')

    # === Fret numbers ===
    for f in range(num_frets):
        fret_number = start_fret + f + 1
        y_center = string_names_gap+(frett_r*(f+0.5))
        ax.text(0, y_center, str(fret_number), color = frett_num_c, va='center', ha='center', fontsize=20)

    # === Draw strings ===
    for s in range(num_strings):
        ax.plot([fret_num_gap+s, fret_num_gap+s], [string_names_gap, string_names_gap+ (num_frets*frett_r)], color=strings_c, linewidth=1.5)

    # === Draw frets ===
    for f in range(num_frets + 1):
        y = string_names_gap+ (f*frett_r)
        if f == 0:
            if start_fret == 0:
                ax.plot([fret_num_gap, fret_num_gap+num_strings - 1], [y, y], color=nut_c, linewidth=5)
            else:
                ax.plot([fret_num_gap, fret_num_gap+num_strings - 1], [y, y], color=nut_c, linewidth=2, linestyle="--")
        else:
            ax.plot([fret_num_gap, fret_num_gap+num_strings - 1], [y, y], color=frett_c, linewidth=2)


    # === Draw capo(s) ===
    for capo in capos:
        capo_fret = capo["fret"]
        capo_y = capo_fret - start_fret
        if 0 <= capo_y <= num_frets:
            s1 = capo["startString"]
            s2 = capo["lastString"]

            # # since data are from the last string
            s1 = num_strings - s1
            s2 = num_strings - s2

            s1 -= 1
            s2 -= 1
            ax.plot([fret_num_gap+s1, fret_num_gap+s2], [string_names_gap+(frett_r*(capo_y - 0.5)), string_names_gap+(frett_r*(capo_y - 0.5))], color=finger_back_c, linewidth=45, solid_capstyle="round")
            # show finger number above capo
            mid_x = fret_num_gap+ ((s1 + s2) / 2)
            ax.text(mid_x, string_names_gap+ (frett_r*(capo_y - 0.5)), str(capo["finger"]), ha='center', va='center', fontsize=25, color=finger_text_c, fontweight="bold")

    # === Draw fretted notes / open / muted ===

    # since data are from the last string
    fingers.reverse()
    frets.reverse()

    for s in range(num_strings):
        f = frets[s]
        finger = fingers[s]

        if f == -1:
            ax.text(fret_num_gap+s, string_names_gap+(frett_r*0.5), "X", ha='center', va='center', fontsize=45, color=finger_back_c, fontweight="bold",transform=ax.transData)
        elif f > 0 and finger>0:
            fret_y = (f - start_fret - 0.5)
            if 0 <= fret_y < num_frets:
                circle = plt.Circle((fret_num_gap+s, string_names_gap+(frett_r*fret_y)), frett_r*0.25, color=finger_back_c, zorder=2)
                ax.add_patch(circle)
                ax.text(fret_num_gap+s, string_names_gap+(frett_r*fret_y), str(finger), ha='center', va='center', fontsize=25, color=finger_text_c, fontweight="bold")

    # === Style ===
    # fig.set_size_inches(num_strings, 4)

    # plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(0, fret_num_gap+num_strings)
    ax.set_ylim(0, (num_frets*frett_r)+string_names_gap)
    ax.invert_yaxis()
    ax.axis('off')
    ax.set_aspect('equal')
    # plt.tight_layout(rect=(1,0,0,0))
    plt.subplots_adjust(left=0.05, top=0.9, right=1.05, bottom=0.0)
    # plt.tight_layout(rect=(0.05, 0, 1, 0.95))
    fig.set_size_inches(fret_num_gap+num_strings, string_names_gap+(num_frets*frett_r))

    # plt.tight_layout(pad=1)
    if out_file is None:
        plt.show()
    else:
        plt.savefig(out_file, dpi=300, transparent=False)  # optional: transparent background
        plt.close(fig)  # close figure to free memory

def get_chords_data(chords,tuning):
    url = "https://tabs.ultimate-guitar.com/tab/applicature/transpose"
    headers = {"referer": "https://tabs.ultimate-guitar.com"}
    params = {}
    for c in chords:
        params[c] = c
    params['instr'] = 'guitar'
    params['json'] = '1'
    params['appl_api_version'] = '2'
    params['custom'] = '0'
    params['tuning'] = " ".join(tuning)
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    applicature = data["info"]["applicature"]

    out = []
    for c in chords:
        out.append(applicature[c]["0"])
    return out

def draw_chord_files(chords,dir='./tmp/',tuning=("E", "A", "D", "G", "B", "E")):
    chords_data = get_chords_data(chords,tuning)
    out = []
    for c_i in range(len(chords)):
        file = os.path.join(dir, hashlib.md5(chords[c_i].encode()).hexdigest() + "_g.png")
        out.append(file)
        draw_chord(chord_data=chords_data[c_i], out_file = file)

    return out

# print(draw_chord_files(["F#7","Bm"]))
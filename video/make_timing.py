"""Fit each shot to Daniel's narration and write src/data/timing.json.

Each shot lasts as long as its clip plus a short pad. Within a shot, anchor points map narration time to the shot's own
(nominal) frame clock, so each visual beat lands on the words that describe it. The anchor times come from timestamped
transcripts of the clips (Oct 22). Wherever no clip plays, Daniel's room tone (silence.mp3, his "baseline for any sort of
audio editing") fills the gap, so the noise floor never drops to digital silence.

    python3 make_timing.py
"""
import json
import math
import subprocess
from pathlib import Path

FPS = 30
PAD_S = 0.5  # breath after each clip (the clips already carry ~0.6 s of room tone at each edge)
HERE = Path(__file__).parent

# composition, nominal end frame, clip, anchors as (seconds into the clip, nominal frame) for the beat it narrates
SHOTS = [
    ("Shot1Open", 810, "shot1", [(13.5, 150),    # "Does its set of candidate pathways include..." -> sub-question 1
                                 (17.9, 300),    # "and can we pick that one..." -> sub-question 2
                                 (21.4, 505)]),  # "We fit at ... and forecast 750" -> the test case
    ("Shot3Loop", 1020, "shot3", [(11.0, 265),   # "Code then checks that every combination conserves atoms" -> card 2
                                  (20.3, 515),   # "The picks are locked in before we load 750" -> card 3
                                  (22.6, 700),   # "Finally, the AI tells us what the data can't settle" -> card 4
                                  (28.0, 950)]),
    ("Shot4Reveal", 600, "shot4", [(5.5, 215),   # during "picks the best fit": the 750 C measurements land
                                   (9.2, 330),   # "That pick ranks 11th" (word at 9.5 s) -> baseline row
                                   (9.6, 342),   # its countdown ends on the word
                                   (20.1, 400),  # "That one ranks 4th" (20.5 s) -> the rule's pick
                                   (20.5, 412),
                                   (25.7, 470),  # "and that one ranks first" (26.1 s) -> the agent's other pick
                                   (26.1, 482)]),
    ("Shot5Ranks", 540, "shot5", [(3.0, 120),    # "On the left is its ranking by fit"
                                  (9.5, 300),    # "...its ranking at forecasting 750" (the dots have moved)
                                  (10.5, 330),
                                  (13.4, 420)]),  # "the best fit is not the best forecaster"
    ("Shot5bRuns", 480, "shot5b", [(9.5, 290),   # all five rows in during "every set of candidates held a top four"
                                   (11.0, 330)]),  # "Picking by the best fit chose anywhere from fourth to 36th" -> caption
    ("Shot7Plan", 720, "shot7", [(6.5, 95),      # "the experiment where its explanations would disagree the most"
                                 (8.5, 120),     # "Its top pick is to halve the lithium carbonate" -> highlight
                                 (11.3, 150),    # "That would test its rival idea" -> curves draw
                                 (18.5, 320),
                                 (19.3, 330),    # "By two minutes, the two explanations differ" -> the gap
                                 (23.0, 400)]),  # "Two of its leading models can't be told apart" -> note
    ("Shot9Close", 700, "shot9", [(8.4, 30),     # "Yes, every time." -> finding 1
                                  (14.4, 70),    # "Not reliably." -> finding 2
                                  (16.0, 110),   # "The chemistry agreed across models" -> finding 3
                                  (18.0, 150),   # "and the agent said what it couldn't settle" -> finding 4
                                  (20.2, 330),   # "a study we found through Valency..." -> finding 5
                                  (36.2, 650),   # "The AI is useful for proposing pathways" -> conclusion line
                                  (37.0, 680)]),  # fully shown while he says it
    ("ShotEnd", 760, "conclusion", [(0.6, 30),   # "Through NernstWork, we've shown..." -> first line
                                    (11.7, 340),  # "The implication is more targeted experiments" -> second line
                                    (20.8, 560)]),  # "It points to a better way to design experiments" -> credits
]


def seconds(name: str) -> float:
    p = HERE / "public" / "audio" / f"{name}.mp3"
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def main():
    shots = []
    for comp, nominal, clip, cues in SHOTS:
        a = seconds(clip)
        frames = math.ceil((a + PAD_S + (1.5 if comp == "ShotEnd" else 0)) * FPS)  # hold the end card a moment
        anchors = [[0, 0]] + [[round(t * FPS), n] for t, n in cues] + [[frames, nominal]]
        assert all(p[0] < q[0] and p[1] <= q[1] for p, q in zip(anchors, anchors[1:])), (comp, anchors)
        clip_end = math.ceil(a * FPS)
        shots.append({"id": comp, "nominal": nominal, "frames": frames, "anchors": anchors,
                      "audio": [{"src": f"audio/{clip}.mp3", "from": 0, "seconds": a}],
                      "room_tone": [[clip_end, frames]] if frames - clip_end >= 2 else []})
    out = {"fps": FPS, "shots": shots, "total_frames": sum(s["frames"] for s in shots)}
    (HERE / "src" / "data" / "timing.json").write_text(json.dumps(out, indent=1))
    t = 0.0
    for s in shots:
        print(f"{s['id']:12s} {t:6.1f} s -> {t + s['frames'] / FPS:6.1f} s   clip {s['audio'][0]['seconds']:.1f} s")
        t += s["frames"] / FPS
    print(f"total {out['total_frames'] / FPS:.1f} s")


if __name__ == "__main__":
    main()

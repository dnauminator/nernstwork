# YouTube upload

File: `out/NernstWork_final_2026-10-22.mp4` (3:42, 1080p30 H.264, AAC 48 kHz at -16 LUFS; under the hackathon's
4-minute limit). Captions: `captions/nernstwork_final.en.srt` (English, from the narration). Thumbnail:
`docs/submission/youtube_thumbnail.png` (1280x720). Visibility must be Public for the submission ("publicly accessible").

## Title

NernstWork: can an AI agent infer how a material forms? (OSI Hackathon 2026)

## Description

Can a language-model agent infer a solid-state reaction pathway from time-resolved X-ray data, and prove it on a temperature it never saw? On a published battery-material synthesis (TiO₂ + Li₂CO₃ → Li₄Ti₅O₁₂), every AI-proposed search space contained a model that predicted 750 °C among the top 4 of 153 code-built reference models, but picking that model from the 700 and 725 °C data alone was unreliable. The agent instead names the experiment that would tell its candidates apart.

0:00 The research question
0:30 How NernstWork works
1:00 Predicting 750 °C without refitting
1:28 The best fit is not the best forecaster
1:43 Four AI runs, Claude and Gemini
2:05 What to measure next
2:33 What we found
3:16 Conclusion

Code and results: https://github.com/dnauminator/nernstwork
Data: D. Hu et al., J. Am. Chem. Soc. 145, 26545 (2023), doi:10.1021/jacs.3c10916 (Chapman group).
Models: Claude Opus 5.5, Gemini 4 Argon. Literature search: Valency.
Caveats: a retrospective test on one chemistry with two runs per model; the models may have seen the paper.

Daniel Naumov (narration) and Jarrod Barnes. Built at the 4th Open Scientific Intelligence Hackathon, October 2026.

## Tags

AI for science, materials science, solid-state synthesis, reaction kinetics, in situ XRD, lithium titanate, LLM agents, Claude, Gemini, scientific discovery, OSI Hackathon

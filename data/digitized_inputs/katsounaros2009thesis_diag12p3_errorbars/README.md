# Katsounaros thesis Diag 12.3: error bars

These are the error bars on every series in the thesis copy of Katsounaros et al. 2012 Fig. 1 (0.5 M NaNO3 + 1 M NaOH, Sn, -2.2 V vs Ag/AgCl). The thesis is the Katsounaros PhD thesis, AUTh 2009, doi 10.12681/eadd/19491; the figure is Diag 12.3 on printed p. 191. Axes were calibrated from 11 y ticks and 7 x ticks located on the 300 dpi page image. Each bar end was then read from its cap, a 1 px horizontal line about 17 px wide. `extracted.csv` holds one row per species and time.

**Finding.** Every measurable bar is +-10% of the plotted value, for all five species and all times. The 18 well-resolved bars (half-width at least 5 px) give a relative half-width of 0.0997 +- 0.0010 (range 0.097-0.101). The 8 small bars give 0.103 +- 0.010, which is consistent with 0.100 within their 0.2-0.5 px reading error. The plotting program applied a fixed percentage to every point, so the bars are not replicate statistics that vary from point to point. Neither the caption nor the text describes them. Elsewhere the thesis says its experimental error "was of the order of 10%" (printed p. 81), and it reports a 5% RSD for the hyponitrite ion-chromatography method (printed p. 71).

**Coverage.** Five bars are missing or weak:
- Hidden: N2 at 30 min (inside the filled triangle) and NO3 at 150 min (inside the filled square, under the NH3 triangle).
- Unresolved: NH3 and N2O at 30 min, where the expected half-width is under 1 px in a crowded cluster on the axis.
- Low confidence: NO3 at 180 min.
- One cap only: NO3 at 0 min (the upper end is clipped above the axis), and NO2 at 60 and 90 min (the lower cap falls inside the NO3 square).

**Use as noise model.** Set `relative_sigma = 0.10` for NO3, NO2, N2, NH3 and N2O, or give each point `sigma = 0.10 * y`. Add an `absolute_sigma_mM` floor for points near zero. Caveat: these are author-drawn bars of unstated type. They are a uniform 10%, not measured scatter. If they mean 2 sigma or a maximum-error range, the 1-sigma value is nearer 0.05.

A by-product: where both caps are visible, the cap midpoint gives an independent reading of the plotted value. It moves NO3 at 60 min to 123.5 mM, against 122.0 from the occluded template match, and it puts NH3 at 120 min at 25.8 mM (see `meta.json`). That supports the thesis marker over Daniel's 19.6 for the thesis copy only. Daniel digitized the journal figure, which was not checked, and the thesis's own Diag 12.1 NH3 rates imply about 20.8 mM at 120 min (`../katsounaros2009thesis_diag12p1_intermediates/`), so this does not settle Daniel's value. Overlay check: scratch only, not committed. Scripts: `literature/extraction_scripts/k12_hidden/errorbars/`.

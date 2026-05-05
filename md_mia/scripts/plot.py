"""Generate plots for the §27-1001 dataset (FY 2008–FY 2025)."""
import polars as pl
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, PercentFormatter
from datetime import date

df = pl.read_csv("mia_27_1001_data.csv")
years = df["fy"].to_numpy()
total = df["total"].to_numpy()
settled = df["settled_wd_dismissed"].to_numpy()
bad_faith = df["bad_faith"].to_numpy()
no_viol = df["no_violation"].to_numpy()
breach_only = df["breach_pay_only"].to_numpy()
on_merits = df["on_merits"].to_numpy()
pct = df["pct_insured_wins"].to_numpy()

C_SETTLED = "#B8B8C8"
C_NO_VIOL = "#5B7BA0"
C_PARTIAL = "#D4A55E"
C_BAD     = "#C44536"
C_LINE    = "#222"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#444",
    "axes.labelcolor": "#222",
    "xtick.color": "#444",
    "ytick.color": "#444",
})

fig = plt.figure(figsize=(14, 9.5))
gs = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.32)

# === Top panel — stacked bars =================================================
ax1 = fig.add_subplot(gs[0])
ax1.bar(years, settled, color=C_SETTLED, label="Settled / withdrawn / dismissed", edgecolor="white", linewidth=0.5)
ax1.bar(years, no_viol, bottom=settled, color=C_NO_VIOL, label="No violation (insurer wins)", edgecolor="white", linewidth=0.5)
ax1.bar(years, breach_only, bottom=settled + no_viol, color=C_PARTIAL,
        label="Breach to pay only (partial insured win)", edgecolor="white", linewidth=0.5)
ax1.bar(years, bad_faith, bottom=settled + no_viol + breach_only, color=C_BAD,
        label="§27-1001 violation (bad-faith finding)", edgecolor="white", linewidth=0.5)

for x, t in zip(years, total):
    ax1.text(x, t + 1.5, str(t), ha="center", va="bottom", fontsize=8.5, color="#222")

for x, s, n, br, bf in zip(years, settled, no_viol, breach_only, bad_faith):
    if bf > 0:
        ax1.text(x, s + n + br + bf / 2, str(bf), ha="center", va="center",
                 fontsize=8, color="white", weight="bold")

ax1.set_title("Maryland Insurance Administration §27-1001 bad-faith complaints, FY 2008–FY 2025",
              fontsize=13, weight="bold", loc="left", pad=14)
ax1.set_ylabel("Number of complaints filed")
ax1.set_xticks(years)
ax1.set_xticklabels([str(y) for y in years], fontsize=9)
ax1.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=8))
ax1.set_ylim(0, max(total) * 1.13)
ax1.grid(axis="y", linestyle=":", alpha=0.45)
ax1.set_axisbelow(True)
ax1.legend(loc="upper left", frameon=False, fontsize=9)

# Vertical pointer above the FY 2008 bar, sitting in the gap between the bar
# top label and the legend.
ax1.annotate("FY 2008 = partial year\n(Oct 1 2007 – Jun 30 2008)",
             xy=(2008, total[0] + 2.5), xytext=(2008, 60),
             fontsize=8, color="#555", ha="center", va="bottom",
             arrowprops=dict(arrowstyle="-", color="#888", lw=0.6))

# === Bottom panel — % finding for insured w/ commissioner bands ==============
ax2 = fig.add_subplot(gs[1])

def fy_x(d: date) -> float:
    """Convert calendar date to plot x-coord. FY end Jun 30 of year Y → x = Y+0.5."""
    fy_end_year = d.year if d.month <= 6 else d.year + 1
    fy_start = date(fy_end_year - 1, 7, 1)
    days_in = (d - fy_start).days
    days_total = (date(fy_end_year, 6, 30) - fy_start).days + 1
    frac = days_in / days_total
    return (fy_end_year - 0.5) + frac

# Commissioner tenures with exact dates
commissioners = [
    # (full_name, short_name, start_date, end_date, color)
    ("Ralph S. Tyler",       "Tyler",      date(2007,  4,  1), date(2010,  1,  8), "#7DA68A"),
    ("Beth Sammis (acting)", "Sammis",     date(2010,  1,  8), date(2011,  6, 13), "#D4C26B"),
    ("Therese M. Goldsmith", "Goldsmith",  date(2011,  6, 13), date(2015,  1, 21), "#6F8FB0"),
    ("Al Redmer, Jr.",       "Redmer",     date(2015,  1, 21), date(2020,  5, 18), "#5BA89A"),
    ("Kathleen A. Birrane",  "Birrane",    date(2020,  5, 18), date(2024,  6, 30), "#9885B0"),
    # FY 2025 covers a Hatchette interim (Jul 1 – Sep 30, 2024) followed by
    # Grant (Oct 1, 2024 onwards). Merged here since case data isn't split.
    ("Marie Grant",          "Grant",      date(2024,  7,  1), date(2025,  6, 30), "#7BA8C7"),
]

x_lo, x_hi = 2007.5, 2025.5

# Background bands
for full_name, short_name, d0, d1, color in commissioners:
    x0 = max(fy_x(d0), x_lo)
    x1 = min(fy_x(d1), x_hi)
    if x1 <= x0:
        continue
    ax2.axvspan(x0, x1, color=color, alpha=0.20, zorder=0, lw=0)

# Transition markers
for _, _, d0, _, _ in commissioners[1:]:
    xt = fy_x(d0)
    if x_lo < xt < x_hi:
        ax2.axvline(xt, color="#666", lw=0.7, linestyle=(0, (4, 3)), zorder=1, alpha=0.7)

# === Three aggregate dashed lines =============================================
gold_fys = {2012, 2013, 2014, 2015}
gold_mask = df["fy"].is_in(list(gold_fys)).to_numpy()

bf_all = bad_faith.sum()
om_all = on_merits.sum()
bf_g   = bad_faith[gold_mask].sum()
om_g   = on_merits[gold_mask].sum()
bf_o   = bad_faith[~gold_mask].sum()
om_o   = on_merits[~gold_mask].sum()

agg_lifetime = bf_all / om_all * 100
agg_gold     = bf_g   / om_g   * 100
agg_other    = bf_o   / om_o   * 100

# (y, color, linestyle, lw, label_text)
agg_lines = [
    (agg_gold,     "#8B0000", (0, (6, 2)),  1.6,
     f"Goldsmith tenure: {bf_g}/{om_g} = {agg_gold:.2f}%"),
    (agg_lifetime, "#444",    "--",          1.4,
     f"MIA all time: {bf_all}/{om_all} = {agg_lifetime:.2f}%"),
    (agg_other,    "#0F5F4F", (0, (2, 2)),  1.4,
     f"All other commissioners: {bf_o}/{om_o} = {agg_other:.2f}%"),
]
for yval, color, ls, lw, _ in agg_lines:
    ax2.axhline(yval, color=color, linestyle=ls, linewidth=lw, zorder=2, alpha=0.85)

# === Data line on top =========================================================
zero_mask = pct == 0
ax2.plot(years, pct, color=C_LINE, linewidth=1.4, zorder=3)
ax2.scatter(years[~zero_mask], pct[~zero_mask], s=70, color=C_BAD,
            edgecolor="white", linewidth=1.2, zorder=4)
ax2.scatter(years[zero_mask], pct[zero_mask], s=70, facecolor="white",
            edgecolor=C_BAD, linewidth=1.5, zorder=4)

for x, p, on_m, bf in zip(years, pct, on_merits, bad_faith):
    label = f"{p:.1f}%\n({bf}/{on_m})"
    ax2.annotate(label, xy=(x, p), xytext=(0, 11),
                 textcoords="offset points", ha="center", fontsize=7.4, color="#222")

# === Commissioner labels along top of panel ===================================
y_label_top = 33
y_label_low = 29  # for narrow bands that need to dodge a neighbor
for full_name, short_name, d0, d1, color in commissioners:
    x0 = max(fy_x(d0), x_lo)
    x1 = min(fy_x(d1), x_hi)
    if x1 <= x0:
        continue
    xc = (x0 + x1) / 2
    width = x1 - x0
    flat = full_name.replace("\n", " ")
    if width < 0.45:
        label = short_name
        fs = 7.0
        y_label = y_label_low  # narrow bands sit lower so they don't clip wider neighbors
    elif width < 1.7 and " " in flat:
        words = flat.split()
        if len(words) <= 2:
            label = "\n".join(words)
        else:
            label = words[0] + "\n" + " ".join(words[1:])
        fs = 8.0
        y_label = y_label_top
    else:
        label = flat
        fs = 8.2
        y_label = y_label_top
    ax2.text(xc, y_label, label, ha="center", va="bottom", fontsize=fs,
             color="#222", weight="bold",
             bbox=dict(boxstyle="round,pad=0.25", facecolor=color,
                       alpha=0.45, edgecolor="none"))

# === Inline labels at right edge of plot (no legend box) =====================
# Position labels just past x_hi at each line's y-value, in the line's color.
label_x = x_hi + 0.15
for yval, color, ls, lw, label in agg_lines:
    ax2.text(label_x, yval, label, ha="left", va="center", fontsize=8.6,
             color=color, weight="bold", clip_on=False)

ax2.set_title("Share of on-merits decisions finding bad faith — i.e. finding for the insured",
              fontsize=12, weight="bold", loc="left", pad=10)
ax2.set_ylabel("Bad-faith findings ÷ on-merits decisions")
ax2.set_xlabel("Fiscal year (Maryland state FY ends June 30); shaded bands = MIA commissioner in office")
ax2.set_xticks(years)
ax2.set_xticklabels([str(y) for y in years], fontsize=8.5)
ax2.yaxis.set_major_formatter(PercentFormatter(decimals=0))
ax2.set_ylim(-2, 38)
ax2.set_xlim(x_lo, x_hi)
ax2.grid(axis="y", linestyle=":", alpha=0.45)
ax2.set_axisbelow(True)

fig.text(0.5, 0.015,
         "Source: MIA annual reports filed under Md. Insurance Article §27-1001(h), FY 2008–2025. "
         "Commissioner tenures from MIA letterhead, Ballotpedia, and contemporaneous press.",
         fontsize=7.8, color="#555", ha="center")

fig.subplots_adjust(left=0.06, right=0.97, top=0.95, bottom=0.08, hspace=0.30)
fig.savefig("mia_27_1001_trends.png", dpi=180, bbox_inches="tight",
            facecolor="white", pad_inches=0.15)
fig.savefig("mia_27_1001_trends.pdf", bbox_inches="tight",
            facecolor="white", pad_inches=0.15)
print(f"Saved mia_27_1001_trends.png and .pdf")
print(f"\nAggregate values:")
print(f"  Goldsmith (FY 2012-2015): {bf_g}/{om_g} = {agg_gold:.2f}%")
print(f"  Lifetime (FY 2008-2025):  {bf_all}/{om_all} = {agg_lifetime:.2f}%")
print(f"  All others:               {bf_o}/{om_o} = {agg_other:.2f}%")

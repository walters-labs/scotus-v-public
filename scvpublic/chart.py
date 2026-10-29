"""Small inline SVG; no plotting globals, filenames, or server-side image writes."""
from html import escape
from math import fsum


def combine_sources(sources):
    """Equal source weights within observed years; never interpolate missing years."""
    years = sorted({year for data in sources.values() for year in data})
    contributors = {year: [name for name, data in sources.items() if year in data]
                    for year in years}
    values = {year: fsum(sources[name][year] for name in names)/len(names)
              for year, names in contributors.items()}
    return values, contributors


def chart(court, public, counts=None, gss=None, ces=None, view="all", pew=None, wvs=None):
    sources = {'ANES': public}
    colors = {'ANES': '#2467ad', 'GSS': '#28734f', 'CES': '#8051a4', 'Pew': '#9c620b', 'WVS': '#007f89'}
    if gss is not None:
        sources['GSS'] = gss
    if ces is not None:
        sources['CES'] = ces
    if pew is not None:
        sources['Pew'] = pew
    if wvs is not None:
        sources['WVS'] = wvs
    combined, contributors = combine_sources(sources)
    datasets = [(court, '#bd493d', 'Court')]
    if view == 'combined':
        datasets.append((combined, '#2467ad', 'Combined'))
    else:
        datasets.extend((data, colors[name], name if len(sources) > 1 else 'Public')
                        for name, data in sources.items()
                        if view == 'all' or view == name.lower())
    years = sorted({year for data, _, _ in datasets for year in data})
    if not years:
        return ''
    lo, hi = min(years) - 1, max(years) + 1
    x = lambda year: 85 + 670 * (year - lo) / (hi - lo)
    y = lambda value: 170 - 125 * value
    parts = ['<svg viewBox="0 0 800 345" role="img" aria-label="Ideological polarity by year">']
    for value, label in [(-1, 'Conservative'), (0, 'Neutral'), (1, 'Liberal')]:
        parts.append(f'<path d="M85 {y(value)} H755" stroke="#d8dde6"/><text x="78" y="{y(value)+4}" text-anchor="end" font-size="11">{label}</text>')
    for year in sorted(set([min(years), (min(years)+max(years))//2, max(years)])):
        parts.append(f'<text x="{x(year)}" y="322" text-anchor="middle" font-size="12">{year}</text>')
    for data, color, name in datasets:
        for year, value in data.items():
            contribution = ("; sources: " + ", ".join(contributors[year]) +
                            f"; equal weight 1/{len(contributors[year])} each") if name == "Combined" else ""
            parts.append(f'<circle cx="{x(year):.2f}" cy="{y(value):.2f}" r="4" fill="{color}"><title>{escape(name)} {year}: {value:.3f}{escape(contribution)}{f'; {counts.get(year, 0)} cases' if name == 'Court' and counts is not None else ''}</title></circle>')
        if len(data) >= 2:
            mx, my = sum(data)/len(data), sum(data.values())/len(data)
            slope = sum((year-mx)*(value-my) for year,value in data.items()) / sum((year-mx)**2 for year in data)
            a, b = min(data), max(data)
            parts.append(f'<path d="M{x(a):.2f} {y(my+slope*(a-mx)):.2f} L{x(b):.2f} {y(my+slope*(b-mx)):.2f}" stroke="{color}" stroke-width="2" fill="none"><title>{name} linear best fit</title></path>')
    return ''.join(parts) + '</svg>'

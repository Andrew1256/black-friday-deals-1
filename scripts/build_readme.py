#!/usr/bin/env python3
"""Build the generated parts of README.md from deals.yml.

Usage:
    python scripts/build_readme.py           # rewrite README.md
    python scripts/build_readme.py --check   # fail if README.md is out of date

Only the text between <!-- NAME:START --> and <!-- NAME:END --> markers is
generated. Everything else in README.md is hand-written and left alone.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "deals.yml"
README = ROOT / "README.md"

STATUS = {
    "live": "🟢&nbsp;Live",
    "soon": "⏳&nbsp;Soon",
    "expired": "⛔&nbsp;Expired",
}
REQUIRED = ("name", "domain", "url", "description", "offer", "status")
PICKS_PER_ROW = 4


# ------------------------------------------------------------------- helpers

def groups_of(cat: dict) -> list[dict]:
    """A category has either a flat `deals` list or a list of `groups`."""
    if "groups" in cat:
        return cat["groups"]
    return [{"deals": cat.get("deals", [])}]


def deals_of(cat: dict) -> list[dict]:
    return [d for g in groups_of(cat) for d in g.get("deals", [])]


def all_deals(data: dict) -> list[dict]:
    return [d for cat in data["categories"] for d in deals_of(cat)]


def fmt_date(value) -> str:
    d = value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value))
    return f"{d:%b} {d.day}, {d.year}"


def shield(label: str, message: str | None, color: str, label_color: str | None = None) -> str:
    def esc(s: str) -> str:
        return quote(s.replace("-", "--").replace("_", "__").replace(" ", "_"), safe="_")

    path = f"{esc(label)}-{esc(message)}-{color}" if message else f"{esc(label)}-{color}"
    extra = f"&labelColor={label_color}" if label_color else ""
    return f"https://img.shields.io/badge/{path}?style=for-the-badge{extra}"


def favicon(domain: str, size: int) -> str:
    return f"https://www.google.com/s2/favicons?domain={domain}&sz={size}"


def code_soon(deal: dict) -> bool:
    """`code: soon` means a coupon code is expected but not out yet."""
    return str(deal.get("code", "")).lower() == "soon"


def waiting_button(deal: dict, height: int = 26) -> str:
    """Grey "Code coming soon" button with a waiting icon, for codes not out yet."""
    img = shield("Code", "Coming Soon", "f97316", "111827")
    return f'<a href="{deal["url"]}"><img src="{img}" alt="Code coming soon" height="{height}"></a>'


def coupon_button(deal: dict, height: int = 26) -> str:
    """Coupon code shown inside a button, styled like Get Deal.

    GitHub READMEs can't run JavaScript, so a click can't copy text. The
    button shows the code and opens the deal page; the alt text holds the
    code too, so it can be selected and copied in most browsers.
    """
    img = shield("Code", deal["code"], "f97316", "111827")
    return f'<a href="{deal["url"]}"><img src="{img}" alt="{deal["code"]}" height="{height}"></a>'


def button(deal: dict) -> str:
    """Coupon deals show a coupon button, other deals a Get Deal button."""
    if code_soon(deal):
        return waiting_button(deal)
    if deal.get("code"):
        return coupon_button(deal)
    if deal["status"] == "live":
        img, alt = shield("Get Deal", None, "f97316"), "Get Deal"
    else:
        img, alt = shield("Visit Site", None, "64748b"), "Visit Site"
    return f'<a href="{deal["url"]}"><img src="{img}" alt="{alt}" height="26"></a>'


def logo(deal: dict, size: int) -> str:
    """Certification logos when set, otherwise the site's favicon."""
    alt = f'{deal["name"]} logo'
    if deal.get("logos"):
        return "&nbsp;".join(f'<img src="{p}" height="{size}" alt="{alt}">' for p in deal["logos"])
    return f'<img src="{favicon(deal["domain"], 128)}" width="{size}" height="{size}" alt="{alt}">'


def offer_text(deal: dict) -> str:
    if code_soon(deal):  # offer not announced yet: show only a waiting icon
        return "⏳"
    if deal["status"] == "soon" and not code_soon(deal):
        return f"👀&nbsp;<i>{deal['offer']}</i>"
    text = deal["offer"]
    if len(text) <= 18:  # keep short offers like "40% off" on one line
        text = text.replace(" ", "&nbsp;")
    return f"<b>{text}</b>"


def plain_offer(deal: dict) -> str:
    """Offer as one plain sentence fragment, for FAQ answers."""
    code = f" with code `{deal['code']}`" if deal.get("code") and not code_soon(deal) else ""
    return f"**{deal['name']}**: {deal['offer']}{code}"


def render_faq(data: dict) -> str:
    """Question-and-answer toggles built from the deal data.

    Short, direct answers in Q&A form are what search engines and AI answer
    engines quote, so every answer here is generated and stays in sync.
    Content inside <details> is still in the page, so it is still indexed.
    """
    year = data["year"]
    bf, cm = fmt_date(data["black_friday"]), fmt_date(data["cyber_monday"])
    live = [d for d in all_deals(data) if d["status"] == "live"]
    qa: list[tuple[str, list[str]]] = [(
        f"When is Black Friday {year}?",
        [f"Black Friday {year} is on **{bf}** and Cyber Monday {year} is on **{cm}**. "
         f"Many deals in this tracker are already live before Black Friday and run through Cyber Monday."],
    )]
    for cat in data["categories"]:
        cat_live = [d for d in deals_of(cat) if d["status"] == "live"]
        if not cat_live:
            continue
        topic = cat.get("faq_topic", cat["title"].lower())
        lines = [f"- {plain_offer(d)}" for d in cat_live[:5]]
        if len(cat_live) > 5:
            lines.append(f"- …and {len(cat_live) - 5} more in [{cat['title']}](#{cat['id']}).")
        qa.append((f"What are the best {topic} deals for Black Friday {year}?", lines))
    codes: dict[str, str] = {}
    for d in live:
        if d.get("code") and not code_soon(d):
            codes.setdefault(d["code"], d["name"])
    if codes:
        qa.append((f"Which Black Friday {year} coupon codes work right now?",
                   [f"- `{code}`: {name}" for code, name in codes.items()]))
    qa.append(("How often is this Black Friday tracker updated?", [
        f"We check every deal during the sale and mark it 🟢 Live, ⏳ Soon or ⛔ Expired. "
        f"Last checked: **{fmt_date(data['last_updated'])}**. {len(live)} of {len(all_deals(data))} deals are live."
    ]))
    out = []
    for question, answer in qa:
        out.append(f"<details>\n<summary><b>{question}</b></summary>\n")
        out.extend(answer)
        out.append("\n</details>\n")
    return "\n".join(out)


# ---------------------------------------------------------------- validation

def validate(data: dict) -> list[str]:
    errors: list[str] = []
    names: set[str] = set()
    for cat in data.get("categories", []):
        for key in ("id", "emoji", "title", "intro"):
            if key not in cat:
                errors.append(f"category {cat.get('id', '?')}: missing '{key}'")
        if "deals" not in cat and "groups" not in cat:
            errors.append(f"category {cat.get('id', '?')}: needs 'deals' or 'groups'")
        for deal in deals_of(cat):
            label = f"{cat.get('id')}/{deal.get('name', '?')}"
            for key in REQUIRED:
                if not deal.get(key):
                    errors.append(f"{label}: missing '{key}'")
            if deal.get("status") not in STATUS:
                errors.append(f"{label}: status must be one of {', '.join(STATUS)}")
            if not str(deal.get("url", "")).startswith("https://"):
                errors.append(f"{label}: url must start with https://")
            if "|" in str(deal.get("description", "")) + str(deal.get("offer", "")):
                errors.append(f"{label}: '|' is not allowed (it breaks the table)")
            for path in deal.get("logos", []):
                if not (ROOT / path).is_file():
                    errors.append(f"{label}: logo file not found: {path}")
            if deal.get("name") in names:
                errors.append(f"{label}: duplicate deal name")
            names.add(deal.get("name"))
    for pick in data.get("top_picks", []):
        if pick not in names:
            errors.append(f"top_picks: '{pick}' is not a deal name")
    return errors


# ----------------------------------------------------------------- rendering

def render_stats(data: dict) -> str:
    deals = all_deals(data)
    live = sum(d["status"] == "live" for d in deals)
    # Plain markdown (no HTML wrapper) so GitHub renders the badge images.
    # The surrounding <div align="center"> in README.md centres them.
    badges = [
        f"[![deals live]({shield('deals live', f'{live} of {len(deals)}', '22c55e')})](#categories)",
        f"![black friday]({shield('black friday', fmt_date(data['black_friday']), '111827')})",
        f"![cyber monday]({shield('cyber monday', fmt_date(data['cyber_monday']), '6366f1')})",
        f"![last checked]({shield('last checked', fmt_date(data['last_updated']), '0ea5e9')})",
    ]
    return "\n" + " ".join(badges) + "\n"


def render_nav(data: dict) -> str:
    """Category boxes: one card per category with its deal count, centred."""
    cats = data["categories"]
    width = f"{100 // len(cats)}%"
    cells = []
    for cat in cats:
        count = len(deals_of(cat))
        cells.append(
            f'    <td align="center" width="{width}">\n'
            f'      <a href="#{cat["id"]}">{cat["emoji"]}<br><b>{cat["title"]}</b></a><br>\n'
            f"      <sub>{count} deals</sub>\n"
            f"    </td>"
        )
    return '<table align="center">\n  <tr>\n' + "\n".join(cells) + "\n  </tr>\n</table>"


def link_name(d: dict) -> str:
    """Underlined, bold product name linking to the deal."""
    return f'<a href="{d["url"]}"><ins><b>{d["name"]}</b></ins></a>'


def card_button(d: dict) -> str:
    """Top pick action: coupon button or Get Deal button, same size."""
    if code_soon(d):
        img = shield("Coming Soon", None, "f97316")
        return f'<a href="{d["url"]}"><img src="{img}" alt="Coming Soon" height="28"></a>'
    if d.get("code"):
        return coupon_button(d, 28)
    img = shield("Get Deal", None, "f97316")
    return f'<a href="{d["url"]}"><img src="{img}" alt="Get Deal" height="28"></a>'


def render_top_picks(data: dict) -> str:
    """Cards in rows of 4. Each card row is followed by a button row, so all
    buttons sit on the same line no matter how long the names are."""
    by_name = {d["name"]: d for d in all_deals(data)}
    picks = [by_name[n] for n in data.get("top_picks", [])]
    width = f"{100 // PICKS_PER_ROW}%"
    rows = []
    for i in range(0, len(picks), PICKS_PER_ROW):
        chunk = picks[i : i + PICKS_PER_ROW]
        info = [
            f'    <td align="center" valign="top" width="{width}">\n'
            f"      <sub>&nbsp;</sub><br>\n"  # breathing space above the logo
            f'      <a href="{d["url"]}">{logo(d, 44)}</a><br>\n'
            f"      {link_name(d)}<br>\n"
            f"      {offer_text(d)}<br>\n"
            f"      <sub>&nbsp;</sub>\n"  # and below the offer
            f"    </td>"
            for d in chunk
        ]
        # Spacer lines above and below keep each button centred in its cell.
        actions = [
            f'    <td align="center" valign="middle" width="{width}">'
            f"<sub>&nbsp;</sub><br>{card_button(d)}<br><sub>&nbsp;</sub></td>"
            for d in chunk
        ]
        rows.append("  <tr>\n" + "\n".join(info) + "\n  </tr>")
        rows.append("  <tr>\n" + "\n".join(actions) + "\n  </tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def render_row(d: dict) -> str:
    size = 28 if d.get("logos") else 32
    offer = offer_text(d)
    if d.get("valid"):
        offer += f"<br><sub>⌛ {d['valid']}</sub>"
    return (
        "  <tr>\n"
        f'    <td align="center">{logo(d, size)}<br>{link_name(d)}</td>\n'
        f"    <td>{d['description']}</td>\n"
        f'    <td align="center">{offer}</td>\n'
        f'    <td align="center" nowrap>{button(d)}</td>\n'
        f'    <td align="center">{"⏳&nbsp;Coming&nbsp;Soon" if code_soon(d) else STATUS[d["status"]]}</td>\n'
        "  </tr>"
    )


def render_table(deals: list[dict]) -> list[str]:
    """HTML table, so coupon cells can hold a copyable code block."""
    return [
        "<table>",
        "  <tr>",
        '    <th width="20%">Platform</th>',
        '    <th width="31%">Description</th>',
        '    <th width="15%">Deal</th>',
        '    <th width="24%">Coupon / Link</th>',
        '    <th width="10%">Status</th>',
        "  </tr>",
        *(render_row(d) for d in deals),
        "</table>",
        "",
    ]


def render_deals(data: dict) -> str:
    out: list[str] = []
    for cat in data["categories"]:
        out.append(f'<a id="{cat["id"]}"></a>\n')
        out.append(f"## {cat['emoji']} {cat['title']}\n")
        out.append(f"{cat['intro'].strip()}\n")
        for group in groups_of(cat):
            if group.get("title"):
                out.append(f"### {group.get('emoji', '')} {group['title']}".replace("###  ", "### ") + "\n")
            if group.get("intro"):
                out.append(f"> {group['intro']}\n")
            out.extend(render_table(group["deals"]))
        if cat.get("guide"):
            out.append(f"📖 **[{cat['guide']['text']}]({cat['guide']['url']})**: every Linux Foundation code, bundle and saving in one place.\n")
        out.append('<p align="right"><a href="#categories">⬆ Back to categories</a></p>\n')
    return "\n".join(out).rstrip() + "\n"


BLOCKS = {
    "STATS": render_stats,
    "NAV": render_nav,
    "TOP-PICKS": render_top_picks,
    "DEALS": render_deals,
    "FAQ": render_faq,
}


def build(readme: str, data: dict) -> str:
    for name, fn in BLOCKS.items():
        pattern = re.compile(rf"(<!-- {name}:START -->\n).*?(<!-- {name}:END -->)", re.S)
        if not pattern.search(readme):
            raise SystemExit(f"README.md is missing the <!-- {name}:START/END --> markers")
        content = fn(data).rstrip("\n") + "\n"
        readme = pattern.sub(lambda m: m.group(1) + content + m.group(2), readme)
    return readme


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if README.md is out of date")
    args = parser.parse_args()

    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print("deals.yml has problems:", *errors, sep="\n  - ", file=sys.stderr)
        return 1

    current = README.read_text(encoding="utf-8")
    new = build(current, data)

    if args.check:
        if new != current:
            print("README.md is out of date. Run: python scripts/build_readme.py", file=sys.stderr)
            return 1
        print("README.md is up to date.")
        return 0

    README.write_text(new, encoding="utf-8")
    print(f"README.md rebuilt with {len(all_deals(data))} deals.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

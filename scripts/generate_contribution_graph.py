import json
import os
import urllib.request
import html
from datetime import datetime

USERNAME = "SeelamRakesh"
OUTPUT = "contribution-graph.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        colors
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
  }
}
"""


def github_graphql():
    token = os.environ["GITHUB_TOKEN"]

    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": USERNAME}
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "SeelamRakesh-contribution-graph"
        }
    )

    with urllib.request.urlopen(request) as response:
        data = json.loads(response.read().decode("utf-8"))

    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))

    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def escape(value):
    return html.escape(str(value), quote=True)


def generate_svg(calendar):
    weeks = calendar["weeks"]
    colors = calendar["colors"]
    total = calendar["totalContributions"]

    # Tokyo-night inspired colors.
    background = "#0d1117"
    text = "#c9d1d9"
    muted = "#8b949e"
    border = "#30363d"

    # GitHub normally returns 5 contribution colors.
    # Use them directly so the graph follows GitHub's contribution levels.
    level_colors = colors

    cell = 12
    gap = 3
    step = cell + gap

    left = 42
    top = 48

    graph_width = len(weeks) * step
    graph_height = 7 * step

    width = left + graph_width + 20
    height = top + graph_height + 35

    svg = []

    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )

    # Background
    svg.append(
        f'<rect width="100%" height="100%" rx="10" fill="{background}"/>'
    )

    # Title
    svg.append(
        f'<text x="{left}" y="23" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="14" font-weight="600" fill="{text}">'
        f'{escape(total)} contributions in the last year'
        f'</text>'
    )

    # Weekday labels
    weekday_labels = {
        1: "Mon",
        3: "Wed",
        5: "Fri",
    }

    for weekday, label in weekday_labels.items():
        y = top + weekday * step + 10

        svg.append(
            f'<text x="0" y="{y}" '
            f'font-family="Arial, Helvetica, sans-serif" '
            f'font-size="9" fill="{muted}">'
            f'{label}'
            f'</text>'
        )

    # Contribution cells
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            weekday = day["weekday"]
            count = day["contributionCount"]

            x = left + week_index * step
            y = top + weekday * step

            if count == 0:
                color = level_colors[0]
            elif count <= 3:
                color = level_colors[1]
            elif count <= 6:
                color = level_colors[2]
            elif count <= 9:
                color = level_colors[3]
            else:
                color = level_colors[4]

            svg.append(
                f'<rect x="{x}" y="{y}" '
                f'width="{cell}" height="{cell}" rx="2" '
                f'fill="{escape(color)}">'
            )

            svg.append(
                f'<title>{escape(day["date"])}: '
                f'{escape(count)} contributions</title>'
            )

            svg.append('</rect>')

    # Legend
    legend_y = top + graph_height + 22

    svg.append(
        f'<text x="{left}" y="{legend_y}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="9" fill="{muted}">Less</text>'
    )

    for i, color in enumerate(level_colors):
        x = left + 30 + i * 16

        svg.append(
            f'<rect x="{x}" y="{legend_y - 9}" '
            f'width="11" height="11" rx="2" '
            f'fill="{escape(color)}"/>'
        )

    svg.append(
        f'<text x="{left + 30 + len(level_colors) * 16 + 3}" '
        f'y="{legend_y}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="9" fill="{muted}">More</text>'
    )

    svg.append("</svg>")

    return "\n".join(svg)


def main():
    print("Fetching GitHub contribution data...")
    calendar = github_graphql()

    print(
        f"Generating graph with "
        f"{calendar['totalContributions']} contributions..."
    )

    svg = generate_svg(calendar)

    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(svg)

    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()

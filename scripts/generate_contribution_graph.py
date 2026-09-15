import json
import os
import urllib.request
import html
from datetime import datetime, timedelta
from collections import defaultdict

USERNAME = "SeelamRakesh"
OUTPUT = "contribution-graph.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
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

    total = calendar["totalContributions"]

    # ---------------------------------------------------------
    # Collect all daily contribution data
    # ---------------------------------------------------------

    daily_data = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            daily_data.append({
                "date": datetime.strptime(day["date"], "%Y-%m-%d").date(),
                "count": day["contributionCount"]
            })

    # Sort by date
    daily_data.sort(key=lambda x: x["date"])

    if not daily_data:
        raise RuntimeError("No contribution data found.")

    # ---------------------------------------------------------
    # Keep approximately the latest 12 months
    # ---------------------------------------------------------

    latest_date = daily_data[-1]["date"]
    start_date = latest_date - timedelta(days=365)

    daily_data = [
        item for item in daily_data
        if item["date"] >= start_date
    ]

    # ---------------------------------------------------------
    # Aggregate contributions by month
    # ---------------------------------------------------------

    monthly = defaultdict(int)

    for item in daily_data:
        month_key = item["date"].strftime("%Y-%m")
        monthly[month_key] += item["count"]

    months = sorted(monthly.keys())

    # Keep latest 12 months
    months = months[-12:]

    values = [monthly[month] for month in months]

    # ---------------------------------------------------------
    # Graph styling
    # ---------------------------------------------------------

    background = "#0d1117"
    panel = "#161b22"
    text = "#f0f6fc"
    muted = "#8b949e"
    grid = "#30363d"
    line = "#58a6ff"
    area = "#1f6feb"

    # ---------------------------------------------------------
    # SVG dimensions
    # ---------------------------------------------------------

    width = 900
    height = 430

    left = 70
    right = 30
    top = 70
    bottom = 70

    graph_width = width - left - right
    graph_height = height - top - bottom

    max_value = max(values) if values else 1

    # Give the graph some breathing room
    if max_value == 0:
        max_value = 1

    # ---------------------------------------------------------
    # Coordinate helpers
    # ---------------------------------------------------------

    def x_position(index):
        if len(months) == 1:
            return left + graph_width / 2

        return left + (
            index * graph_width / (len(months) - 1)
        )

    def y_position(value):
        return (
            top
            + graph_height
            - (value / max_value) * graph_height
        )

    # ---------------------------------------------------------
    # Build SVG
    # ---------------------------------------------------------

    svg = []

    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="100%" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'role="img">'
    )

    # Background
    svg.append(
        f'<rect width="100%" height="100%" '
        f'rx="12" fill="{background}"/>'
    )

    # Panel
    svg.append(
        f'<rect x="20" y="20" '
        f'width="{width - 40}" '
        f'height="{height - 40}" '
        f'rx="12" '
        f'fill="{panel}" '
        f'stroke="{grid}" '
        f'stroke-width="1"/>'
    )

    # ---------------------------------------------------------
    # Title
    # ---------------------------------------------------------

    svg.append(
        f'<text x="{left}" y="45" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="20" '
        f'font-weight="600" '
        f'fill="{text}">'
        f'Contribution Graph'
        f'</text>'
    )

    svg.append(
        f'<text x="{width - right}" y="45" '
        f'text-anchor="end" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="14" '
        f'fill="{muted}">'
        f'{escape(total)} contributions'
        f'</text>'
    )

    # ---------------------------------------------------------
    # Y-axis grid lines
    # ---------------------------------------------------------

    grid_steps = 4

    for i in range(grid_steps + 1):

        value = round(max_value * i / grid_steps)
        y = y_position(value)

        svg.append(
            f'<line x1="{left}" y1="{y}" '
            f'x2="{width - right}" y2="{y}" '
            f'stroke="{grid}" '
            f'stroke-width="1" '
            f'opacity="0.65"/>'
        )

        svg.append(
            f'<text x="{left - 12}" y="{y + 4}" '
            f'text-anchor="end" '
            f'font-family="Arial, Helvetica, sans-serif" '
            f'font-size="11" '
            f'fill="{muted}">'
            f'{value}'
            f'</text>'
        )

    # ---------------------------------------------------------
    # X-axis
    # ---------------------------------------------------------

    svg.append(
        f'<line x1="{left}" y1="{top + graph_height}" '
        f'x2="{width - right}" y2="{top + graph_height}" '
        f'stroke="{grid}" '
        f'stroke-width="1"/>'
    )

    # ---------------------------------------------------------
    # Generate graph points
    # ---------------------------------------------------------

    points = []

    for index, value in enumerate(values):

        x = x_position(index)
        y = y_position(value)

        points.append((x, y))

    # ---------------------------------------------------------
    # Area under graph
    # ---------------------------------------------------------

    area_points = [
        f"{points[0][0]},{top + graph_height}"
    ]

    for x, y in points:
        area_points.append(f"{x},{y}")

    area_points.append(
        f"{points[-1][0]},{top + graph_height}"
    )

    svg.append(
        f'<polygon points="{" ".join(area_points)}" '
        f'fill="{area}" '
        f'opacity="0.18"/>'
    )

    # ---------------------------------------------------------
    # Main graph line
    # ---------------------------------------------------------

    line_points = " ".join(
        f"{x},{y}" for x, y in points
    )

    svg.append(
        f'<polyline points="{line_points}" '
        f'fill="none" '
        f'stroke="{line}" '
        f'stroke-width="3" '
        f'stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
    )

    # ---------------------------------------------------------
    # Data points + labels
    # ---------------------------------------------------------

    for index, ((x, y), value, month) in enumerate(
        zip(points, values, months)
    ):

        # Month label
        month_label = datetime.strptime(
            month, "%Y-%m"
        ).strftime("%b")

        svg.append(
            f'<text x="{x}" '
            f'y="{height - 38}" '
            f'text-anchor="middle" '
            f'font-family="Arial, Helvetica, sans-serif" '
            f'font-size="11" '
            f'fill="{muted}">'
            f'{month_label}'
            f'</text>'
        )

        # Data point
        svg.append(
            f'<circle cx="{x}" cy="{y}" '
            f'r="5" '
            f'fill="{background}" '
            f'stroke="{line}" '
            f'stroke-width="3">'
        )

        # Tooltip
        svg.append(
            f'<title>'
            f'{escape(month_label)}: '
            f'{escape(value)} contributions'
            f'</title>'
        )

        svg.append('</circle>')

    # ---------------------------------------------------------
    # Axis labels
    # ---------------------------------------------------------

    svg.append(
        f'<text x="{left}" y="{height - 12}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="10" '
        f'fill="{muted}">'
        f'Month'
        f'</text>'
    )

    svg.append(
        f'<text x="18" y="{top}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="10" '
        f'fill="{muted}">'
        f'Contributions'
        f'</text>'
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

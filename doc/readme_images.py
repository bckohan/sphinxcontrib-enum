"""
Regenerate the README screenshots from the built html documentation.

The screenshots are of the example tables on the documentation index page, rendered
in light and dark mode. Run with ``just readme-images``.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

DOC = Path(__file__).parent
INDEX = DOC / "build" / "html" / "index.html"
IMAGES = DOC / "images"

# image name -> index page tab label
TABS = {
    "dataclass": "Dataclass",
    "docstrings": "Docstrings",
    "enum-properties": "enum-properties",
}

SCALE = 2  # render at 2x for high density displays
MARGIN = 16  # css pixels around the rendered table, legend and buttons

# the parts of a rendered enum-table that are included in the screenshot
PARTS = ("table.enum-table", "dl.enum-table-legend", ".enum-table-downloads")


def _bounds(container) -> dict[str, float]:
    """The union of the bounding boxes of the table's parts, plus a margin."""
    boxes = [
        box
        for part in PARTS
        for box in [loc.bounding_box() for loc in container.locator(part).all()]
        if box
    ]
    left = min(box["x"] for box in boxes) - MARGIN
    top = min(box["y"] for box in boxes) - MARGIN
    right = max(box["x"] + box["width"] for box in boxes) + MARGIN
    bottom = max(box["y"] + box["height"] for box in boxes) + MARGIN
    return {"x": left, "y": top, "width": right - left, "height": bottom - top}


def main() -> None:
    if not INDEX.is_file():
        raise SystemExit(f"{INDEX} not found, build the html docs first.")
    IMAGES.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for scheme in ("light", "dark"):
            page = browser.new_page(
                viewport={"width": 1000, "height": 1200},
                color_scheme=scheme,
                device_scale_factor=SCALE,
            )
            page.goto(INDEX.as_uri())
            for name, label in TABS.items():
                page.locator(".sphinx-tabs-tab", has_text=label).first.click()
                container = page.locator(
                    ".sphinx-tabs-panel:not([hidden]) .enum-table-container"
                ).first
                container.scroll_into_view_if_needed()
                clip = _bounds(container)
                path = IMAGES / f"{name}-{scheme}.png"
                # clip is in viewport coordinates, like the bounding boxes
                page.screenshot(path=str(path), clip=clip)
                print(
                    f"{path.relative_to(DOC.parent)}: "
                    f"display width {round(clip['width'])}px"
                )
            page.close()
        browser.close()


if __name__ == "__main__":
    main()

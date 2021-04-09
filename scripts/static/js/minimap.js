// Minimap-related functions.

import { view, get_tid } from "./gui.js";
import { draw, update } from "./draw.js";
import { api } from "./api.js";

export { draw_minimap, update_minimap_visible_rect, move_minimap_view };


// Draw the full tree on a small div on the bottom-right ("minimap").
async function draw_minimap() {
    if (!view.minimap_show) {
        view.minimap_uptodate = false;
        return;
    }

    const size = view.tree_size;
    const mbw = 3;  // border-width from .minimap css
    if (view.is_circular) {
        if (div_minimap.offsetWidth < div_minimap.offsetHeight)
            div_minimap.style.height = `${div_minimap.offsetWidth - 2*mbw}px`;
        else
            div_minimap.style.width = `${div_minimap.offsetHeight - 2*mbw}px`;

        view.minimap_zoom.x = view.minimap_zoom.y =
            (div_minimap.offsetWidth - 2*mbw) / (view.rmin + size.width) / 2;
    }
    else {
        div_minimap.style.width = "10%";
        div_minimap.style.height = "60%";
        view.minimap_zoom.x = (div_minimap.offsetWidth - 2*mbw) / size.width;
        view.minimap_zoom.y = (div_minimap.offsetHeight - 2*mbw) / size.height;
    }

    let qs = `zx=${view.minimap_zoom.x}&zy=${view.minimap_zoom.y}`;
    if (view.is_circular)
        qs += `&drawer=CircSimple&rmin=${view.rmin}` +
              `&amin=${view.angle.min}&amax=${view.angle.max}`;
    else
        qs += "&drawer=Simple";

    const items = await api(`/trees/${get_tid()}/draw?${qs}`);

    const offset = -(div_minimap.offsetWidth - 2*mbw) / view.minimap_zoom.x / 2;
    const tl = view.is_circular ? {x: offset, y: offset} : {x: 0, y: 0};

    draw(div_minimap, items, tl, view.minimap_zoom);

    Array.from(div_minimap.getElementsByClassName("node")).forEach(
        e => e.remove());

    view.minimap_uptodate = true;

    update_minimap_visible_rect();
}


// Update the minimap's rectangle that represents the current view of the tree.
function update_minimap_visible_rect() {
    const [w_min, h_min] = [5, 5];  // minimum size of the rectangle
    const [round, min, max] = [Math.round, Math.min, Math.max];  // shortcuts

    // Transform all measures into "minimap units" (scaling accordingly).
    const mbw = 3, rbw = 1;  // border-width from .minimap and .visible_rect css
    const mw = div_minimap.offsetWidth - 2 * (mbw + rbw),    // minimap size
          mh = div_minimap.offsetHeight - 2 * (mbw + rbw);
    const wz = view.zoom, mz = view.minimap_zoom;
    const ww = round(mz.x/wz.x * div_tree.offsetWidth),  // viewport size (scaled)
          wh = round(mz.y/wz.y * div_tree.offsetHeight);
    let tx = round(mz.x * view.tl.x),  // top-left corner of visible area
        ty = round(mz.y * view.tl.y);  //   in tree coordinates (scaled)

    if (view.is_circular) {
        tx += mw / 2;
        ty += mh / 2;
    }

    const x = max(0, min(tx, mw)),  // clip tx to the interval [0, mw]
          y = max(0, min(ty, mh)),
          w = max(w_min, ww) + min(tx, 0),
          h = max(h_min, wh) + min(ty, 0);

    const rs = div_visible_rect.style;
    rs.left = `${div_minimap.offsetLeft + mbw + x}px`;
    rs.top = `${div_minimap.offsetTop + mbw + y}px`;
    rs.width = `${max(1, min(w, mw - x))}px`;
    rs.height = `${max(1, min(h, mh - y))}px`;
}


// Move the current tree view to the given point in the minimap.
function move_minimap_view(point) {
    const mbw = 3;  // border-width from .minimap css

    // Top-left pixel coordinates of the tree (0, 0) position in the minimap.
    let [x0, y0] = [div_minimap.offsetLeft + mbw, div_minimap.offsetTop + mbw];
    if (view.is_circular) {
        x0 += (div_minimap.offsetWidth - 2 * mbw) / 2;
        y0 += (div_minimap.offsetHeight - 2 * mbw) / 2;
    }

    // Size of the visible rectangle.
    const [w, h] = [div_visible_rect.offsetWidth, div_visible_rect.offsetHeight];

    view.tl.x = (point.x - w/2 - x0) / view.minimap_zoom.x;
    view.tl.y = (point.y - h/2 - y0) / view.minimap_zoom.y;
    // So the center of the visible rectangle will be where the mouse is.

    update();
}

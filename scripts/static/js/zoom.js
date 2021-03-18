// Zoom-related functions.

import { view } from "./gui.js";
import { update } from "./draw.js";
import { draw_minimap, update_minimap_visible_rect } from "./minimap.js";

export { zoom_around, zoom_into_box };


const zooming = {qz: {x: 1, y: 1}, timeout: undefined};


// Zoom the current view into the area defined by the given box, with a border
// marking the fraction of zoom-out (to see a bit the surroundings).
function zoom_into_box(box, border=0.10) {
    if (!view.is_circular) {
        const [x, y, w, h] = box;
        view.tl.x = x - border * w;
        view.tl.y = y - border * h;
        view.zoom.x = div_tree.offsetWidth / (w * (1 + 2 * border));
        view.zoom.y = div_tree.offsetHeight / (h * (1 + 2 * border));
    }
    else {
        const [r, a, dr, da] = box;
        const points = [[r, a], [r, a+da], [r+dr, a], [r+dr, a+da]];
        const xs = points.map(([r, a]) => r * Math.cos(a)),
              ys = points.map(([r, a]) => r * Math.sin(a));
        const [x, y] = [Math.min(...xs), Math.min(...ys)];
        const [w, h] = [Math.max(...xs) - x, Math.max(...ys) - y];
        const [zx, zy] = [div_tree.offsetWidth / w, div_tree.offsetHeight / h];
        if (zx < zy) {
            view.tl.x = x - border * w;
            view.zoom.x = view.zoom.y = zx / (1 + 2 * border);
            view.tl.y = y - (div_tree.offsetHeight / zx - h) / 2 - border * h;
        }
        else {
            view.tl.y = y - border * h;
            view.zoom.x = view.zoom.y = zy / (1 + 2 * border);
            view.tl.x = x - (div_tree.offsetWidth / zy - w) / 2 - border * w;
        }
    }
    update();
}

window.zoom_into_box = zoom_into_box;  // exposed so it can be called in onclick


// Zoom by a factor qz maintaining the given point on the screen.
function zoom_around(point, zoom_in, do_zoom_x=true, do_zoom_y=true) {
    const qz = (zoom_in ? 1.25 : 0.8);  // zoom change (quotient)

    if (view.is_circular)
        zoom_circular(point, qz, do_zoom_x, do_zoom_y);
    else
        zoom_rectangular(point, qz, do_zoom_x, do_zoom_y);
}


function zoom_circular(point, qz, do_zoom_x, do_zoom_y) {
    if (do_zoom_x) {  // all together
        const do_zoom = (do_zoom_x || do_zoom_y);
        zoom_rectangular(point, qz, do_zoom, do_zoom);
    }
    else {  // zoom by changing the angle
        const x = view.tl.x + point.x / view.zoom.x,
              y = view.tl.y + point.y / view.zoom.y;
        const angle = Math.atan2(y, x) * 180 / Math.PI;

        view.angle.min = angle + qz * (view.angle.min - angle);
        view.angle.max = angle + qz * (view.angle.max - angle);

        if (zooming.timeout)
            window.clearTimeout(zooming.timeout);

        zooming.timeout = window.setTimeout(() => {
            zooming.timeout = undefined;
            draw_minimap();
            update();
        }, 200);  // 200 ms until we actually update (if not cancelled before!)
    }
}


function zoom_rectangular(point, qz, do_zoom_x, do_zoom_y) {
    if (do_zoom_x) {
        const zoom_new = qz * view.zoom.x;
        view.tl.x += (1 / view.zoom.x - 1 / zoom_new) * point.x;
        view.zoom.x = zoom_new;
        zooming.qz.x *= qz;
    }

    if (do_zoom_y) {
        const zoom_new = qz * view.zoom.y;
        view.tl.y += (1 / view.zoom.y - 1 / zoom_new) * point.y;
        view.zoom.y = zoom_new;
        zooming.qz.y *= qz;
    }

    if (do_zoom_x || do_zoom_y)
        smooth_zoom(point);
}


// Perform zoom by scaling the svg, and really update it only after a timeout.
function smooth_zoom(point) {
    if (zooming.timeout)
        window.clearTimeout(zooming.timeout);

    const g = div_tree.children[0].children[0];
    g.setAttribute("transform",
        `scale(${zooming.qz.x}, ${zooming.qz.y}) ` +
        `translate(${(1 / zooming.qz.x - 1) * point.x}
                   ${(1 / zooming.qz.y - 1) * point.y})`);

    if (view.minimap_show)
        update_minimap_visible_rect();

    zooming.timeout = window.setTimeout(() => {
        zooming.qz.x = zooming.qz.y = 1;
        zooming.timeout = undefined;
        update();
    }, 200);  // 200 ms until we actually update (if not cancelled before!)
}

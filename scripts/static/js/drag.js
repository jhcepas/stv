// Drag-related functions.

import { view, datgui } from "./gui.js";
import { update_minimap_visible_rect } from "./minimap.js";
import { update_tree } from "./draw.js";

export { drag_start, drag_stop, drag_move };


const dragging = {p0: {x: 0, y: 0}, element: undefined, moved: false};



function drag_start(point, element) {
    div_tree.style.cursor = div_visible_rect.style.cursor = "grabbing";
    dragging.p0 = point;
    dragging.element = element;
}


function drag_stop() {
    if (dragging.element === undefined)
        return;

    div_tree.style.cursor = "auto";
    div_visible_rect.style.cursor = "grab";

    if (dragging.moved) {
        update_tree();
        dragging.moved = false;
    }

    dragging.element = undefined;
}


function drag_move(point, movement) {
    if (dragging.element) {
        dragging.moved = true;

        if (view.update_on_drag)
            update_tree();

        const [scale_x, scale_y] = get_drag_scale();
        view.tl.x += scale_x * movement.x;
        view.tl.y += scale_y * movement.y;

        let dx = point.x - dragging.p0.x,
            dy = point.y - dragging.p0.y;

        if (dragging.element === div_visible_rect) {
            dx *= -view.zoom.x / view.minimap_zoom.x;
            dy *= -view.zoom.y / view.minimap_zoom.y;
        }

        const g = div_tree.children[0].children[0];
        g.setAttribute("transform", `translate(${dx} ${dy})`);

        datgui.updateDisplay();  // update the info box on the top-right

        if (view.minimap_show)
            update_minimap_visible_rect();
    }
}

function get_drag_scale() {
    if (dragging.element === div_tree)
        return [-1 / view.zoom.x, -1 / view.zoom.y];
    else // dragging.element === div_visible_rect
        return [1 / view.minimap_zoom.x, 1 / view.minimap_zoom.y];
}
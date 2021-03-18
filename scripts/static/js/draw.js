// Functions related to updating (drawing) the view.

import { view, datgui, api, get_tid, on_box_click } from "./gui.js";
import { update_minimap_visible_rect } from "./minimap.js";
import { add_search_boxes } from "./search.js";
import { on_box_contextmenu } from "./contextmenu.js";
import { zoom_towards_box } from "./zoom.js";

export { update, update_tree, create_rect, create_asec, draw };


// Update the view of all elements (gui, tree, minimap).
function update() {
    datgui.updateDisplay();  // update the info box on the top-right

    update_tree();

    if (view.minimap_show)
        update_minimap_visible_rect();
}


// Ask the server for a tree in the new defined region, and draw it.
async function update_tree() {
    const [zx, zy] = [view.zoom.x, view.zoom.y];
    const [x, y] = [view.tl.x, view.tl.y];
    const [w, h] = [div_tree.offsetWidth / zx, div_tree.offsetHeight / zy];

    div_tree.style.cursor = "wait";

    let qs = `drawer=${view.drawer}&min_size=${view.min_size}&` +
             `zx=${zx}&zy=${zy}&x=${x}&y=${y}&w=${w}&h=${h}`;
    if (view.is_circular)
        qs += `&rmin=${view.rmin}&amin=${view.angle.min}&amax=${view.angle.max}`;

    const items = await api(`/trees/${get_tid()}/draw?${qs}`);

    save_nodeboxes(items);

    draw(div_tree, items, view.tl, view.zoom);

    if (view.drawer.startsWith("Align")) {
        const aitems = await api(`/trees/${get_tid()}/draw?${qs}&aligned`);
        draw(div_aligned, aitems, {x: 0, y: view.tl.y}, view.zoom);
    }

    for (let search_text in view.searches)
        add_search_boxes(search_text);

    div_tree.style.cursor = "auto";
}


// From all the graphic items received, save the nodeboxes in the global
// variable view.nodes. We can use them later to count the total number of
// nodes shown, and to color the searched nodes that are currently visible.
function save_nodeboxes(items) {
    view.nodes.boxes = {};
    view.nodes.n = 0;
    items.forEach(item => {
        if (is_nodebox(item)) {
            const [shape, box, type, name, properties, node_id] = item;
            view.nodes.boxes[node_id] = box;
            view.nodes.n += 1;
        }
    });
}

function is_nodebox(item) {
    return (is_rect(item) || is_asec(item)) && item[2] === "node";
}

const is_rect = item => item[0] === 'r';  // is it a rectangle?
const is_asec = item => item[0] === 's';  // is it an annular sector?


// Drawing.

function create_svg_element(name, attrs) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [attr, value] of Object.entries(attrs))
        element.setAttributeNS(null, attr, value);
    return element;
}


function create_rect(box, tl, zx=1, zy=1, type="") {
    const [x, y, w, h] = box;

    return create_svg_element("rect", {
        "class": "box " + type,
        "x": zx * (x - tl.x), "y": zy * (y - tl.y),
        "width": zx * w, "height": zy * h,
        "stroke": view.rect_color,
    });
}


// Return a newly-created svg annular sector, described by box and with zoom z.
function create_asec(box, tl, z=1, type="") {
    const [r, a, dr, da] = box;
    const large = da > Math.PI ? 1 : 0;
    const p00 = cartesian_shifted(r, a, tl, z),
          p01 = cartesian_shifted(r, a + da, tl, z),
          p10 = cartesian_shifted(r + dr, a, tl, z),
          p11 = cartesian_shifted(r + dr, a + da, tl, z);

    return create_svg_element("path", {
        "class": "box " + type,
        "d": `M ${p00.x} ${p00.y}
              L ${p10.x} ${p10.y}
              A ${z * (r + dr)} ${z * (r + dr)} 0 ${large} 1 ${p11.x} ${p11.y}
              L ${p01.x} ${p01.y}
              A ${z * r} ${z * r} 0 ${large} 0 ${p00.x} ${p00.y}`,
        "fill": view.box_color,
    });
}

function cartesian_shifted(r, a, tl, z) {
    return {x: z * (r * Math.cos(a) - tl.x),
            y: z * (r * Math.sin(a) - tl.y)};
}


function create_line(p1, p2, tl, zx, zy) {
    const [x1, y1] = [zx * (p1[0] - tl.x), zy * (p1[1] - tl.y)],
          [x2, y2] = [zx * (p2[0] - tl.x), zy * (p2[1] - tl.y)];

    return create_svg_element("line", {
        "class": "line",
        "x1": x1, "y1": y1,
        "x2": x2, "y2": y2,
        "stroke": view.line.color,
    });
}


function create_arc(p1, p2, large, tl, z=1) {
    const [x1, y1] = p1,
          [x2, y2] = p2;
    const r = z * Math.sqrt(x1*x1 + y1*y1);
    const n1 = {x: z * (x1 - tl.x), y: z * (y1 - tl.y)},
          n2 = {x: z * (x2 - tl.x), y: z * (y2 - tl.y)};

    return create_svg_element("path", {
        "class": "line",
        "d": `M ${n1.x} ${n1.y} A ${r} ${r} 0 ${large} 1 ${n2.x} ${n2.y}`,
        "stroke": view.line.color,
    });
}


function create_text(text, fs, point, tl, zx, zy, type) {
    const [x, y] = [zx * (point[0] - tl.x), zy * (point[1] - tl.y)];

    const t = create_svg_element("text", {
        "class": "text " + type,
        "x": x, "y": y,
        "font-size": `${fs}px`,
    });

    t.appendChild(document.createTextNode(text));

    return t;
}


// Return svg transformation to flip the given text.
function flip(text) {
    const bbox = text.getBBox();  // NOTE: text must be already in the DOM
    return ` rotate(180, ${bbox.x + bbox.width/2}, ${bbox.y + bbox.height/2})`;
}


// Append a svg to the given element, with all the items in the list drawn.
function draw(element, items, tl, zoom) {
    const svg = create_svg_element("svg", {
        "width": element.offsetWidth,
        "height": element.offsetHeight,
    });

    if (element.children.length > 0)
        element.children[0].replaceWith(svg);
    else
        element.appendChild(svg);

    const g = create_svg_element("g", {});

    svg.appendChild(g);

    items.forEach(item => draw_item(g, item, tl, zoom));
}


// Append to g the graphical (svg) element corresponding to a drawer item.
function draw_item(g, item, tl, zoom) {
    // item looks like ['r', ...] for a rectangle, etc.

    const [zx, zy] = [zoom.x, zoom.y];  // shortcut

    if (item[0] === 'r' || item[0] === 's') {  // rectangle or annular sector
        const [shape, box, type, name, properties, node_id] = item;

        const b = shape === 'r' ?
            create_rect(box, tl, zx, zy, type) :
            create_asec(box, tl, zx, type);

        g.appendChild(b);

        b.addEventListener("click", event =>
            on_box_click(event, box, node_id));
        b.addEventListener("contextmenu", event =>
            on_box_contextmenu(event, box, name, properties, node_id));
        b.addEventListener("wheel", event =>
            on_wheel(event, box), {passive: false});

        if (name.length > 0 || Object.entries(properties).length > 0)
            b.appendChild(create_tooltip(name, properties));
    }
    else if (item[0] === 'l') {  // line
        const [ , p1, p2] = item;

        g.appendChild(create_line(p1, p2, tl, zx, zy));
    }
    else if (item[0] === 'c') {  // arc (part of a circle)
        const [ , p1, p2, large] = item;

        g.appendChild(create_arc(p1, p2, large, tl, zx));
    }
    else if (item[0] === 't') {  // text
        const [ , text, point, fs, type] = item;
        const font_size = font_adjust(type, zy * fs);

        const t = create_text(text, font_size, point, tl, zx, zy, type);

        g.appendChild(t);

        if (view.is_circular) {
            const [x, y] = point;
            const angle = Math.atan2(y, x) * 180 / Math.PI;

            t.setAttributeNS(null, "transform",
                `rotate(${angle}, ${zx * (x - tl.x)}, ${zy * (y - tl.y)})` +
                ((angle < -90 || angle > 90) ? flip(t) : ""));
        }
    }
    else if (item[0] === 'a') {  // array
        const [ , box, a] = item;
        const [x0, y0, dx0, dy0] = box;
        const dx = dx0 / a.length / zx;

        for (let i = 0, x = 0; i < a.length; i++, x+=dx) {
            const r = create_rect([x, y0, dx, dy0], tl, zx, zy, "array");
            r.style.stroke = `hsl(${a[i]}, 100%, 50%)`;
            g.appendChild(r);
        }
    }
}

// Mouse wheel -- zoom in/out (instead of scrolling).
function on_wheel(event, box) {
    event.preventDefault();

    const point = {x: event.pageX, y: event.pageY};
    const zoom_in = event.deltaY < 0;
    const [do_zoom_x, do_zoom_y] = [!event.ctrlKey, !event.altKey];

    zoom_towards_box(box, point, zoom_in, do_zoom_x, do_zoom_y);
}


function create_tooltip(name, properties) {
    const title = create_svg_element("title", {});
    const text = name + "\n" +
        Object.entries(properties).map(x => x[0] + ": " + x[1]).join("\n");
    title.appendChild(document.createTextNode(text));
    return title;
}


// Return the font size adjusted for the given type of text.
function font_adjust(type, fs) {
    if (type === "name")
        return fs;  // no adjustments
    else
        return Math.min(view.font_size_max, fs);
    // NOTE: we could modify the font size depending on other kinds of text
    // (limiting their minimum and maximum sizes if appropriate, for example).
}

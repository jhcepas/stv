// Functions related to updating (drawing) the view.

import { view, datgui, get_tid, on_box_click, on_box_wheel } from "./gui.js";
import { update_minimap_visible_rect } from "./minimap.js";
import { colorize_searches, get_search_class } from "./search.js";
import { on_box_contextmenu } from "./contextmenu.js";
import { api } from "./api.js";

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

    try {
        const items = await api(`/trees/${get_tid()}/draw?${qs}`);

        save_nodeboxes(items);

        draw(div_tree, items, view.tl, view.zoom);

        colorize_searches();

        if (view.drawer.startsWith("Align")) {
            const aitems = await api(`/trees/${get_tid()}/draw?${qs}&aligned`);
            draw(div_aligned, aitems, {x: 0, y: view.tl.y}, view.zoom);
        }
    }
    catch (ex) {
        Swal.fire({
            html: `When drawing: ${ex.message}`,
            icon: "error",
        });
    }

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
            const [shape, box, name, properties, node_id] = item;
            view.nodes.boxes[node_id] = box;
            view.nodes.n += 1;
        }
    });
}

function is_nodebox(item) {
    return item[0] === "box" && item[4].length > 0;
}


// Drawing.

// Append a svg to the given element, with all the items in the list drawn.
async function draw(element, items, tl, zoom) {
    const svg = create_svg_element("svg", {
        "width": element.offsetWidth,
        "height": element.offsetHeight,
    });

    if (element.children.length > 0)
        element.children[0].replaceWith(svg);
    else
        element.appendChild(svg);

    const g = create_svg_element("g", {});

    items.forEach(item => draw_item(g, item, tl, zoom));

    svg.appendChild(g);

    if (view.is_circular)
        fix_text_orientations();
}


// Append to g the graphical (svg) element corresponding to a drawer item.
function draw_item(g, item, tl, zoom) {
    // item looks like ["line", ...] for a line, etc.

    const [zx, zy] = [zoom.x, zoom.y];  // shortcut

    if (item[0] === "box") {
        const [ , box, name, properties, node_id, result_of] = item;

        const b = create_box(box, tl, zx, zy, result_of);

        b.addEventListener("click", event =>
            on_box_click(event, box, node_id));
        b.addEventListener("contextmenu", event =>
            on_box_contextmenu(event, box, name, properties, node_id));
        b.addEventListener("wheel", event =>
            on_box_wheel(event, box), {passive: false});

        if (name.length > 0 || Object.entries(properties).length > 0)
            b.appendChild(create_tooltip(name, properties));

        g.appendChild(b);
    }
    else if (item[0] === "cone") {
        const [ , box] = item;

        g.appendChild(create_cone(box, tl, zx, zy));
    }
    else if (item[0] === "line") {
        const [ , p1, p2, type, parent_of] = item;

        g.appendChild(create_line(p1, p2, tl, zx, zy, type, parent_of));
    }
    else if (item[0] === "arc") {
        const [ , p1, p2, large, type] = item;

        g.appendChild(create_arc(p1, p2, large, tl, zx, type));
    }
    else if (item[0] === "text") {
        const [ , text, point, fs, type] = item;
        const font_size = font_adjust(type, zy * fs);

        const t = create_text(text, font_size, point, tl, zx, zy, type);

        if (view.is_circular) {
            const [x, y] = point;
            const angle = Math.atan2(y, x) * 180 / Math.PI;
            t.setAttributeNS(null, "transform",
                `rotate(${angle}, ${zx * (x - tl.x)}, ${zy * (y - tl.y)})`);
        }

        g.appendChild(t);
    }
    else if (item[0] === "array") {
        const [ , box, a] = item;
        const [x0, y0, dx0, dy0] = box;
        const dx = dx0 / a.length / zx;

        const [y, dy] = pad(y0, dy0, view.array.padding);

        for (let i = 0, x = 0; i < a.length; i++, x+=dx) {
            const r = create_rect([x, y, dx, dy], tl, zx, zy, "array");
            r.style.stroke = `hsl(${a[i]}, 100%, 50%)`;
            g.appendChild(r);
        }
    }
}


// Transform the interval [y0, y0+dy0] into one padded with the given fraction.
function pad(y0, dy0, fraction) {
    const dy = dy0 * (1 - fraction);
    return [y0 + (dy0 - dy)/2, dy]
}


function create_svg_element(name, attrs) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [attr, value] of Object.entries(attrs))
        element.setAttributeNS(null, attr, value);
    return element;
}


// Return a box (rectangle or annular sector).
function create_box(box, tl, zx, zy, result_of) {
    const classes = "node " +
        result_of.map(text => get_search_class(text, "results")).join(" ");

    if (view.is_circular)
        return create_asec(box, tl, zx, classes);
    else
        return create_rect(box, tl, zx, zy, classes);
}


function create_rect(box, tl, zx=1, zy=1, type="") {
    const [x, y, w, h] = box;

    return create_svg_element("rect", {
        "class": "box " + type,
        "x": zx * (x - tl.x), "y": zy * (y - tl.y),
        "width": zx * w, "height": zy * h,
    });
}


// Return a svg annular sector, described by box and with zoom z.
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
    });
}

function cartesian_shifted(r, a, tl, z) {
    return {x: z * (r * Math.cos(a) - tl.x),
            y: z * (r * Math.sin(a) - tl.y)};
}


// Return a cone (collapsed version of a box).
function create_cone(box, tl, zx, zy) {
    if (view.is_circular)
        return create_circ_cone(box, tl, zx);
    else
        return create_rect_cone(box, tl, zx, zy);
}


// Return a svg horizontal cone.
function create_rect_cone(box, tl, zx=1, zy=1) {
    const [x, y, w, h] = transform(box, tl, zx, zy);

    return create_svg_element("path", {
        "class": "outline",
        "d": `M ${x} ${y + h/2}
              L ${x + w} ${y}
              L ${x + w} ${y + h}
              L ${x} ${y + h/2}`,
    });
}

// Return the box translated (from tl) and scaled.
function transform(box, tl, zx, zy) {
    const [x, y, w, h] = box;
    return [zx * (x - tl.x), zy * (y - tl.y), zx * w, zy * h];
}


// Return a svg cone in the direction of an annular sector.
function create_circ_cone(box, tl, z=1) {
    const [r, a, dr, da] = box;
    const large = da > Math.PI ? 1 : 0;
    const p0 = cartesian_shifted(r, a + da/2, tl, z),
          p10 = cartesian_shifted(r + dr, a, tl, z),
          p11 = cartesian_shifted(r + dr, a + da, tl, z);

    return create_svg_element("path", {
        "class": "outline",
        "d": `M ${p0.x} ${p0.y}
              L ${p10.x} ${p10.y}
              A ${z * (r + dr)} ${z * (r + dr)} 0 ${large} 1 ${p11.x} ${p11.y}
              L ${p0.x} ${p0.y}`,
    });
}


// Create an element that, appended to a svg element (normally a box), will
// make it show a tooltip showing nicely the contents of name and properties.
function create_tooltip(name, properties) {
    const title = create_svg_element("title", {});
    const text = (name ? name : "(unnamed)") + "\n" +
        Object.entries(properties).map(x => x[0] + ": " + x[1]).join("\n");
    title.appendChild(document.createTextNode(text));
    return title;
}


function create_line(p1, p2, tl, zx, zy, type, parent_of) {
    const [x1, y1] = [zx * (p1[0] - tl.x), zy * (p1[1] - tl.y)],
          [x2, y2] = [zx * (p2[0] - tl.x), zy * (p2[1] - tl.y)];

    const classes = "line " + type + " " +
        parent_of.map(text => get_search_class(text, "parents")).join(" ");

    return create_svg_element("line", {
        "class": classes,
        "x1": x1, "y1": y1,
        "x2": x2, "y2": y2,
        "stroke": view.line.color,
    });
}


function create_arc(p1, p2, large, tl, z=1, type) {
    const [x1, y1] = p1,
          [x2, y2] = p2;
    const r = z * Math.sqrt(x1*x1 + y1*y1);
    const n1 = {x: z * (x1 - tl.x), y: z * (y1 - tl.y)},
          n2 = {x: z * (x2 - tl.x), y: z * (y2 - tl.y)};

    return create_svg_element("path", {
        "class": "line " + type,
        "d": `M ${n1.x} ${n1.y} A ${r} ${r} 0 ${large} 1 ${n2.x} ${n2.y}`,
        "stroke": view.line.color,
    });
}


function create_text(text, fs, point, tl, zx, zy, type) {
    const [x, y] = [zx * (point[0] - tl.x), zy * (point[1] - tl.y)];

    const dx = (type === "name") ? view.text_padding * fs / 100 : 0;

    const t = create_svg_element("text", {
        "class": "text " + type,
        "x": x + dx, "y": y,
        "font-size": `${fs}px`,
    });

    t.appendChild(document.createTextNode(text));

    return t;
}


// Flip all the texts in circular representation that look upside-down.
// NOTE: getBBox() is very expensive and requires text to be already in the DOM.
async function fix_text_orientations() {
    const texts = Array.from(div_tree.getElementsByClassName("text"))
        .filter(is_upside_down);

    texts.sort((a, b) => get_font_size(b) - get_font_size(a));

    texts.slice(0, 1000).forEach(t => flip_with_bbox(t, t.getBBox()));
    texts.slice(1000).forEach(t => flip_with_bbox(t, get_approx_BBox(t)));
}

function is_upside_down(text) {
    const angle = text.transform.baseVal[0].angle;
    return angle < -90 || angle > 90;
}

function get_font_size(text) {
    return Number(text.getAttribute('font-size').slice(0, -2));  // "px"
}


// Apply svg transformation to flip the given text (bounded by bbox).
function flip_with_bbox(text, bbox) {
    const rot180 = text.ownerSVGElement.createSVGTransform();
    rot180.setRotate(180, bbox.x + bbox.width/2, bbox.y + bbox.height/2);
    text.transform.baseVal.appendItem(rot180);
}


// Return an approximate bounding box for the given svg text.
function get_approx_BBox(text) {
    const height = get_font_size(text);
    const x = Number(text.getAttribute("x"));
    const y = Number(text.getAttribute("y")) - height;
    const width = text.childNodes[0].length * height / 1.5;
    return {x, y, width, height};
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

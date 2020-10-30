'use strict';

document.addEventListener("DOMContentLoaded", () => {
  create_minimap();
  update();
});


// Variables shown on the top-right gui (using dat.gui).
const view = {
  tl: {x: 0, y: 0},  // in-tree coordinates of the top-left corner of the view
  pos: {x: 0, y: 0},  // in-tree current pointer position
  zoom: 10,
  update_on_drag: true,
  drag: {x0: 0, y0: 0, element: undefined},  // used when dragging
  select_text: false,
  line_color: "#000",
  rect_color: "#0A0",
  font_color: "#00A",
  font_family: "sans-serif",
  font_size_auto: true,
  font_size_scroller: undefined,
  font_size: 10,
  minimap_show: true,
  minimap_zoom: 1
};

const [style_line, style_rect, style_font] = [1, 2, 3].map(i =>
  document.styleSheets[0].cssRules[i].style);  // shortcut

const dgui = new dat.GUI();
dgui.add(view.pos, "x").listen();
dgui.add(view.pos, "y").listen();

const dgui_ctl = dgui.addFolder("control");
dgui_ctl.add(view.tl, "x").name("top-left x").onChange(update);
dgui_ctl.add(view.tl, "y").name("top-left y").onChange(update);
dgui_ctl.add(view, "zoom", 1, 1000).onChange(update);
dgui_ctl.add(view, "update_on_drag").name("continuous dragging");
dgui_ctl.add(view, "select_text").name("select text").onChange(() =>
  style_font.userSelect = (view.select_text ? "text" : "none"));

const dgui_style = dgui.addFolder("style");
dgui_style.addColor(view, "line_color").name("line color").onChange(() =>
  style_line.stroke = view.line_color);
dgui_style.addColor(view, "rect_color").name("rectangle color").onChange(() =>
  style_rect.stroke = view.rect_color);
dgui_style.addColor(view, "font_color").name("text color").onChange(() =>
  style_font.fill = view.font_color);
dgui_style.add(view, "font_family", ["sans-serif", "serif", "monospace"])
  .name("font").onChange(() => style_font.fontFamily = view.font_family);
dgui_style.add(view, "font_size_auto").name("automatic size").onChange(() => {
  style_font.fontSize = (view.font_size_auto ? "" : `${view.font_size}px`);
  if (view.font_size_auto && view.font_size_scroller)
    view.font_size_scroller.remove();
  else
    view.font_size_scroller = create_font_size_scroller();
});

function create_font_size_scroller() {
  return dgui_style.add(view, "font_size", 1, 50).name("font size")
    .onChange(() => style_font.fontSize = `${view.font_size}px`);
}

const dgui_minimap = dgui.addFolder("minimap");
dgui_minimap.add(view, "minimap_show").name("active").onChange(() => {
    const status = (view.minimap_show ? "visible" : "hidden");
    div_minimap.style.visibility = div_visible_rect.style.visibility = status;
    if (view.minimap_show)
      update_minimap_visible_rect();
  });


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const zr = (event.deltaY < 0 ? 1.25 : 0.8);  // zoom change (ratio)
  if (is_valid_zoom_change(zr)) {
    const zoom_new =  zr * view.zoom;
    const a = 1 / view.zoom - 1 / zoom_new;
    view.tl.x += a * event.pageX;
    view.tl.y += a * event.pageY;
    view.zoom = zoom_new;
    update();
  }
}, {passive: false});  // chrome now uses passive=true otherwise

function is_valid_zoom_change(zr) {
  return (zr > 1 && view.zoom < 1000) || (zr < 1 && view.zoom > 1);
}


// Mouse down -- select text, or move in minimap, or start dragging.
document.addEventListener("mousedown", event => {
  if (view.select_text) {
    ;  // if by clicking we can select text, don't do anything else
  }
  else if (div_visible_rect.contains(event.target)) {
    view.drag.element = div_visible_rect;
    drag_start(event);
  }
  else if (div_minimap.contains(event.target)) {
    move_minimap_view(event);
  }
  else if (div_tree.contains(event.target)) {
    view.drag.element = div_tree;
    drag_start(event);
  }
});

document.addEventListener("mouseup", event => {
  if (view.drag.element)
    drag_stop(event);

  view.drag.element = undefined;
});

document.addEventListener("mousemove", event => {
  update_pointer_pos(event);

  if (view.drag.element && view.update_on_drag) {
    drag_stop(event);
    drag_start(event);
  }
});

function drag_start(event) {
  view.drag.x0 = event.pageX;
  view.drag.y0 = event.pageY;
}

function drag_stop(event) {
  const dx = event.pageX - view.drag.x0,  // mouse position increment
        dy = event.pageY - view.drag.y0;

  if (dx != 0 || dy != 0) {
    const scale = get_drag_scale();
    view.tl.x += scale * dx;
    view.tl.y += scale * dy;
    update();
  }
}

function get_drag_scale() {
  if (view.drag.element === div_tree)
    return -1 / view.zoom;
  else if (view.drag.element === div_visible_rect)
    return 1 / view.minimap_zoom;
  else
    console.log(`Cannot find dragging scale for ${view.drag.element}.`);
}


function move_minimap_view(event) {
  // Top-left pixel coordinates of the tree (0, 0) position.
  const [x0, y0] = [div_minimap.offsetLeft + 6, div_minimap.offsetTop + 6];

  // Center of the visible rectangle (in px).
  const cx = view.minimap_zoom / view.zoom * div_tree.offsetWidth / 2,
        cy = view.minimap_zoom / view.zoom * div_tree.offsetHeight / 2;

  view.tl.x = (event.pageX - x0) / view.minimap_zoom - cx;
  view.tl.y = (event.pageY - y0) / view.minimap_zoom - cy;

  update();
}


// Update the coordinates of the pointer, as shown in the top-right gui.
function update_pointer_pos(event) {
  view.pos.x = view.tl.x + event.pageX / view.zoom;
  view.pos.y = view.tl.y + event.pageY / view.zoom;
}


function update() {
  dgui.updateDisplay();  // updates the info box on the top-right gui

  update_tree();

  if (view.minimap_show)
    update_minimap_visible_rect();
}


// Ask the server for a tree in the new defined region, and draw it.
function update_tree() {
  const x = view.zoom * Math.max(0, view.tl.x),
        y = view.zoom * Math.max(0, view.tl.y),
        w = div_tree.offsetWidth - Math.max(0, - view.zoom * view.tl.x),
        h = div_tree.offsetHeight - Math.max(0, - view.zoom * view.tl.y);

  fetch(`/get_scene_region/${view.zoom},${x},${y},${w},${h}/`)
    .then(response => response.json())
    .then(data => draw(div_tree, data.items))
    .catch(error => console.log(error));
}


// Append a svg to the given element, with all the items in the list drawn.
function draw(element, items) {
  const [x, y] = [view.zoom * view.tl.x, view.zoom * view.tl.y],
        [w, h] = [element.offsetWidth, element.offsetHeight];

  element.innerHTML = `
    <svg viewBox="${x} ${y} ${w} ${h}" width="${w}" height="${h}">
      ${items.map(item2svg).join("\n")}
    </svg>`;
}


// Return the graphical (svg) element corresponding to an ete item.
function item2svg(item) {
  // ete items look like ['r', ...] for a rectangle, etc.
  if (item[0] === 'r') {       // rectangle
    const [ , x, y, w, h] = item;
    return `<rect class="rect" x="${x}" y="${y}" width="${w}" height="${h}"
                  fill="none" stroke="${view.rect_color}"/>`;
  }
  else if (item[0] === 'l') {  // line
    const [ , x1, y1, x2, y2] = item;
    return `<line class="line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                  stroke="${view.line_color}"/>`;
  }
  else if (item[0] === 't') {  // text
    const [ , x, y, w, h, txt] = item;
    const fs = Math.ceil(1.5 * w / txt.length);  // fs * length = w (approx.)
    return `<text class="text" x="${x}" y="${y+fs}" color="${view.font_color}"
                  font-size="${fs}px">${txt}</text>`;
    // If we wanted to use the exact width of the item, we could add:
    //   textLength="${w}px"
  }
  else {
    console.log(`Got unknown item of type: ${item[0]}`);
    return "";
  }
}


// Create a drawing on the bottom-right of the full tree ("minimap").
function create_minimap() {
  fetch('/size/')
    .then(response => response.json())
    .then(size => create_minimap_with_size(size))
    .catch(error => console.log(error));
}

function create_minimap_with_size(size) {
  const [tw, th] = [size.width, size.height];  // tree width and height
  const [w_min, h_min] = [20, 20];  // minimum size of the minimap
  const w_max = 0.2 * window.innerWidth,
        h_max = 0.8 * window.innerHeight;  // maximum size of the minimap
  const zoom = Math.min(1, w_max / tw, h_max / th);  // zoom that accomodates

  // Adjust minimap's size.
  div_minimap.style.width = `${Math.ceil(Math.max(w_min, zoom * tw))}px`;
  div_minimap.style.height = `${Math.ceil(Math.max(h_min, zoom * th))}px`;

  view.minimap_zoom = zoom;

  update_minimap_visible_rect();

  fetch(`/get_scene_region/${zoom},0,0,${zoom * tw},${zoom * th}/`)
    .then(response => response.json())
    .then(resp_data => draw(div_minimap, resp_data.items))
    .catch(error => console.log(error));
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
  const ww = round(mz / wz * div_tree.offsetWidth),  // tree size (scaled)
        wh = round(mz / wz * div_tree.offsetHeight);
  const tx = round(mz * view.tl.x),  // top-left corner of visible area
        ty = round(mz * view.tl.y);  //   in tree coordinates (scaled)

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

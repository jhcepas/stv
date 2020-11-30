'use strict';


// Global variables related to the current view on the tree.
// Most will be shown on the top-right gui (using dat.gui).
const view = {
  pos: {x: 0, y: 0},  // in-tree current pointer position
  tree_name: "HmuY.aln2",
  tree_id: 4,
  show_tree_info: () => window.location.href = `/trees/${view.tree_id}`,
  upload_tree: () => window.location.href = "upload_tree.html",
  representation: "default",
  tl: {x: 0, y: 0},  // in-tree coordinates of the top-left of the view
  zoom: 1,
  update_on_drag: true,
  drag: {x0: 0, y0: 0, element: undefined},  // used when dragging
  select_text: false,
  line_color: "#000",
  rect_color: "#0A0",
  names_color: "#00A",
  lengths_color: "#888",
  font_family: "sans-serif",
  font_size_auto: true,
  font_size_scroller: undefined,
  font_size: 10,
  minimap_show: true,
  minimap_zoom: 1,
  datgui: undefined
};


// Run when the page is loaded (the "main" function).
document.addEventListener("DOMContentLoaded", () => {
  set_query_string_values();
  view.datgui = create_datgui();
  draw_minimap();
  update();
});


// Set values that have been given with the query string.
function set_query_string_values() {
  const params = get_query_params();
  if ("id" in params)
    view.tree_id = params.id;
  if ("name" in params)
    view.tree_name = params.name;
  if ("x" in params)
    view.tl.x = Number(params.x);
  if ("y" in params)
    view.tl.y = Number(params.y);
  if ("z" in params)
    view.zoom = Number(params.z);
}


// Return the value corresponding to a key given in a GET query string.
function get_query_params() {
  const params = {};
  window.location.search.substr(1).split("&").forEach(key_value => {
    const [key, value] = key_value.split("=", 2);
    params[key] = value;
  });
  return params;
}


// Update when the window is resized too.
window.addEventListener("resize", update);  // we could also draw_minimap()


// Create the top-right box ("gui") with all the options we can see and change.
function create_datgui() {
  // Shortcut for getting the styles.
  const [style_line, style_rect, style_font, style_names, style_lengths] =
    [1, 2, 3, 4, 5].map(i => document.styleSheets[0].cssRules[i].style);

  const dgui = new dat.GUI({autoPlace: false});
  div_datgui.appendChild(dgui.domElement);

  dgui.add(view.pos, "x").listen();
  dgui.add(view.pos, "y").listen();

  const dgui_tree = dgui.addFolder("tree");

  add_trees(dgui_tree).then(() => {
    dgui_tree.add(view, "show_tree_info").name("info");
    dgui_tree.add(view, "upload_tree").name("upload");
    add_representations(dgui_tree);  // so they will be added in order
  });

  const dgui_ctl = dgui.addFolder("control");

  dgui_ctl.add(view.tl, "x").name("top-left x").onChange(update);
  dgui_ctl.add(view.tl, "y").name("top-left y").onChange(update);
  dgui_ctl.add(view, "zoom").onChange(update);
  dgui_ctl.add(view, "update_on_drag").name("continuous dragging");
  dgui_ctl.add(view, "select_text").name("select text").onChange(() =>
    style_font.userSelect = (view.select_text ? "text" : "none"));

  const dgui_style = dgui.addFolder("style");

  dgui_style.addColor(view, "line_color").name("line color").onChange(() =>
    style_line.stroke = view.line_color);
  dgui_style.addColor(view, "rect_color").name("rectangle color").onChange(() =>
    style_rect.stroke = view.rect_color);
  dgui_style.addColor(view, "names_color").name("names color").onChange(() =>
    style_names.fill = view.names_color);
  dgui_style.addColor(view, "lengths_color").name("lengths color").onChange(() =>
    style_lengths.fill = view.lengths_color);
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
    return dgui_style.add(view, "font_size", 0.1, 50).name("font size")
      .onChange(() => style_font.fontSize = `${view.font_size}px`);
  }

  const dgui_minimap = dgui.addFolder("minimap");

  dgui_minimap.add(view, "minimap_show").name("active").onChange(() => {
      const status = (view.minimap_show ? "visible" : "hidden");
      div_minimap.style.visibility = div_visible_rect.style.visibility = status;
      if (view.minimap_show)
        update_minimap_visible_rect();
    });

  return dgui;
}


async function add_trees(dgui_tree) {
  const response = await fetch(`http://${location.host}/trees`);
  const data = await response.json();
  const trees = {};
  data.map(t => trees[t.name] = t.id);
  dgui_tree.add(view, "tree_name", Object.keys(trees)).name("name")
    .onChange(() => {
      view.tree_id = trees[view.tree_name];
      view.tl.x = 0;
      view.tl.y = 0;
      view.zoom = 1;
      draw_minimap();
      update();
    });
}


async function add_representations(dgui_tree) {
  const response = await fetch(`http://${location.host}/trees/representations`);
  const data = await response.json();
  dgui_tree.add(view, "representation", data).onChange(update);
}


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
  return (zr > 1 && view.zoom < 1e6) || (zr < 1 && view.zoom > 1e-6);
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


// Move the current tree view to the given mouse position in the minimap.
function move_minimap_view(event) {
  // Top-left pixel coordinates of the tree (0, 0) position in the minimap.
  const [x0, y0] = [div_minimap.offsetLeft + 6, div_minimap.offsetTop + 6];

  // Size of the visible rectangle.
  const [w, h] = [div_visible_rect.offsetWidth, div_visible_rect.offsetHeight];

  view.tl.x = (event.pageX - w/2 - x0) / view.minimap_zoom;
  view.tl.y = (event.pageY - h/2 - y0) / view.minimap_zoom ;
  // So the center of the visible rectangle will be where the mouse is.

  update();
}


// Update the coordinates of the pointer, as shown in the top-right gui.
function update_pointer_pos(event) {
  view.pos.x = view.tl.x + event.pageX / view.zoom;
  view.pos.y = view.tl.y + event.pageY / view.zoom;
}


// Update the view of all elements (gui, tree, minimap).
function update() {
  view.datgui.updateDisplay();  // update the info box on the top-right

  update_tree();

  if (view.minimap_show)
    update_minimap_visible_rect();
}


// Ask the server for a tree in the new defined region, and draw it.
function update_tree() {
  const z = view.zoom;
  const [x, y] = [view.tl.x, view.tl.y];
  const [w, h] = [div_tree.offsetWidth / z, div_tree.offsetHeight / z];

  const url = `http://${location.host}/trees/${view.tree_id}/draw`;

  fetch(`${url}?z=${z}&x=${x}&y=${y}&w=${w}&h=${h}`)
    .then(response => response.json())
    .then(data => draw(div_tree, data, view.tl, view.zoom))
    .catch(error => console.log(error));
}


// Append a svg to the given element, with all the items in the list drawn.
function draw(element, items, tl, zoom) {
  const [w, h] = [element.offsetWidth, element.offsetHeight];

  element.innerHTML = `
    <svg width="${w}" height="${h}"
         viewBox="${tl.x} ${tl.y} ${w / zoom} ${h / zoom}">
      ${items.map(item => item2svg(item, zoom)).join("\n")}
    </svg>`;
}


// Return the graphical (svg) element corresponding to an ete item.
function item2svg(item, zoom) {
  // items look like ['r', ...] for a rectangle, etc.
  if (item[0] === 'r') {       // rectangle
    const [ , x, y, w, h] = item;

    return `<rect class="rect" x="${x}" y="${y}" width="${w}" height="${h}"
                  fill="none"
                  stroke="${view.rect_color}"
                  stroke-width="${1 / zoom}"/>`;
  }
  else if (item[0] === 'l') {  // line
    const [ , x1, y1, x2, y2] = item;

    return `<line class="line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                  stroke="${view.line_color}"
                  stroke-width="${1 / zoom}"/>`;
  }
  else if (item[0].startsWith('t')) {  // text
    const [text_type, x, y, fs, txt] = item;

    return `<text class="text ${get_class(text_type)}" x="${x}" y="${y+fs}"
                  font-size="${fs}px">${txt}</text>`;
    // NOTE: If we wanted to use the exact width of the item, we could add:
    //   textLength="${w}px"
  }
  else {
    console.log(`Got unknown item of type: ${item[0]}`);
    return "";
  }
}


function get_class(text_type) {
  if (text_type === "tn")
    return "names";
  else if (text_type === "tl")
    return "lengths";
  else
    return "";
}


// Draw the full tree on a small div on the bottom-right ("minimap").
function draw_minimap() {
  fetch(`http://${location.host}/trees/${view.tree_id}/size`)
    .then(response => response.json())
    .then(size => draw_minimap_with_size(size))
    .catch(error => console.log(error));
}


function draw_minimap_with_size(size) {
  const [tw, th] = [size.width, size.height];  // tree width and height
  const [w_min, h_min] = [20, 20];  // minimum size of the minimap
  const w_max = 0.2 * window.innerWidth,
        h_max = 0.8 * window.innerHeight;  // maximum size of the minimap
  const zoom = Math.min(1, w_max / tw, h_max / th);  // zoom that accomodates

  // Adjust minimap's size.
  div_minimap.style.width = `${Math.ceil(Math.max(w_min, zoom * tw))}px`;
  div_minimap.style.height = `${Math.ceil(Math.max(h_min, zoom * th))}px`;

  view.minimap_zoom = zoom;

  fetch(`http://${location.host}/trees/${view.tree_id}/draw?z=${zoom}`)
    .then(response => response.json())
    .then(data => draw(div_minimap, data, {x: 0, y: 0}, view.minimap_zoom))
    .then(() => update_minimap_visible_rect())
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
  const ww = round(mz / wz * div_tree.offsetWidth),  // viewport size (scaled)
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

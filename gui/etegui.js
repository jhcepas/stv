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
  text_color: "#00A",
  font_family: "sans-serif",
  font_size: 10,
  minimap_show: true,
  minimap_zoom: 1
};
const dgui = new dat.GUI();
dgui.add(view.pos, "x").listen();
dgui.add(view.pos, "y").listen();
const dgui_ctl = dgui.addFolder("control");
dgui_ctl.add(view.tl, "x").name("top-left x").onChange(update);
dgui_ctl.add(view.tl, "y").name("top-left y").onChange(update);
dgui_ctl.add(view, "zoom", 1, 100).onChange(update);
dgui_ctl.add(view, "update_on_drag").name("continuous dragging");
dgui_ctl.add(view, "select_text").name("select text").onChange(() =>
  css[3].style.userSelect = (view.select_text ? "text" : "none"));
const dgui_style = dgui.addFolder("style");
const css = document.styleSheets[0].cssRules;  // shortcut
dgui_style.addColor(view, "line_color").name("line color").onChange(() =>
  css[1].style.stroke = view.line_color);
dgui_style.addColor(view, "rect_color").name("rectangle color").onChange(() =>
  css[2].style.stroke = view.rect_color);
dgui_style.addColor(view, "text_color").name("text color").onChange(() =>
  css[3].style.fill = view.text_color);
dgui_style.add(view, "font_family",
  ["sans-serif", "serif", "cursive", "monospace"]).name("font").onChange(() =>
  css[3].style.fontFamily = view.font_family);
dgui_style.add(view, "font_size", 1, 20).onChange(() =>
  css[3].style.fontSize = `${view.font_size}px`);
const dgui_minimap = dgui.addFolder("minimap");
dgui_minimap.add(view, "minimap_show").name("active").onChange(() => {
    const display = (view.minimap_show ? "block" : "none");
    div_minimap.style.display = div_visible_rect.style.display = display;
    if (view.minimap_show)
      update_minimap_visible_rect();
  });


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const zr = (event.deltaY < 0 ? 1.25 : 0.8);  // zoom change (ratio)
  if (is_valid_zoom_change(zr)) {
    const zoom_new = view.zoom * zr,
          tppix = 1 / view.zoom - 1 / zoom_new;  // tree coordinates per pixel
    view.tl.x += tppix * event.pageX;
    view.tl.y += tppix * event.pageY;
    view.zoom = zoom_new;
    update();
  }
}, {passive: false});  // chrome now uses passive=true otherwise

function is_valid_zoom_change(zr) {
  return (zr > 1 && view.zoom < 100) || (zr < 1 && view.zoom > 1);
}


// Drag the tree around (by changing the top-left corner of the view).
document.addEventListener("mousedown", event => {
  if (view.select_text)
    return;  // if by clicking we can select text, do not start a drag too

  if (div_visible_rect.contains(event.target))
    view.drag.element = div_visible_rect;
  else if (div_tree.contains(event.target))
    view.drag.element = div_tree;

  drag_start(event);
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
        w = window.innerWidth - Math.max(0, - view.zoom * view.tl.x),
        h = window.innerHeight - Math.max(0, - view.zoom * view.tl.y);

  fetch(`/get_scene_region/${view.zoom},${x},${y},${w},${h}/`)
    .then(response => response.json())
    .then(resp_data => div_tree.innerHTML = draw(resp_data.items))
    .catch(error => console.log(error));
}


// Return an svg with all the items in the list (rectangles and lines).
function draw(items, x0_, y0_, width_, height_) {
  const width = width_ || (window.innerWidth - 10),
        height = height_ || (window.innerHeight - 10),
        x0 = x0_ || (view.zoom * view.tl.x),
        y0 = y0_ || (view.zoom * view.tl.y);

  let svg = `<svg width="${width}" height="${height}">`;
  items.forEach(d => {
    if (d[0] === 'r') {       // rectangle
      const x = d[1] - x0, y = d[2] - y0, w = d[3], h = d[4];
      svg += `<rect class="rect" x="${x}" y="${y}" width="${w}" height="${h}"
                    fill="none" stroke="${view.rect_color}"/>`;
    }
    else if (d[0] === 'l') {  // line
      const x1 = d[1] - x0, y1 = d[2] - y0,
            x2 = d[3] - x0, y2 = d[4] - y0;
      svg += `<line class="line" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                    stroke="${view.line_color}"/>`;
    }
    else if (d[0] === 't') {  // text
      const x = d[1] - x0, y = d[2] - y0, w = d[3], h = d[4];
      svg += `<text class="text" x="${x}" y="${y}"
                    color="${view.text_color}">${d[5]}</text>`;
      // TODO: check if we want to use something like:
      //    textLength="${w}"
      // TODO: compute the length of the text and adjust so it fits in the rect
    }
    else {
      console.log(`Got unknown item: ${d[0]}`);
    }
  });
  svg += '</svg>';

  return svg;
}


// Create a drawing on the bottom-right of the full tree at zoom 1 ("minimap").
function create_minimap() {
  fetch('/limits/')
    .then(response => response.json())
    .then(limits => {
      const tw = limits.width, th = limits.height;  // tree width and height
      const w_min = 20, h_min = 20,  // minimum and maximum size of the minimap
            w_max = 0.2 * window.innerWidth, h_max = 0.8 * window.innerHeight;
      const z = Math.min(1, w_max / tw, h_max / th);  // zoom that accomodates

      div_minimap.style.width = `${Math.ceil(Math.max(w_min, z * tw))}px`;
      div_minimap.style.height = `${Math.ceil(Math.max(h_min, z * th))}px`;
      view.minimap_zoom = z;

      update_minimap_visible_rect();

      fetch(`/get_scene_region/${z},0,0,${z * tw},${z * th}/`)
        .then(response => response.json())
        .then(resp_data => {
          div_minimap.innerHTML = draw(resp_data.items);
          const cs = div_minimap.childNodes[0].style;
          cs.width = div_minimap.style.width;
          cs.height = div_minimap.style.height;
        })
        .catch(error => console.log(error));
    })
    .catch(error => console.log(error));
}

// Update the minimap's rectangle that represents the current view of the tree.
function update_minimap_visible_rect() {
  const w_min = 5, h_min = 5;  // minimum size of the rectangle
  const round = Math.round, min = Math.min, max = Math.max;  // shortcuts

  const wz = view.zoom, mz = view.minimap_zoom;

  // Transform all measures into "minimap units" (scaling accordingly).
  const mbw = 3, rbw = 1;  // border-width from .minimap and .visible_rect css
  const mw = div_minimap.offsetWidth - 2 * (mbw + rbw),    // minimap size
        mh = div_minimap.offsetHeight - 2 * (mbw + rbw);
  const ww = round(mz / wz * window.innerWidth),  // window size (scaled)
        wh = round(mz / wz * window.innerHeight);
  const tx = round(mz * view.tl.x),  // top-left corner of visible area
        ty = round(mz * view.tl.y);  //   in tree coordinates (scaled)

  const x = max(0, min(tx, mw)),
        y = max(0, min(ty, mh)),
        w = max(w_min, ww) + min(tx, 0),
        h = max(h_min, wh) + min(ty, 0);

  const rs = div_visible_rect.style;
  rs.left = `${div_minimap.offsetLeft + mbw + x}px`;
  rs.top = `${div_minimap.offsetTop + mbw + y}px`;
  rs.width = `${max(1, min(w, mw - x))}px`;
  rs.height = `${max(1, min(h, mh - y))}px`;
}

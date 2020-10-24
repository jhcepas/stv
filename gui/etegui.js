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
  drag: {x0: 0, y0: 0, active: false},  // used when dragging the image
  line_color: "#000",
  rect_color: "#00F",
  font_family: "sans-serif",
  minimap_show: true
};
const dgui = new dat.GUI();
dgui.add(view.pos, "x").listen();
dgui.add(view.pos, "y").listen();
const dgui_ctl = dgui.addFolder("control");
dgui_ctl.add(view.tl, "x").name("top-left x").onChange(update);
dgui_ctl.add(view.tl, "y").name("top-left y").onChange(update);
dgui_ctl.add(view, "zoom", 1, 100).onChange(update);
dgui_ctl.add(view, "update_on_drag").name("continuous dragging");
const dgui_style = dgui.addFolder("style");
dgui_style.addColor(view, "line_color").name("line color").onChange(update);
dgui_style.addColor(view, "rect_color").name("rectangle color").onChange(update);
dgui_style.add(view, "font_family",
  ["sans-serif", "serif", "cursive", "monospace"]).name("font").onChange(() =>
    div_tree.style.fontFamily = view.font_family);
const dgui_minimap = dgui.addFolder("minimap");
dgui_minimap.add(view, "minimap_show").name("active").onChange(() => {
    const display = view.minimap_show ? "block" : "none";
    div_minimap.style.display = div_visible_rect.style.display = display;
    if (view.minimap_show)
      update_minimap_visible_rect();
  });


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const zr = (event.deltaY > 0 ? 1.25 : 0.8);  // zoom change (ratio)
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
  if (div_tree.contains(event.target))
    drag_start(event);
});

document.addEventListener("mouseup", event => {
  if (view.drag.active)
    drag_stop(event);
});

document.addEventListener("mousemove", event => {
  if (view.drag.active && view.update_on_drag) {
    drag_stop(event);
    drag_start(event);
  }

  update_pos(event);
});

function drag_start(event) {
  view.drag.x0 = event.pageX;
  view.drag.y0 = event.pageY;
  view.drag.active = true;
}

function drag_stop(event) {
  const dx = event.pageX - view.drag.x0,  // mouse position increment
        dy = event.pageY - view.drag.y0;
  if (dx != 0 || dy != 0) {
    view.tl.x -= dx / view.zoom;
    view.tl.y -= dy / view.zoom;
    update();
  }
  view.drag.active = false;
}

function update_pos(event) {
  view.pos.x = view.tl.x + event.pageX / view.zoom;
  view.pos.y = view.tl.y + event.pageY / view.zoom;
}


// Ask the server for a tree in the new defined region, and draw it.
function update() {
  dgui.updateDisplay();  // updates the info box on the top-right gui

  update_tree();

  if (view.minimap_show)
    update_minimap_visible_rect();
}

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
    switch (d[0]) {
      case 'r':
        const x = d[1] - x0, y = d[2] - y0, w = d[3], h = d[4];
        svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}"
                      fill="none" stroke="${view.rect_color}"/>`;
        break;
      case 'l':
        const x1 = d[1] - x0, y1 = d[2] - y0,
              x2 = d[3] - x0, y2 = d[4] - y0;
        svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                      stroke="${view.line_color}"/>`;
        break;
      default:
        console.log(`Got unknown item: ${d}`);
    }
  });
  svg += '</svg>';

  return svg;
}


function create_minimap() {
  fetch('/limits/')
    .then(response => response.json())
    .then(limits => {
      div_minimap.style.width = `${limits.width}px`;
      div_minimap.style.height = `${limits.height}px`;

      update_minimap_visible_rect();

      fetch(`/get_scene_region/1,0,0,${limits.width},${limits.height}/`)
        .then(response => response.json())
        .then(resp_data => {
          div_minimap.innerHTML = draw(resp_data.items);
          const svg = div_minimap.childNodes[0];
          svg.style.width = `${limits.width}px`;
          svg.style.height = `${limits.height}px`;
        })
        .catch(error => console.log(error));
    })
    .catch(error => console.log(error));
}

function update_minimap_visible_rect() {
  const ww = window.innerWidth / view.zoom, wh = window.innerHeight / view.zoom,
        mw = div_minimap.offsetWidth, mh = div_minimap.offsetHeight;
  const x = Math.ceil(Math.max(0, Math.min(view.tl.x, mw))),
        y = Math.ceil(Math.max(0, Math.min(view.tl.y, mh))),
        w = Math.ceil(Math.max(1, Math.min(ww + view.tl.x, ww, mw - x))),
        h = Math.ceil(Math.max(1, Math.min(wh + view.tl.y, wh, mh - y)));
  const r = document.getElementById("div_visible_rect").style;
  r.left = `${div_minimap.offsetLeft + x}px`;
  r.top = `${div_minimap.offsetTop + y}px`;
  r.width = `${w}px`;
  r.height = `${h}px`;
}

'use strict';

document.addEventListener("DOMContentLoaded", () => {
  const div_tree = document.getElementById('div_tree');
  update();
});


// Variables shown on the top-right gui (using dat.gui).
const scene = {
  x: 0,
  y: 0,
  zoom: 10,
  update_on_drag: true,
  drag: {x0: 0, y0: 0, active: false}  // used when dragging the image
};
const data_gui = new dat.GUI();
data_gui.add(scene, "x").onChange(update);
data_gui.add(scene, "y").onChange(update);
data_gui.add(scene, "zoom", 1, 100).onChange(update);
data_gui.add(scene, "update_on_drag").name("continuous dragging");


// Use the mouse wheel to zoom in/out (instead of scrolling).
document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const dz = (event.deltaY > 0 ? 1 : -1);  // zoom change
  if (valid_zoom_change(dz)) {
    const zoom_old = scene.zoom, zoom_new = zoom_old + dz;
    scene.zoom = zoom_new;

    // Trying to replicate how Jaime changes x,y -- but not really working yet!
    // scene.x = event.clientX - (zoom_new / zoom_old) * (event.clientX - scene.x);
    // scene.y = event.clientY - (zoom_new / zoom_old) * (event.clientY - scene.y);
    // scene.x += (1 / zoom_old - 1 / zoom_new) * event.clientX;
    // scene.y += (1 / zoom_old - 1 / zoom_new) * event.clientY;
    const a = zoom_new / zoom_old - 1;
    scene.x -= (event.clientX - scene.x) * a;
    scene.y -= (event.clientY - scene.y) * a;

    update();
  }
}, {passive: false});  // chrome now uses passive=true otherwise

function valid_zoom_change(dz) {
  return (scene.zoom < 100 && dz > 0) || (scene.zoom > 1 && dz < 0);
}


// Move the tree.
document.addEventListener("mousedown", event => {
  scene.drag.x0 = event.clientX;
  scene.drag.y0 = event.clientY;
  scene.drag.active = true;
});
document.addEventListener("mouseup", event => {
  const dx = event.clientX - scene.drag.x0,
        dy = event.clientY - scene.drag.y0;
  if (dx != 0 || dy != 0) {
    scene.x -= dx;
    scene.y -= dy;
    update();
  }
  scene.drag.active = false;
});
document.addEventListener("mousemove", event => {
  if (scene.drag.active && scene.update_on_drag) {
    const dx = event.clientX - scene.drag.x0,
          dy = event.clientY - scene.drag.y0;
    scene.x -= dx;
    scene.y -= dy;
    scene.drag.x0 = event.clientX;
    scene.drag.y0 = event.clientY;
    update();
  }
});


// Ask the server for a tree in the new defined region, and draw it.
function update() {
  data_gui.updateDisplay();  // updates the info box on the top-right gui

  // Trying to replicate the bounds that Jaime requests, but not working yet!
  const x = Math.max(0, -scene.x), y = Math.max(0, -scene.y),
        w = Math.min(window.innerWidth, window.innerWidth - scene.x),
        h = Math.min(window.innerHeight, window.innerHeight - scene.y);

  fetch(`/get_scene_region/${scene.zoom},${x},${y},${w},${h}/`)
    .then(response => response.json())
    .then(resp_data => draw(resp_data.items))
    .catch(error => console.log(error));
}


// Draw all the items in the list (rectangles and lines) by creating a svg.
function draw(items) {
  const w = window.innerWidth - 10, h = window.innerHeight - 10;
  let svg = `<svg width="${w}" height="${h}">`;
  items.forEach(d => {
    switch (d[0]) {
      case 'r':
        const x = d[1] - scene.x, y = d[2] - scene.y, w = d[3], h = d[4];
        svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}"
                      fill="none" stroke="blue"/>`;
        break;
      case 'l':
        const x1 = d[1] - scene.x, y1 = d[2] - scene.y,
              x2 = d[3] - scene.x, y2 = d[4] - scene.y;
        svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                      stroke="red"/>`;
        break;
    }
  });
  svg += '</svg>';
  div_tree.innerHTML = svg;
}

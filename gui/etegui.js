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
  const zr = (event.deltaY > 0 ? 1.25 : 0.8);  // zoom change (ratio)
  if (valid_zoom_change(zr)) {
    scene.x -= (zr - 1) * (event.clientX - scene.x);
    scene.y -= (zr - 1) * (event.clientY - scene.y);
    scene.zoom *= zr;
    update();
  }
}, {passive: false});  // chrome now uses passive=true otherwise

function valid_zoom_change(zr) {
  return (scene.zoom < 100 && zr > 1) || (scene.zoom > 1 && zr < 1);
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
    scene.x += dx;
    scene.y += dy;
    update();
  }
  scene.drag.active = false;
});
document.addEventListener("mousemove", event => {
  if (scene.drag.active && scene.update_on_drag) {
    const dx = event.clientX - scene.drag.x0,
          dy = event.clientY - scene.drag.y0;
    scene.x += dx;
    scene.y += dy;
    scene.drag.x0 = event.clientX;
    scene.drag.y0 = event.clientY;
    update();
  }
});


// Ask the server for a tree in the new defined region, and draw it.
function update() {
  data_gui.updateDisplay();  // updates the info box on the top-right gui

  const x = Math.max(0, -scene.x), y = Math.max(0, -scene.y),
        w = window.innerWidth - Math.max(0, scene.x),
        h = window.innerHeight - Math.max(0, scene.y);

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
        const x = d[1] + scene.x, y = d[2] + scene.y, w = d[3], h = d[4];
        svg += `<rect x="${x}" y="${y}" width="${w}" height="${h}"
                      fill="none" stroke="blue"/>`;
        break;
      case 'l':
        const x1 = d[1] + scene.x, y1 = d[2] + scene.y,
              x2 = d[3] + scene.x, y2 = d[4] + scene.y;
        svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                      stroke="black"/>`;
        break;
    }
  });
  svg += '</svg>';
  div_tree.innerHTML = svg;
}

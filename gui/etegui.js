'use strict';



const data = {
  zoom: 1
};

const gui = new dat.GUI();
gui.add(data, "zoom", 1, 100).onChange(() => draw_scene());


document.body.addEventListener("wheel", event => {
  event.preventDefault();
  const dz = (event.deltaY > 0 ? 1 : -1);
  draw_scene();
}, {passive: false});



function draw_scene() {
  const query =
    "" + data.zoom + "," + 0 + "," + 0 + "," + 1000 + "," + 9000;

  console.log(query);
  fetch("/get_scene_region/" + query + "/")
    .then(response => response.json())
    .then(data => {

      const div_svg = document.getElementById('div_svg');
      let svg = '<svg width="6cm" height="5cm" viewBox="0 0 600 1500">';
      data.items.forEach(item => {
        switch (item[0]) {
          case 'r':
            svg += `<rect x="${item[1]}" y="${item[2]}"
                    width="${item[3]}" height="${item[4]}"
                    fill="none" stroke="blue"/>`;
            break;
          case 'l':
            svg += `<line x1="${item[1]}" y1="${item[2]}"
                    x2="${item[3]}" y2="${item[4]}" stroke="red"/>`;
          break;
        }
      });
      svg += '</svg>';
      div_svg.innerHTML = svg;
    })
    .catch(function (error) {
      console.log(error);
    })
    .then(function () {
      // always executed
    });
}


draw_scene();
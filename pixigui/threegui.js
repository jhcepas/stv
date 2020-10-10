var renderer = new THREE.WebGLRenderer();

width = 1800;
height = 900;
renderer.setSize(width, height);
document.body.appendChild(renderer.domElement);

//var camera = new THREE.PerspectiveCamera(360, height / width, 1, 500);

var camera = new THREE.OrthographicCamera(
  width / -2,
  width / 2,
  height / 2,
  height / -2,
  1,
  1000
);

camera.position.set(0, 0, 100);
camera.lookAt(0, 0, 0);
fps = 0;

var controls = new OrbitControls(camera, renderer.domElement);
controls.update();

var scene = new THREE.Scene();

var blue_material = new THREE.LineBasicMaterial({ color: 0x0000ff });
var red_material = new THREE.LineBasicMaterial({ color: 0xff0000 });
// while (scene.children.length > 0) {
//   scene.remove(scene.children[0]);
// }

function square(w, h) {
  var squareShape = new THREE.Shape()
    .moveTo(0, 0)
    .lineTo(w, 0)
    .lineTo(w, h)
    .lineTo(0, h)
    .lineTo(0, 0);
  var geometry = new THREE.ShapeBufferGeometry(squareShape);
  //geometry.elementsNeedUpdate = false;
  //var mesh = new THREE.Mesh(geometry, material);
  return mesh;
}

function drawsquare(x, y, w, h) {
  var points = [];
  points.push(new THREE.Vector3(x, y, 0));
  points.push(new THREE.Vector3(x + w, y, 0));
  points.push(new THREE.Vector3(x + w, y + h, 0));
  points.push(new THREE.Vector3(x, y + h, 0));
  points.push(new THREE.Vector3(x, y, 0));

  var geometry = new THREE.BufferGeometry().setFromPoints(points);
  var line = new THREE.Line(geometry, red_material);
  return line;
}

function get_line(x1, y1, x2, y2) {
  var points = [];
  points.push(new THREE.Vector3(x1, y1, 0));
  points.push(new THREE.Vector3(x2, y2, 0));

  var geometry = new THREE.BufferGeometry().setFromPoints(points);
  var line = new THREE.Line(geometry, blue_material);
  return line;
}

function draw_scene_threejs() {
  var rects = 0;
  var lines = 0;
  // Make a request for a user with a given ID
  axios
    .get("/get_scene_region")
    .then(function (response) {
      items = response["data"]["items"];
      console.log("loaded");
      group = new THREE.Group();
      group.position.y = 0;
      for (var off = 0; off < 10; off += 10) {
        for (var i = 0; i < items.length; i++) {
          item = items[i];
          //console.log(item);
          if (item["0"] == "r") {
            rect = drawsquare(item[1] + off, item[2], item[3], item[4]);
            // mesh = square(item[3], item[4]);
            // //mesh.position.set(item[1], item[2], 1);
            // mesh.x = item[1];
            // mesh.y = item[2];
            group.add(rect);
            rects += 1;
          } else if (item["0"] == "l") {
            line = get_line(item[1] + off, item[2], item[3], item[4]);
            group.add(line);
            lines += 1;
          }
        }
      }
      console.log("items", rects, lines);
      scene.add(group);
      renderer.render(scene, camera);
    })
    .catch(function (error) {
      // handle error
      console.log(error);
    })
    .then(function () {
      // always executed
    });
}
draw_scene_threejs();
renderer.render(scene, camera);

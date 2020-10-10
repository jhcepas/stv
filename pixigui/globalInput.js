function bindGlobalInput(graphics) {
  console.log(graphics.domContainer);
  addWheelListener(graphics.domContainer, function (e) {
    zoom(e.clientX, e.clientY, e.deltaY < 0);
  });

  addDragNDrop();

  function zoom(x, y, isZoomIn) {
    direction = isZoomIn ? 1 : -1;
    var factor = 1 + direction * 0.1;
    console.log("Zoom", factor);
  }

  function addDragNDrop() {
    var stage = graphics.stage;
    stage.setInteractive(true);

    var isDragging = false,
      prevX,
      prevY;

    stage.mousedown = function (moveData) {
      var pos = moveData.global;
      prevX = pos.x;
      prevY = pos.y;
      isDragging = true;
    };

    stage.mousemove = function (moveData) {
      if (!isDragging) {
        return;
      }
      var pos = moveData.global;
      var dx = pos.x - prevX;
      var dy = pos.y - prevY;

      graphics.x += dx;
      graphics += dy;
      prevX = pos.x;
      prevY = pos.y;
    };

    stage.mouseup = function (moveDate) {
      isDragging = false;
    };
  }
}

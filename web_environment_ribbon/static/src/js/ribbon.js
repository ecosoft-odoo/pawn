openerp.web_environment_ribbon = function(instance) {
  setTimeout(function() {
    // Hide ribbon
    var ribbon = $(document).find(".test-ribbon");
    ribbon.hide();

    // Show ribbon
    var model = new instance.web.Model("ir.config_parameter");
    var res = model.call("get_param", ["ribbon.name"]).then(
      function (name) {
        if (name && name != "False") {
          ribbon.html(name);
          ribbon.show();
        }
      }
    );

    // Get ribbon color from system parameters
    var res = model.call("get_param", ["ribbon.color"]).then(
      function (strColor) {
        if (strColor && validStrColour(strColor)) {
          ribbon.css("color", strColor);
        }
      }
    );

    // Get ribbon background color from system parameters
    var res = model.call("get_param", ["ribbon.background.color"]).then(
      function (strBackgroundColor) {
        if (strBackgroundColor && validStrColour(strBackgroundColor)) {
          ribbon.css("background-color", strBackgroundColor);
        }
      }
    );
    
    // Code from: http://jsfiddle.net/WK_of_Angmar/xgA5C/
    function validStrColour(strToTest) {
        if (strToTest === "") { return false; }
        if (strToTest === "inherit") { return true; }
        if (strToTest === "transparent") { return true; }
        var image = document.createElement("img");
        image.style.color = "rgb(0, 0, 0)";
        image.style.color = strToTest;
        if (image.style.color !== "rgb(0, 0, 0)") { return true; }
        image.style.color = "rgb(255, 255, 255)";
        image.style.color = strToTest;
        return image.style.color !== "rgb(255, 255, 255)";
    }
  }, 1000)
}

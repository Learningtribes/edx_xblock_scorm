function disableOnbeforeunload() {
    window.onbeforeunload = function () {
          return null;
        };
}

disableOnbeforeunload();

function DisableOnbeforeunload(runtime, element) {
    "use strict";

    function disableOnbeforeunload() {
        window.onbeforeunload = function () {
              return null;
            };
    }

    $(function ($) {
        disableOnbeforeunload();
    });
}

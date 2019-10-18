function disableOnbeforeunload() {
    $('#scorm-object-frame')[0].contentWindow.onbeforeunload = function () {
        return null;
    };
}

disableOnbeforeunload();
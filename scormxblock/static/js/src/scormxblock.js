function ScormXBlock(runtime, element, settings) {
    "use strict";
    var errorCode = 0;

    const commitUrl = runtime.handlerUrl(element, 'scorm_commit');
    const getValueUrl = runtime.handlerUrl(element, 'scorm_get_value');
    const package_version = settings['scorm_pkg_version_value'];
    const package_date = settings['scorm_pkg_modified_value'];
    const ratio_value = settings['ratio_value'];
    let pendingValues = null;

    function scormInit() {
        var $scormFrame = $('#scorm-object-frame')
        var ratios = {
            '4:3': 0.75,
            '16:9': 0.5625,
            '1:1': 1,
        }
        var resetIframeSize = function () {
          $scormFrame.height($scormFrame.width() * ratios[ratio_value]);
        }
        if ($scormFrame.length){
          $(window).resize(function () {
            resetIframeSize();
          })
          resetIframeSize();
        }
    }

    function Initialize(value) {
        return pingServer() ? "true": "false";
    }

    function Terminate(value) {
        Commit(value);
        return 'true';
    }

    function GetValue(name) {
        const data = getPackageData();
        data['name'] = name;
        const resp = $.ajax({
            type: "POST",
            url: getValueUrl,
            data: JSON.stringify(data),
            async: false
        });
        const content = JSON.parse(resp.responseText);
        if(content.error) {
            alert(content.error)
        }
        return content.value;
    }

    function SetValue(name, value) {
        pendingValues[name] = value;
        return 'true';
    }

    function Commit(value) {
        $.ajax({
            type: "POST",
            url: commitUrl,
            data: JSON.stringify(pendingValues),
            async: false,
            success: function (response) {
                if (typeof response['scorm_score_value'] !== "undefined") {
                    $(".lesson_score", element).html(response['scorm_score_value']);
                }
                $(".success_status", element).html(response['scorm_status_value']);
            }
        });
        initPendingValues();
        return 'true';
    }
    function initPendingValues(){
        pendingValues = getPackageData();
    }


    function GetLastError() {
        // console.log(version + ' GetLastError');
        return 0;
    }

    function GetErrorString(errCode) {
        // console.log(version + ' GetErrorString: ' + errCode);
        return '';
    }

    function GetDiagnostic(errCode) {
        // console.log(version + ' GetDiagnostic: ' + errCode);
        return 'true';
    }


    function SCORM_12_API() {
        this.LMSInitialize = Initialize;
        this.LMSFinish = Terminate;
        this.LMSGetValue = GetValue;
        this.LMSSetValue = SetValue;
        this.LMSCommit = Commit;
        this.LMSGetLastError = GetLastError;
        this.LMSGetErrorString = GetErrorString;
        this.LMSGetDiagnostic = GetDiagnostic;
    }

    function SCORM_2004_API() {
        this.Initialize = Initialize;
        this.Terminate = Terminate;
        this.GetValue = GetValue;
        this.SetValue = SetValue;
        this.Commit = Commit;
        this.GetLastError = GetLastError;
        this.GetErrorString = GetErrorString;
        this.GetDiagnostic = GetDiagnostic;
    }

    function getPackageData() {
        return {
            'package_date': package_date,
            'package_version': package_version
        }
    }


    function pingServer() {
        const resp = $.ajax({
            type: "GET",
            url: runtime.handlerUrl(element, 'ping'),
            async: false
        });
        return resp.status === 200;

    }

    $(function ($) {
        scormInit();
        initPendingValues();
        window.API = new SCORM_12_API();
        window.API_1484_11 = new SCORM_2004_API();
        setTimeout(function() {
            $('#scorm-object-frame')[0].contentWindow.onbeforeunload = function () {
                return null;
            }
        }, 10000);
    });
}

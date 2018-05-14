function ScormXBlock(runtime, element, settings) {
    const commitUrl = runtime.handlerUrl(element, 'commit');
    const getValueUrl = runtime.handlerUrl(element, 'scorm_get_value');
    const version = settings['version_scorm'];
    var errorCode = 0;

    function Initialize(value) {
        console.log(version + ' Initialize: ' + value);
        return 'true';
    }

    function Terminate(value) {
        console.log(version + ' Terminate: ' + value);
        return 'true';
    }

    function GetValue(name) {
        console.log(version + ' GetValue: ' + name);
        var response = $.ajax({
            type: "POST",
            url: getValueUrl,
            data: JSON.stringify({'name': name}),
            async: false
        });
        response = JSON.parse(response.responseText);
        return response.value;
    }

    var pendingValues = {};
    function SetValue(name, value) {
        console.log(version + ' SetValue: ' + name + ' ' + value);
        pendingValues[name] = value;
        return 'true';
    }

    function Commit(value) {
        console.log(version + ' Commit: ' + value);

        $.ajax({
            type: "POST",
            url: commitUrl,
            data: JSON.stringify(pendingValues),
            async: false,
            success: function (response) {
                if (typeof response.lesson_score != "undefined") {
                    $(".lesson_score", element).html(response.lesson_score);
                }
                $(".completion_status", element).html(response.completion_status);
            }
        });
        return 'true';
    }


    function GetLastError() {
        console.log(version + ' GetLastError');
        return 'true';
    }

    function GetErrorString(errCode) {
        console.log(version + ' GetErrorString: ' + errCode);
        return 'true';
    }

    function GetDiagnostic(errCode) {
        console.log(version + ' GetDiagnostic: ' + errCode);
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


    $(function ($) {
        if (version === 'SCORM_12') {
            window.API = new SCORM_12_API();
        } else {
            window.API_1484_11 = new SCORM_2004_API();
        }
    });
}

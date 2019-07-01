function ScormXBlock(runtime, element, settings) {
    const commitUrl = runtime.handlerUrl(element, 'commit');
    const getValueUrl = runtime.handlerUrl(element, 'scorm_get_value');
    var errorCode = 0;
    const package_version = settings['version_scorm_value'];
    const package_date = settings['scorm_modified_value'];

    function Initialize(value) {
        // console.log(' Initialize: ' + value);
        return 'true';
    }

    function Terminate(value) {
        // console.log(' Terminate: ' + value);
        Commit(value);
        return 'true';
    }

    function GetValue(name) {
        // console.log(' GetValue: ' + name);
        var data = getPackageData();
        data['name'] = name;
        var response = $.ajax({
            type: "POST",
            url: getValueUrl,
            data: JSON.stringify(data),
            async: false
        });
        response = JSON.parse(response.responseText);
        // console.log(response.value)
        return response.value;
    }

    function SetValue(name, value) {
        // console.log(' SetValue: ' + name + ' ' + value);
        // console.log(version + 'current pending values: ' + JSON.stringify(pendingValues));
        window.pendingValues[name] = value;
        // console.log(window.pendingValues)
        return 'true';
    }

    function Commit(value) {
        // console.log(' Commit: ' + value);
        // console.log(window.pendingValues)
        $.ajax({
            type: "POST",
            url: commitUrl,
            data: JSON.stringify(window.pendingValues),
            async: false,
            success: function (response) {
                if (typeof response['lesson_score_value'] !== "undefined") {
                    $(".lesson_score", element).html(response['lesson_score_value']);
                }
                $(".success_status", element).html(gettext(response['success_status_value']));
            }
        });
        initPendingValues();
        return 'true';
    }


    function GetLastError() {
        // console.log(' GetLastError');
        return 0;
    }

    function GetErrorString(errCode) {
        // console.log(' GetErrorString: ' + errCode);
        return '';
    }

    function GetDiagnostic(errCode) {
        // console.log(' GetDiagnostic: ' + errCode);
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

    function initPendingValues() {
        window.pendingValues = getPackageData()
    }

    $(function ($) {
        initPendingValues();
        window.API = new SCORM_12_API();
        window.API_1484_11 = new SCORM_2004_API();

        // setInterval(Commit, 1000 * 60 * 5)

    });
}

function ScormXBlock(runtime, element, settings) {
    "use strict";
    var errorCode = 0;

    const commitUrl = runtime.handlerUrl(element, 'scorm_commit');
    const getValueUrl = runtime.handlerUrl(element, 'scorm_get_value');
    const syncScoreUrl = runtime.handlerUrl(element, 'sync_score_value')
    const package_version = settings['scorm_pkg_version_value'];
    const package_date = settings['scorm_pkg_modified_value'];
    const ratio_value = settings['ratio_value'];
    const open_new_tab = settings['open_new_tab_value'];
    var timerId;
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

        if (open_new_tab) {
            $('.launch-button').click(function() {
                $('.launch-content').toggleClass('hidden');
                $('.button-container').addClass('hidden');
            })
        }

        // Get runtime score value due to unexpected terminal action
        timerId = setInterval(syncScoreValue, 2000);
    }

    function Initialize(value) {
        return pingServer() ? "true": "false";
    }

    function Terminate(value) {
        Commit(value);
        clearInterval(timerId);
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

    function CheckChrome() {
        var isChromium = window.chrome;
        var winNav = window.navigator;
        var vendorName = winNav.vendor;
        var isOpera = typeof window.opr !== "undefined";
        var isIEedge = winNav.userAgent.indexOf("Edge") > -1;
        var isIOSChrome = winNav.userAgent.match("CriOS");
        var chrome_commit = false

        if (isIOSChrome) {
            chrome_commit = true
        } else if(
          isChromium !== null &&
          typeof isChromium !== "undefined" &&
          vendorName === "Google Inc." &&
          isOpera === false &&
          isIEedge === false
        ) {
            chrome_commit = true
        }

        return chrome_commit;
    }

    function CheckSafari() {
        var isSafari = false;
        var winNav = window.navigator;
        if (winNav.userAgent.indexOf('Safari') != -1 && winNav.userAgent.indexOf('Chrome') == -1) {
            isSafari = true
        }

        return isSafari;
    }

    function CheckSafariMobile() {
        var isSafariMobile = false;
        var winNav = window.navigator;
        if (winNav.userAgent.indexOf('Safari') != -1 && winNav.userAgent.indexOf('Chrome') == -1 && winNav.userAgent.indexOf('Mobile') != -1) {
            isSafariMobile = true
        }

        return isSafariMobile;
    }

    function GetCookie(name) {
      if (!document.cookie) {
        return null;
      }
      const xsrfCookies = document.cookie.split(';')
        .map(c => c.trim())
        .filter(c => c.startsWith(name + '='));
      if (xsrfCookies.length === 0) {
        return null;
      }
      return decodeURIComponent(xsrfCookies[0].split('=')[1]);
    }


    function Commit(value) {
        if ((CheckChrome() || CheckSafari()) && !CheckSafariMobile()) {
            const csrftoken = GetCookie('csrftoken');
            fetch(commitUrl, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                  'X-CSRFToken': csrftoken
                },
                body: JSON.stringify(pendingValues),
                credentials: 'same-origin',
                keepalive: true
            })
              .then(response => {
                if (response.ok) {
                  return response.json();
                }
              })
              .then(data => {
                if (typeof data['scorm_score_value'] !== "undefined") {
                  $(".lesson_score", element).html(data['scorm_score_value']);
                }
                $(".success_status", element).html(data['scorm_status_value']);
              });
            initPendingValues();
            return 'true';
        } else {
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

    function syncScoreValue() {
        $.ajax({
            type: "GET",
            url: syncScoreUrl,
            async: true,
            success: function(response) {
                $(".lesson_score", element).html(response['scorm_score_value']);
            }
        });
    }

    $(function ($) {
        scormInit();
        initPendingValues();
        window.API = new SCORM_12_API();
        window.API_1484_11 = new SCORM_2004_API();
        if (!open_new_tab) {
            if (CheckSafariMobile()) {
                $('#scorm-object-frame')[0].contentWindow.onpagehide = function () {
                    Commit('value');
                }
            } else {
                $('#scorm-object-frame')[0].contentWindow.onbeforeunload = function () {
                    Commit('value');
                }
            }               
        }
    });
}

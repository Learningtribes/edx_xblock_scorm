(function () {
  function scrollToBottomWhenToggleNewTab () {
    var $newTabSwitcher = document.querySelector('#xb-field-edit-open_new_tab + span.switcher-wrapper > div');

    if ($newTabSwitcher) $newTabSwitcher.addEventListener('click', function () {scrollToBottom('#settings-tab > div.list-input.settings-list')});

    function scrollToBottom (selector) {
      var $container = document.querySelector(selector);
      if ($container && $container.children.length) {
        var $lastChild = $container.children[$container.children.length - 1];
        requestAnimationFrame(function () {
          if ($lastChild.scrollIntoViewIfNeeded) $lastChild.scrollIntoViewIfNeeded(false);
          else $lastChild.scrollIntoView({behavior: 'smooth', block: 'nearest', inline: 'start'});
        });
      }
    }
  }

  function waitUntilDOM (selector, cb) {
    requestAnimationFrame(function () {
      console.count('wait for', selector);
      if (document.querySelector(selector)) cb();
      else requestAnimationFrame(function () {waitUntilDOM(selector, cb)});
    })
  }

  if (requestIdleCallback) requestIdleCallback(function () {waitUntilDOM('.xblock-initialized', scrollToBottomWhenToggleNewTab)});
  else waitUntilDOM('.xblock-initialized', scrollToBottomWhenToggleNewTab);
})();

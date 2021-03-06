function ScormStudioXBlock(runtime, element) {

  var handlerUrl = runtime.handlerUrl(element, 'studio_submit');

  $(element).find('.save-button').bind('click', function() {
    var form_data = new FormData();
    var file_data = $(element).find('#scorm_file').prop('files')[0];
    var ratio = $(element).find('select[name=ratio]').val();
    var new_window = $(element).find('select[name=new_window]').val();
    var display_name = $(element).find('input[name=display_name]').val();
    var has_score = $(element).find('select[name=has_score]').val();
    var weight = $(element).find('input[name=weight]').val();
    form_data.append('file', file_data);
    form_data.append('ratio', ratio);
    form_data.append('new_window', new_window);
    form_data.append('display_name', display_name);
    form_data.append('has_score', has_score);
    form_data.append('weight', weight);

    runtime.notify('save', {state: 'start'});

    $.ajax({
      url: handlerUrl,
      dataType: 'text',
      cache: false,
      contentType: false,
      processData: false,
      data: form_data,
      type: "POST",
      success: function(response){
        runtime.notify('save', {state: 'end'});
      }
    });

  });

  $(element).find('.cancel-button').bind('click', function() {
    runtime.notify('cancel', {});
  });

}

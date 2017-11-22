function setScrollWidths() {
  $('#top-scroll-fade').appendTo('#table-body');
  $('#bottom-scroll-fade').appendTo('#table-body');

  var destination = $('#table-body').offset();
  $('#top-scroll-fade').offset(destination);

  var height = $('#table-body').height();
  destination.top += height;
  destination.top -= $('#bottom-scroll-fade').height();
  $('#bottom-scroll-fade').offset(destination);

  var helperDiv = $('<div />');
  $('#table-body').append(helperDiv);
  $('#top-scroll-fade').width(helperDiv.width());
  $('#bottom-scroll-fade').width(helperDiv.width());
  $('#table-head').width(helperDiv.width());
  helperDiv.remove();
}

window.onload = setScrollWidths;
window.onresize = setScrollWidths;

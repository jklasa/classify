function setScrollFades() {
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
  helperDiv.remove();
}

setScrollFades();
window.onresize = setScrollFades;

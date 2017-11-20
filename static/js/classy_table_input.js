$('#table-body').on('click', '.clickable-row', function(event) {
  if($(this).hasClass('active')){
    $(this).removeClass('active'); 
  } else {
    $(this).addClass('active').siblings().removeClass('active');
  }
});


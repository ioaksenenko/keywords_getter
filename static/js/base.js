$(function () {
  $('[data-toggle="tooltip"]').tooltip();

  $('.nav-item').each(function (i, e) {
    $(e).removeClass('active');
  });
});


function remove_link() {
  let active = $('.nav-item.active');
  let link = $('.nav-item.active a');
  active.append(link.text());
  link.detach();
}
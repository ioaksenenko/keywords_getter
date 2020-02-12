$(document).ready(function () {
    let submit = $('#submit');
    let cid_list = $('#cid-list');
    let index_form = $('#index-form');

    cid_list.keyup(function () {
        let submit = $('#submit');
        let value = $(this).val();

        if (/^[1-9]+\d*(,\s*[1-9]+\d*)*$/.test(value)) {
            submit.prop('disabled', false);
        } else {
            submit.prop('disabled', true);
        }
    });

    index_form.on('submit' , function() {
        let spinner = $('#spinner');
        let submit = $('#submit');

        submit.prop('disabled', true);
        spinner.removeClass('d-none');
    });

    let value = cid_list.val();
    if (/^[1-9]+\d*(,\s*[1-9]+\d*)*$/.test(value)) {
        submit.prop('disabled', false);
    } else {
        submit.prop('disabled', true);
    }


    $('#courses-keywords').parent().addClass('active');
    remove_link();
});
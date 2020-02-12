$(document).ready(function () {
    $('[type="radio"][name="sdo"]').change(function () {
        $.ajax({
            dataType: "html",
            method: "GET",
            url: "/courses/",
            data: {'sdo': this.value}
        }).done(function (response) {
            $('body').html(response);
        }).fail(function (response) {
            console.log(response);
        });
    });

    let checkboxes = $('input[type="checkbox"][name="courses"]');
    let checked = $('input[type="checkbox"][name="courses"]:checked');
    let check_all = $('#check-all');

    if (check_all.prop('checked')) {
        check_all.prop('indeterminate', checked.length !== checkboxes.length);
    }

    checkboxes.change(function () {
        let checkboxes = $('input[type="checkbox"][name="courses"]');
        let checked = $('input[type="checkbox"][name="courses"]:checked');
        let check_all = $('#check-all');
        let processing = $('#processing');

        if (checked.length !== 0) {
            check_all.prop('checked', true);
            check_all.prop('indeterminate', checked.length !== checkboxes.length);
            processing.prop('disabled', false);
        } else {
            check_all.prop('checked', false);
            check_all.prop('indeterminate', false);
            processing.prop('disabled', true);
        }
    });

    check_all.change(select);

    $('#auto-processing').parent().addClass('active');
    remove_link();
});


function select() {
    let checkboxes = $('input[type="checkbox"][name="courses"]');
    let checked = $('input[type="checkbox"][name="courses"]:checked');
    let check_all = $('#check-all');
    let processing = $('#processing');
    if (checked.length === 0) {
        checkboxes.each(function (i, e) {
            $(e).prop('checked', true);
        });
        check_all.prop('checked', true);
        processing.prop('disabled', false);
    } else {
        checkboxes.each(function (i, e) {
            $(e).prop('checked', false);
        });
        check_all.prop('checked', false);
        processing.prop('disabled', true);
    }
    check_all.prop('indeterminate', false);
}
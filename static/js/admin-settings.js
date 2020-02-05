$(document).ready(function () {
    let checkboxes = $('input[type="checkbox"][name="keywords"]');
    let checked = $('input[type="checkbox"][name="keywords"]:checked');
    let check_all = $('#check-all');

    if (check_all.prop('checked')) {
        check_all.prop('indeterminate', checked.length !== checkboxes.length);
    }

    checkboxes.change(function () {
        let checkboxes = $('input[type="checkbox"][name="keywords"]');
        let checked = $('input[type="checkbox"][name="keywords"]:checked');
        let check_all = $('#check-all');

        if (checked.length !== 0) {
            check_all.prop('checked', true);
            check_all.prop('indeterminate', checked.length !== checkboxes.length);
        } else {
            check_all.prop('checked', false);
            check_all.prop('indeterminate', false);
        }
    });

    check_all.change(select);
});


function select() {
    let checkboxes = $('input[type="checkbox"][name="keywords"]');
    let checked = $('input[type="checkbox"][name="keywords"]:checked');
    let check_all = $('#check-all');
    if (checked.length === 0) {
        checkboxes.each(function (i, e) {
            $(e).prop('checked', true);
        });
        check_all.prop('checked', true);
    } else {
        checkboxes.each(function (i, e) {
            $(e).prop('checked', false);
        });
        check_all.prop('checked', false);
    }
    check_all.prop('indeterminate', false);
}
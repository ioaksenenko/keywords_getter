$(document).ready(function () {
    let time = new Date($.now());

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

    $('#admin-settings').parent().addClass('active');
    remove_link();
    add_collapse();
    /*let edeted = add_collapse();
    while (edeted) {
        edeted = add_collapse();
    }*/

    let collapses = $('[id^="collapse-"]');
    collapses.on('shown.bs.collapse', function () {
        let id = $(this).prop('id').split('-')[1];
        let comma = $('#comma-' + id);
        let link = $('#collapse-link-' + id);
        let content = $('#content-' + id);

        comma.removeClass('d-none');
        link.text('свернуть');
        let content_text = content.text();
        content.text(content_text !== '' ? content_text + ', ' : '');
    });
    collapses.on('hidden.bs.collapse', function () {
        let id = $(this).prop('id').split('-')[1];
        let comma = $('#comma-' + id);
        let link = $('#collapse-link-' + id);
        let content = $('#content-' + id);

        comma.addClass('d-none');
        link.text('развернуть');
        content.text(content.text().substr(0, content.text().length - 2));
    });

    time = new Date($.now()) - time;
    console.log(time);

    let join = $('#join-modal');
    let join_row = join.parent().parent();
    $('tr').click(function () {
        if ($(this).hasClass('table-info')) {
            $(this).removeClass('table-info');
        } else {
            $(this).addClass('table-info');
        }
        let selected_rows = $('.table-info');
        if (selected_rows.length > 1) {
            join_row.removeClass('d-none');
        } else {
            if (!join_row.hasClass('d-none')) {
                join_row.addClass('d-none');
            }
        }
    });
    let nf_select = $('#normal-form');
    let keywords = [];
    join.click(function () {
        $('.table-info').each(function (i, e) {
            let keyword = {};
            keyword['normal-form'] = $(e).find('td:eq(1)').text().trim();
            nf_select.append('<option>' + keyword['normal-form'] + '</option>');
            keyword['original-forms'] = [];
            $(e).find('td:eq(2) div span').each(function (i, e) {
                keyword['original-forms'] = $.merge(keyword['original-forms'], $(e).text().split(', '));
            });
            keywords.push(keyword);
        });
    });
    $('#join').click(function () {
        $.ajax({
            dataType: "html",
            method: "GET",
            url: "/join/",
            data: {
                keywords: JSON.stringify(keywords),
                normal_form: nf_select.val()
            }
        }).done(function (response) {
            location.reload();
        }).fail(function (response) {
            console.log(response);
        });
    });
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


function add_collapse() {
    let containers = $('[id^="container-"]');
    let edeted = false;
    containers.each(function (index, element) {
        let container = $(element);
        let id = container.prop('id').split('-')[1];
        let content = $('#content-' + id);

        let original_height = container.innerHeight();
        let text = content.text();
        content.html('...');
        let one_line_height = container.innerHeight();
        content.html(text);

        /*
        console.log($('#word-' + id).text());
        console.log(original_height);
        console.log(one_line_height);
        */

        if (original_height !== one_line_height) {
            edeted = true;
            let collapse = $('#collapse-' + id);
            let collapse_link = $('#collapse-link-' + id);
            collapse.removeClass('d-none');
            collapse_link.removeClass('d-none');

            let fragments = text.split(', ');
            let collapse_content = [];
            while (original_height !== one_line_height) {
                collapse_content.push(fragments.pop());
                content.html(fragments.join(', '));
                original_height = container.innerHeight();
            }

            let old_collapse_content = collapse.text().split(', ');
            if (old_collapse_content.length > 1) {
                collapse_content = old_collapse_content.concat(collapse_content);
            }
            collapse.html(collapse_content.join(', '));
        }
    });
    return edeted;
}
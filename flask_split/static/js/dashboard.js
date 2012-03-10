$(function () {
    $('[rel=tooltip]').tooltip();

    var modalConfirmDelete = $('#modal-confirm-delete'),
        modalConfirmReset = $('#modal-confirm-reset'),
        modalConfirmWinner = $('#modal-confirm-winner');

    modalConfirmReset.find('.btn-danger').on('click', function () {
        var form = modalConfirmReset.data('form');
        form.submit();
        return false;
    });

    modalConfirmDelete.find('.btn-danger').on('click', function () {
        var form = modalConfirmDelete.data('form');
        form.submit();
        return false;
    });

    modalConfirmWinner.find('.btn-success').click(function () {
        var form = modalConfirmWinner.data('form');
        form.submit();
        return false;
    });

    $('.form-reset-experiment').on('submit', function () {
        modalConfirmReset
            .modal('show')
            .data('form', this);
        return false;
    });

    $('.form-delete-experiment').on('submit', function () {
        modalConfirmDelete
            .modal('show')
            .data('form', this);
        return false;
    });
    $('.form-set-winner').on('submit', function () {
        modalConfirmWinner
            .modal('show')
            .data('form', this);
        return false;
    });
});

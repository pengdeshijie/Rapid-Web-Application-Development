"""Friendly application error pages."""

from flask import render_template

from . import db


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return (
            render_template(
                "errors/error.html",
                code=400,
                heading="That request could not be completed",
                message="Please check the submitted information and try again.",
            ),
            400,
        )

    @app.errorhandler(403)
    def forbidden(error):
        return (
            render_template(
                "errors/error.html",
                code=403,
                heading="This action belongs to another rider",
                message="You do not have permission to access this resource.",
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(error):
        return (
            render_template(
                "errors/error.html",
                code=404,
                heading="This route is off the map",
                message="The page or event could not be found.",
            ),
            404,
        )

    @app.errorhandler(413)
    def file_too_large(error):
        return (
            render_template(
                "errors/error.html",
                code=413,
                heading="That image is too large",
                message="Choose an image smaller than 5 MB and try again.",
            ),
            413,
        )

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return (
            render_template(
                "errors/error.html",
                code=500,
                heading="We hit an unexpected climb",
                message="Nothing was lost. Please return and try again.",
            ),
            500,
        )

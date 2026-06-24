from __future__ import annotations

from lsco_tdcj_intake.review_app.app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
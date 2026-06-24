from __future__ import annotations

from flask import Flask, render_template, request

from lsco_tdcj_intake.review_app.packet_store import (
    filter_packets,
    read_packet_registry,
    registry_summary,
)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        status_filter = request.args.get("status", "active")
        all_packets = read_packet_registry()
        visible_packets = filter_packets(all_packets, status_filter)
        summary = registry_summary(all_packets)

        return render_template(
            "index.html",
            packets=visible_packets,
            summary=summary,
            status_filter=status_filter,
        )

    return app
from __future__ import annotations

from flask import Flask, abort, render_template, request

from lsco_tdcj_intake.review_app.packet_store import (
    filter_packets,
    get_packet,
    read_packet_registry,
    read_packet_review_rows,
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

    @app.route("/packet/<packet_id>")
    def packet_detail(packet_id: str):
        packet = get_packet(packet_id)
        if packet is None:
            abort(404)

        review_rows = read_packet_review_rows(packet_id)

        return render_template(
            "packet.html",
            packet=packet,
            review_rows=review_rows,
        )

    return app
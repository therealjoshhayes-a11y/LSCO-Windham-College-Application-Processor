from __future__ import annotations

from flask import Flask, abort, redirect, render_template, request, send_file, url_for

from lsco_tdcj_intake.review_app.packet_store import (
    REVIEW_PACKETS_ROOT,
    add_evidence_paths,
    approve_packet,
    filter_packets,
    get_packet,
    packet_has_unresolved_reviews,
    read_packet_registry,
    read_packet_review_rows,
    registry_summary,
    save_review_decision,
    export_approved_admissions_batch,
)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        all_packets = read_packet_registry()
        status = request.args.get("status", "active")
        packets = filter_packets(all_packets, status)
        summary = registry_summary(all_packets)

        return render_template(
            "index.html",
            packets=packets,
            summary=summary,
            selected_status=status,
        )
    
    @app.route("/export-approved-admissions", methods=["POST"])
    def export_approved_admissions_route():
        exported = export_approved_admissions_batch()

        if not exported:
            return redirect(url_for("index", export_error="failed"))

        return redirect(url_for("index", export_status="success"))

    @app.route("/packet/<packet_id>")
    def packet_detail(packet_id: str):
        packet = get_packet(packet_id)
        if packet is None:
            abort(404)

        review_rows = add_evidence_paths(
            packet_id,
            read_packet_review_rows(packet_id),
        )

        return render_template(
            "packet.html",
            packet=packet,
            review_rows=review_rows,
        )

    @app.route("/packet/<packet_id>/review", methods=["POST"])
    def save_packet_review(packet_id: str):
        packet = get_packet(packet_id)
        if packet is None:
            abort(404)

        field_id = request.form.get("field_id", "")
        action = request.form.get("action", "")
        review_value = request.form.get("review_value", "")
        review_notes = request.form.get("review_notes", "")

        saved = save_review_decision(
            packet_id=packet_id,
            field_id=field_id,
            action=action,
            review_value=review_value,
            review_notes=review_notes,
        )

        if not saved:
            abort(400)

        return redirect(url_for("packet_detail", packet_id=packet_id))

    @app.route("/packet/<packet_id>/approve", methods=["POST"])
    def approve_packet_route(packet_id: str):
        packet = get_packet(packet_id)
        if packet is None:
            abort(404)

        if packet_has_unresolved_reviews(packet_id):
            return redirect(
                url_for(
                    "packet_detail",
                    packet_id=packet_id,
                    approval_error="unresolved",
                )
            )

        approved = approve_packet(packet_id=packet_id)

        if not approved:
            abort(400)

        return redirect(url_for("packet_detail", packet_id=packet_id))

    @app.route("/packet-file/<packet_id>/<path:relative_path>")
    def packet_file(packet_id: str, relative_path: str):
        packet = get_packet(packet_id)
        if packet is None:
            abort(404)

        packet_dir = (REVIEW_PACKETS_ROOT / packet_id).resolve()
        requested_path = (packet_dir / relative_path).resolve()

        try:
            requested_path.relative_to(packet_dir)
        except ValueError:
            abort(403)

        if not requested_path.exists() or not requested_path.is_file():
            abort(404)

        return send_file(requested_path)

    return app
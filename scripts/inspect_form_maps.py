"""Print a compact inventory of the locked LSCO TDCJ form maps."""

from __future__ import annotations

from collections import Counter

from lsco_tdcj_intake.form_maps.loader import load_all_maps


def main() -> None:
    """Print page-level and field-level map inventory."""
    maps = load_all_maps()

    total_fields = 0
    print("LSCO TDCJ locked form-map inventory")
    print("=" * 40)

    for page_number in sorted(maps):
        form_map = maps[page_number]
        fields = form_map.fields
        field_type_counts = Counter(field.get("type", "UNKNOWN") for field in fields.values())

        total_fields += len(fields)

        print()
        print(f"Page {page_number}")
        print(f"  document_id: {form_map.document_id}")
        print(f"  revision:    {form_map.revision}")
        print(f"  size:        {form_map.width} x {form_map.height} pt")
        print(f"  dpi:         {form_map.dpi}")
        print(f"  fields:      {len(fields)}")
        print(f"  anchors:     {len(form_map.anchors)}")
        print(f"  locked zones:{len(form_map.locked_zones)}")
        print("  field types:")

        for field_type, count in sorted(field_type_counts.items()):
            print(f"    {field_type}: {count}")

        print("  first 10 fields:")
        for field_id in list(fields)[:10]:
            print(f"    - {field_id}")

    print()
    print(f"Total mapped fields: {total_fields}")


if __name__ == "__main__":
    main()
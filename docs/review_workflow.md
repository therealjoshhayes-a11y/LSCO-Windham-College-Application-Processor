# LSCO TDCJ Intake Review Workflow

## Purpose

This workflow turns a scanned TDCJ/Windham application packet into review-ready files, then applies human-reviewed values into a draft admissions export row.

The machine does **not** final-approve identity-critical fields. The reviewer remains responsible for verifying fields such as TDCJ number, SSN, and date of birth.

## Source packet location

Place scanned packet TIFF files here:

```text
data\incoming\scans
```

Example packet:

```text
data\incoming\scans\image-1.tif
```

## Build review packets

From the repo root:

```powershell
python scripts\batch_build_review_packets.py
```

For a single packet:

```powershell
python scripts\build_review_packet.py data\incoming\scans\image-1.tif
```

## Output packet folder

Each packet produces a folder here:

```text
data\processed\review_packets\<packet_id>
```

Example:

```text
data\processed\review_packets\image-1
```

Important files:

```text
human_review_queue.csv
human_review_queue_FOR_REVIEW.csv
reviewed_packet.json
reviewed_packet_values.csv
admissions_export_row.csv
```

## Reviewer file

The reviewer should use this file:

```text
human_review_queue_FOR_REVIEW.csv
```

Do **not** edit the original machine/source artifacts unless intentionally debugging.

The reviewer fills only these columns:

```text
review_value
review_notes
```

The reviewer should verify each row using the scanned packet and any available machine evidence.

## Identity-critical fields

These fields must be reviewed carefully:

```text
p1_tdcj_number
p1_ssn
p1_date_of_birth
```

The reviewer-facing CSV includes machine evidence columns:

```text
machine_value
numeric_fullfield_digits
numeric_shape_valid
notes
```

Important rules:

```text
TDCJ number: exactly 8 digits
SSN: exactly 9 digits
Date of Birth: exactly 8 digits in MMDDYYYY form
```

The system preserves leading zeroes for reviewed DOB, SSN, and TDCJ values.

## Apply reviewed values

After the reviewer fills `review_value` in the reviewer CSV, run:

```powershell
python scripts\apply_review_values.py `
  --packet-id image-1 `
  --human-review-csv data\processed\review_packets\image-1\human_review_queue_FOR_REVIEW.csv `
  --machine-accepted-csv data\processed\review_packets\image-1\page1_machine_accepted.csv `
  --checkbox-summary-csv data\processed\review_packets\image-1\checkbox_review_summary.csv `
  --reviewed-packet-json data\processed\review_packets\image-1\reviewed_packet.json `
  --reviewed-packet-values-csv data\processed\review_packets\image-1\reviewed_packet_values.csv `
  --admissions-export-row-csv data\processed\review_packets\image-1\admissions_export_row.csv
```

## Check review status

Inspect reviewed packet values:

```powershell
Import-Csv data\processed\review_packets\image-1\reviewed_packet_values.csv |
Group-Object source |
Select-Object Name,Count |
Format-Table -AutoSize
```

Possible sources:

```text
machine_accepted
checkbox_accepted
human_review
review_pending
```

A complete review should have no `review_pending` rows.

## Check admissions export row

```powershell
Import-Csv data\processed\review_packets\image-1\admissions_export_row.csv |
Select-Object export_status,packet_id,pending_review_count,'Last Name','First Name','Middle Name','Date of Birth',SSN,'High School - Name','Start Term','Admission Type 1','Student Type' |
Format-List
```

Expected while review is incomplete:

```text
export_status        : review_pending
pending_review_count : greater than 0
```

Expected after all review fields are filled:

```text
export_status        : review_complete
pending_review_count : 0
```

## Do not edit

Do not manually edit these files during normal processing:

```text
page1_ocr.csv
page1_ocr.json
page1_numeric_fullfield_ocr.csv
page1_numeric_fullfield_ocr.json
packet_checkbox_groups.json
checkbox_review_summary.csv
checkbox_review_summary.json
reviewed_packet.json
reviewed_packet_values.csv
admissions_export_row.csv
```

These are generated artifacts. If they need to change, rebuild them through the scripts.

## Normal operator sequence

```powershell
python scripts\batch_build_review_packets.py
```

Reviewer fills:

```text
human_review_queue_FOR_REVIEW.csv
```

Operator applies reviewed values:

```powershell
python scripts\apply_review_values.py `
  --packet-id image-1 `
  --human-review-csv data\processed\review_packets\image-1\human_review_queue_FOR_REVIEW.csv `
  --machine-accepted-csv data\processed\review_packets\image-1\page1_machine_accepted.csv `
  --checkbox-summary-csv data\processed\review_packets\image-1\checkbox_review_summary.csv `
  --reviewed-packet-json data\processed\review_packets\image-1\reviewed_packet.json `
  --reviewed-packet-values-csv data\processed\review_packets\image-1\reviewed_packet_values.csv `
  --admissions-export-row-csv data\processed\review_packets\image-1\admissions_export_row.csv
```

Operator verifies:

```powershell
Import-Csv data\processed\review_packets\image-1\admissions_export_row.csv |
Select-Object export_status,packet_id,pending_review_count,'Last Name','First Name','Date of Birth',SSN,'Start Term','Admission Type 1','Student Type' |
Format-List
```

## Current known good test

A partial reviewer test with these values:

```text
p1_date_of_birth = 01011980
p1_ssn = 123456789
p1_hs_name = TEST HIGH SCHOOL
```

correctly produced:

```text
pending_review_count : 20
Date of Birth        : 01011980
SSN                  : 123456789
High School - Name   : TEST HIGH SCHOOL
Start Term           : Fall
Admission Type 1     : Associate Degree
Student Type         : Transfer
```

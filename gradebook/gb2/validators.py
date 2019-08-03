import os

from django.core.exceptions import ValidationError


def _validate_file_extension(value, *valid_extensions):
    ext = os.path.splitext(value.name)[1]
    if not ext.lower() in valid_extensions:
        raise ValidationError("Unsupported file type.")


def validate_csv_file_extension(value):
    return _validate_file_extension(value, ".csv")


def _validate_content_type(value, *valid_contenttypes):
    if (
        hasattr(value.file, "content_type")
        and value.file.content_type not in valid_contenttypes
    ):
        raise ValidationError("Unsupported file type.")


def validate_spreadsheet(value):
    extensions = [".csv", ".xls", ".xlsx", ".ods"]
    contenttypes = [
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "application/vnd.oasis.opendocument.spreadsheet",
    ]
    _validate_file_extension(value, *extensions)
    _validate_content_type(value, *contenttypes)

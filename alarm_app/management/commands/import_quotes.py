"""
Management command to import quotes from a text file.

Usage:
    python manage.py import_quotes <file_path>
"""

from django.core.management.base import BaseCommand, CommandError
from alarm_app.models import Quote
import os


class Command(BaseCommand):
    help = 'Import quotes from a text file (format: quote text followed by "----" separator)'

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to the quotes text file")
        parser.add_argument(
            "--category",
            type=str,
            default="",
            help="Category to assign to imported quotes",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing quotes before importing",
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]
        category = options["category"]
        clear_existing = options["clear"]

        # Check if file exists
        if not os.path.exists(file_path):
            raise CommandError(f"File '{file_path}' does not exist")

        # Clear existing quotes if requested
        if clear_existing:
            count = Quote.objects.count()
            Quote.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing quotes"))

        # Read and parse the file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise CommandError(f"Error reading file: {e}")

        # Split by separator
        quotes_raw = content.split("----\n")

        imported_count = 0
        skipped_count = 0

        for quote_text in quotes_raw:
            quote_text = quote_text.strip()

            # Skip empty quotes
            if not quote_text:
                continue

            # Try to extract author (last line if it doesn't end with punctuation)
            lines = quote_text.split("\n")
            author = ""

            if len(lines) > 1:
                last_line = lines[-1].strip()
                # If last line looks like an author attribution
                if last_line and not last_line[-1] in ".!?":
                    author = last_line
                    quote_text = "\n".join(lines[:-1]).strip()

            # Check if quote already exists
            if Quote.objects.filter(text=quote_text).exists():
                skipped_count += 1
                continue

            # Create the quote
            Quote.objects.create(
                text=quote_text, author=author, category=category, active=True
            )
            imported_count += 1

        # Summary
        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {imported_count} quotes")
        )

        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Skipped {skipped_count} duplicate quotes")
            )

"""
Management command to run both Django server and Django-Q worker together.

Usage:
    python manage.py runserver_with_worker
    python manage.py runserver_with_worker 8080  # Custom port
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys
import signal
import os


class Command(BaseCommand):
    help = 'Run Django development server and Django-Q worker together'

    def add_arguments(self, parser):
        parser.add_argument(
            'addrport',
            nargs='?',
            default='8000',
            help='Optional port number, or ipaddr:port'
        )

    def handle(self, *args, **options):
        addrport = options['addrport']
        
        self.stdout.write(self.style.SUCCESS('Starting Django server and Django-Q worker...\n'))
        
        # Start qcluster in background
        qcluster_process = subprocess.Popen(
            [sys.executable, 'manage.py', 'qcluster'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Django-Q worker started (PID: {qcluster_process.pid})'))
        
        # Handle Ctrl+C to stop both processes
        def signal_handler(sig, frame):
            self.stdout.write(self.style.WARNING('\n\nStopping server and worker...'))
            qcluster_process.terminate()
            qcluster_process.wait()
            self.stdout.write(self.style.SUCCESS('✓ Stopped'))
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Print qcluster output in background
        import threading
        def print_qcluster_output():
            for line in qcluster_process.stdout:
                self.stdout.write(self.style.SUCCESS(f'[Q] {line.rstrip()}'))
        
        thread = threading.Thread(target=print_qcluster_output, daemon=True)
        thread.start()
        
        # Start Django server (this blocks)
        self.stdout.write(self.style.SUCCESS(f'✓ Starting Django server on {addrport}...\n'))
        try:
            call_command('runserver', addrport, use_reloader=True)
        except KeyboardInterrupt:
            pass
        finally:
            qcluster_process.terminate()
            qcluster_process.wait()

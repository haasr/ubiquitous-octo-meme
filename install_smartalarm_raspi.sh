#!/bin/bash -

# This script automates the complete setup of the Smart Alarm System

set -e  # Exit on any error

# Configuration variables
INSTALL_DIR="/opt/smartalarm_web"
SERVICE_NAME="smartalarm_web"
GROUP=$USER

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run as the pi user."
        exit 1
    fi
}

# Check if we're on Raspberry Pi
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        log_warning "This doesn't appear to be a Raspberry Pi. Continuing anyway..."
    fi
}

# Update system packages
update_system() {
    log_info "Updating system packages..."
    sudo apt update && sudo apt upgrade -y
    log_success "System packages updated"
}

# Install required packages
install_packages() {
    log_info "Installing required packages..."
    sudo apt install -y python3-pip python3-venv git chromium-browser unclutter curl xdotool fonts-noto-color-emoji
    log_success "Required packages installed"
}

# Create installation directory
create_install_dir() {
    log_info "Creating installation directory..."
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown $USER:$GROUP "$INSTALL_DIR"
    log_success "Installation directory created: $INSTALL_DIR"
}

# Setup Python environment
setup_python_env() {
    log_info "Setting up Python virtual environment..."
    cd "$INSTALL_DIR"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install croniter django django_q2 feedparser requests google-images-downloader gunicorn whitenoise
    log_success "Python environment configured"
}

# Copy project files
copy_project_files() {
    log_info "Copying project files..."
    
    # Prompt user for source directory
    echo -n "Enter the path to your project files (or press Enter for current directory): "
    read source_dir
    
    if [ -z "$source_dir" ]; then
        source_dir="."
    fi
    
    # Copy all files
    rsync -av --exclude='.venv' --exclude='*.pyc' --exclude='__pycache__' "$source_dir/" "$INSTALL_DIR/"
    log_success "Project files copied"
}

# Configure Django settings for production
configure_django_settings() {
    log_info "Configuring Django settings for production..."
    
    # Add production settings to config/settings.py
    cat >> "$INSTALL_DIR/config/settings.py" <<'EOF'

# Production settings added by installer
DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Static files configuration
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Media files configuration
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
EOF

    log_success "Django settings updated for production"
}

# Configure Django (migrations, static files, etc.)
configure_django() {
    log_info "Configuring Django..."
    cd "$INSTALL_DIR"
    source .venv/bin/activate

    # Run migrations
    log_info "Running database migrations..."
    python manage.py migrate

    # Collect static files
    log_info "Collecting static files..."
    python manage.py collectstatic --noinput
    sudo chown -R $USER:$GROUP "$INSTALL_DIR/staticfiles"

    # Create superuser (optional)
    echo -n "Create Django admin superuser? (y/n): "
    read create_superuser
    if [[ $create_superuser =~ ^[Yy]$ ]]; then
        python manage.py createsuperuser
    fi

    log_success "Django configured"
}

# Create systemd service file for Django web server
create_web_service_file() {
    log_info "Creating Django web service file..."

    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Smart Alarm Django Web Server
After=network.target

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin
ExecStart=/opt/smartalarm_web/.venv/bin/python manage.py runserver_with_worker 0.0.0.0:8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    log_success "Web service file created"
}

# Enable and start services
enable_services() {
    log_info "Enabling and starting services..."
    sudo systemctl daemon-reload

    # Enable and start web service
    sudo systemctl enable $SERVICE_NAME.service
    sudo systemctl start $SERVICE_NAME.service

    # Wait and check status
    sleep 3
    if sudo systemctl is-active --quiet $SERVICE_NAME.service; then
        log_success "Web service is running"
    else
        log_error "Web service failed to start. Check: sudo systemctl status $SERVICE_NAME.service"
        exit 1
    fi
}

# Create kiosk launch script
create_launch_script() {
    log_info "Creating kiosk launch script..."
    
    cat > /home/$USER/start_smartalarm.sh <<'EOF'
#!/bin/bash

# Wait for the Django service to be ready
echo "Waiting for Django service to start..."
while ! curl -s http://localhost:8080 > /dev/null; do
    sleep 2
done

# Hide mouse cursor
unclutter -idle 0.5 -root &

# Launch Chromium in kiosk mode
chromium-browser \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-suggestions-service \
    --disable-translate \
    --disable-save-password-bubble \
    --disable-web-security \
    --disable-features=TranslateUI \
    --disable-extensions \
    --disable-plugins \
    --disable-default-apps \
    --disable-popup-blocking \
    --disable-prompt-on-repost \
    --no-first-run \
    --fast \
    --fast-start \
    --disable-default-apps \
    --no-default-browser-check \
    --autoplay-policy=no-user-gesture-required \
    --start-maximized \
    --kiosk \
    --app=http://localhost:8080
EOF

    chmod +x /home/$USER/start_smartalarm.sh
    log_success "Kiosk launch script created"
}

# Create desktop autostart entry
create_autostart() {
    log_info "Creating desktop autostart entry..."
    
    mkdir -p /home/$USER/.config/autostart
    
    cat > /home/$USER/.config/autostart/smartalarm.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Smart Alarm Display
Exec=/home/$USER/start_smartalarm.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
    
    log_success "Desktop autostart entry created"
}

# Configure LXDE session
configure_lxde() {
    log_info "Configuring LXDE session..."
    
    mkdir -p /home/$USER/.config/lxsession/LXDE-pi
    
    # Create or append to autostart file
    cat >> /home/$USER/.config/lxsession/LXDE-pi/autostart <<EOF

# Smart Alarm display configuration
@xset s off
@xset -dpms
@xset s noblank
@unclutter -idle 0.5

EOF
    
    log_success "LXDE session configured"
}

# Configure boot options
configure_boot() {
    log_info "Configuring boot options..."
    
    # Backup original config
    sudo cp /boot/config.txt /boot/config.txt.backup
    
    # Add display settings
    sudo tee -a /boot/config.txt > /dev/null <<EOF

# Smart Alarm display configuration
disable_overscan=1
gpu_mem=128
disable_splash=1
EOF
    
    log_success "Boot configuration updated"
}

# Test the installation
test_installation() {
    log_info "Testing installation..."
    
    # Test web service
    if sudo systemctl is-active --quiet $SERVICE_NAME.service; then
        log_success "Web service is running"
    else
        log_error "Web service is not running"
        return 1
    fi

    # Test web server response
    if curl -s http://localhost:8080 > /dev/null; then
        log_success "Web server is responding"
    else
        log_error "Web server is not responding"
        return 1
    fi
    
    # Test static files
    if curl -s http://localhost:8080/static/alarm_app/css/style.css > /dev/null; then
        log_success "Static files are serving correctly"
    else
        log_warning "Static files may not be configured correctly"
    fi

    log_success "Installation test passed"
}

# Create uninstall script
create_uninstall_script() {
    log_info "Creating uninstall script..."
    
    cat > /home/$USER/uninstall_smartalarm.sh <<EOF
#!/bin/bash

# Uninstall Smart Alarm System
echo "Uninstalling Smart Alarm System..."

# Stop and disable services
sudo systemctl stop $SERVICE_NAME.service
sudo systemctl disable $SERVICE_NAME.service
sudo rm /etc/systemd/system/$SERVICE_NAME.service
sudo systemctl daemon-reload

# Remove autostart entries
rm -f /home/$USER/.config/autostart/smartalarm.desktop
rm -f /home/$USER/start_smartalarm.sh

# Remove installation directory
sudo rm -rf "$INSTALL_DIR"

# Restore boot config
if [ -f /boot/config.txt.backup ]; then
    sudo cp /boot/config.txt.backup /boot/config.txt
fi

echo "Smart Alarm System uninstalled"
echo "Note: System packages were not removed"
EOF
    
    chmod +x /home/$USER/uninstall_smartalarm.sh
    log_success "Uninstall script created at /home/$USER/uninstall_smartalarm.sh"
}

# Main installation function
main() {
    echo "=========================================="
    echo "       Smart Alarm System"
    echo "   Raspberry Pi Installation Script"
    echo "=========================================="
    echo
    
    check_root
    check_raspberry_pi
    
    log_info "Starting installation..."
    
    # System setup
    update_system
    install_packages
    
    # Application setup
    create_install_dir
    copy_project_files
    setup_python_env
    configure_django_settings
    configure_django
    
    # Service setup
    create_web_service_file
    enable_services
    
    # Kiosk setup
    create_launch_script
    create_autostart
    configure_lxde
    configure_boot
    
    # Utility scripts
    create_uninstall_script
    
    # Final test
    test_installation

    echo
    log_success "Installation completed successfully!"
    echo
    echo "=========================================="
    echo "  Installation Summary"
    echo "=========================================="
    echo "Web Service: $SERVICE_NAME"
    echo "Worker Service: ${SERVICE_NAME}-worker"
    echo "Install directory: $INSTALL_DIR"
    echo "Web interface: http://localhost:8080"
    echo "Launch script: /home/$USER/start_smartalarm.sh"
    echo "Uninstall script: /home/$USER/uninstall_smartalarm.sh"
    echo
    echo "To complete the setup:"
    echo "1. Reboot the system: sudo reboot"
    echo "2. The Smart Alarm System will start automatically"
    echo "3. Access admin at: http://localhost:8080/admin/"
    echo
    echo "Useful commands:"
    echo "- Web service: sudo systemctl status $SERVICE_NAME"
    echo "- Worker service: sudo systemctl status ${SERVICE_NAME}-worker"
    echo "- Web logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "- Worker logs: sudo journalctl -u ${SERVICE_NAME}-worker -f"
    echo "- Reload schedules: cd $INSTALL_DIR && source .venv/bin/activate && python manage.py reload_schedules"
    echo "=========================================="
}

# Run main function
main "$@"

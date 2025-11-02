#!/bin/bash
# Quick Setup Script for Smart Alarm Web Templates
# Run this after copying files to your Django project

echo "=========================================="
echo "Smart Alarm Web - Template Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Checking Django installation...${NC}"
if ! command -v python &> /dev/null; then
    echo "Python not found! Please install Python first."
    exit 1
fi

if ! python -c "import django" &> /dev/null 2>&1; then
    echo "Django not found! Installing..."
    pip install django apscheduler feedparser requests
else
    echo -e "${GREEN}✓ Django is installed${NC}"
fi

echo ""
echo -e "${YELLOW}Step 2: Running migrations...${NC}"
python manage.py makemigrations
python manage.py migrate
echo -e "${GREEN}✓ Migrations complete${NC}"

echo ""
echo -e "${YELLOW}Step 3: Creating superuser (if needed)...${NC}"
echo "You can skip this if you already have a superuser."
python manage.py createsuperuser --noinput --username admin --email admin@example.com 2>/dev/null || echo "Superuser already exists or skipped"

echo ""
echo -e "${YELLOW}Step 4: Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"

echo ""
echo -e "${YELLOW}Step 5: Importing sample data (optional)...${NC}"
read -p "Do you want to import sample quotes? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "quotes.txt" ]; then
        python manage.py import_quotes quotes.txt
        echo -e "${GREEN}✓ Quotes imported${NC}"
    else
        echo "quotes.txt not found. Skipping..."
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run: python manage.py runserver"
echo "2. Visit: http://localhost:8000/"
echo "3. Admin: http://localhost:8000/admin/"
echo ""
echo "Default admin credentials (if created):"
echo "  Username: admin"
echo "  Password: (you were prompted to set it)"
echo ""
echo "Have fun with your Smart Alarm System! ⏰"
